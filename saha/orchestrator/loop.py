"""Main agentic loop orchestrator."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from saha.config.settings import Settings
from saha.hooks.registry import HookRegistry
from saha.logging import (
    console,
    log_agent_prompt,
    log_iteration_complete,
    log_iteration_start,
    log_phase_complete,
    log_phase_failed,
    log_phase_start,
    log_task_complete,
    log_task_failed,
)
from saha.models.result import (
    CodeQualityResult,
    QAResult,
    ResultStatus,
    SubagentResult,
)
from saha.models.state import ExecutionState, LoopPhase, StepStatus
from saha.orchestrator.state import StateManager
from saha.runners.base import Runner
from saha.runners.registry import RunnerRegistry
from saha.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class LoopConfig:
    """Configuration for a single loop run."""

    task_id: str
    task_path: Path
    max_iterations: int = 10
    enabled_tools: list[str] | None = None
    playwright_enabled: bool = False
    verification_scripts: list[Path] | None = None


class AgenticLoop:
    """Orchestrates the agentic implementation loop.

    The loop follows this flow:
    1. Get next task/phase to implement
    2. Run Implementation Subagent → produces code diff
    3. Run QA Subagent → verifies DoD with tools
    4. If DoD not achieved → back to step 2 with fix info
    5. Run Code Quality Subagent → checks Ruff, ty, complexity
    6. If quality fails → back to step 2 with fix info
    7. Run Manager Subagent → updates task status
    8. Run DoD Subagent → checks if task is complete
    9. If complete → end, else → back to step 1

    Supports multiple LLM backends via RunnerRegistry, allowing different
    agents to use different runners (e.g., Claude for implementation, Gemini for QA).
    """

    def __init__(
        self,
        runner: Runner,
        tool_registry: ToolRegistry,
        hook_registry: HookRegistry,
        state_manager: StateManager,
        settings: Settings,
        runner_registry: RunnerRegistry | None = None,
    ):
        self._runner = runner  # Default runner for backwards compatibility
        self._runner_registry = runner_registry
        self._tools = tool_registry
        self._hooks = hook_registry
        self._state_manager = state_manager
        self._settings = settings

    def _get_runner_for_agent(self, agent_name: str) -> Runner:
        """Get the appropriate runner for an agent.

        Uses the RunnerRegistry if available, otherwise falls back to default runner.

        Args:
            agent_name: Name of the agent (e.g., "execution-qa").

        Returns:
            Runner instance to use for this agent.
        """
        if self._runner_registry:
            return self._runner_registry.get_runner_for_agent(agent_name)
        return self._runner

    def _get_agent_path(self, agent_name: str) -> Path:
        """Get the path to an agent spec, considering variants.

        Checks settings for agent-specific variant configuration.

        Args:
            agent_name: Base agent name (e.g., "execution_qa").

        Returns:
            Path to the agent spec file.
        """
        normalized_name = agent_name.replace("_", "-")
        config = self._settings.get_agent_runner_config(normalized_name)
        return self._settings.get_agent_path(agent_name, variant=config.variant)

    def run(self, config: LoopConfig) -> ExecutionState:
        """Run the agentic loop for a task.

        Always starts fresh - use resume() to continue from saved state.
        """
        # Delete any existing state and create fresh
        self._state_manager.delete(config.task_id)
        state = self._state_manager.create(
            task_id=config.task_id,
            task_path=config.task_path,
            max_iterations=config.max_iterations,
            enabled_tools=config.enabled_tools or self._tools.list_available(),
        )

        console.print(f"\n[task]{'═' * 50}[/task]")
        console.print(f"[task]▶ STARTING TASK: {config.task_id}[/task]")
        console.print(f"[task]  Path: {config.task_path}[/task]")
        console.print(f"[task]  Max iterations: {config.max_iterations}[/task]")
        console.print(f"[task]{'═' * 50}[/task]")
        self._hooks.trigger("loop_start", state=state)

        try:
            while self._should_continue(state):
                state = self._run_iteration(state, config)

            self._finalize(state)

        except Exception as e:
            logger.exception(f"Loop failed with error: {e}")
            self._state_manager.mark_failed(state, str(e))
            self._hooks.trigger("loop_error", state=state, error=str(e))

        return state

    def resume(self, task_id: str) -> ExecutionState:
        """Resume a previously started loop."""
        state = self._state_manager.load(task_id)
        if state is None:
            raise LoopError(f"No saved state found for task: {task_id}")

        if state.current_phase in (LoopPhase.COMPLETED, LoopPhase.FAILED):
            raise LoopError(f"Task {task_id} is already {state.current_phase.value}")

        logger.info(f"Resuming loop for task: {task_id} at phase: {state.current_phase}")

        config = LoopConfig(
            task_id=task_id,
            task_path=state.task_path,
            max_iterations=state.max_iterations,
            enabled_tools=state.enabled_tools,
        )

        return self.run(config)

    def _should_continue(self, state: ExecutionState) -> bool:
        """Check if the loop should continue."""
        if state.current_phase in (LoopPhase.COMPLETED, LoopPhase.FAILED):
            return False

        if state.current_iteration >= state.max_iterations:
            logger.warning(f"Max iterations ({state.max_iterations}) reached")
            return False

        return True

    def _run_iteration(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> ExecutionState:
        """Run a single iteration of the loop."""
        iteration = state.start_iteration()
        log_iteration_start(iteration.iteration, state.max_iterations)
        self._hooks.trigger("iteration_start", state=state, iteration=iteration)

        # Phase 1: Implementation
        impl_result = self._run_implementation(state, config)
        if not impl_result.succeeded:
            self._state_manager.fail_phase(state, LoopPhase.IMPLEMENTATION, impl_result.error or "Implementation failed")
            return state

        # Track files changed for progress visibility
        if impl_result.structured_output:
            iteration.files_changed = impl_result.structured_output.get("files_changed", [])
            iteration.files_added = impl_result.structured_output.get("files_added", [])
            logger.debug(f"Implementation structured output: {impl_result.structured_output}")
        else:
            logger.warning("Implementation agent did not return structured JSON output")
        state.last_agent_output = impl_result.output
        self._state_manager.save(state)

        # Phase 2: QA Verification
        qa_result = self._run_qa(state, config, impl_result)
        if not qa_result.dod_achieved:
            # Loop back with fix info
            state.context["fix_info"] = qa_result.fix_info
            iteration.fix_info = qa_result.fix_info
            self._state_manager.save(state)
            self._hooks.trigger("qa_failed", state=state, qa_result=qa_result)
            return state

        iteration.dod_achieved = True

        # Phase 3: Code Quality
        quality_result = self._run_code_quality(state, config, impl_result)
        if not quality_result.passed:
            # Loop back with fix info
            state.context["fix_info"] = quality_result.fix_info
            iteration.fix_info = quality_result.fix_info
            self._state_manager.save(state)
            self._hooks.trigger("quality_failed", state=state, quality_result=quality_result)
            return state

        iteration.quality_passed = True

        # Phase 4: Manager updates
        self._run_manager(state, config)

        # Phase 5: DoD Check
        task_complete = self._run_dod_check(state, config)
        if task_complete:
            self._state_manager.mark_completed(state)

        iteration.completed_at = datetime.now()
        log_iteration_complete(
            iteration.iteration,
            dod_achieved=iteration.dod_achieved,
            quality_passed=iteration.quality_passed,
        )
        self._state_manager.save(state)
        self._hooks.trigger("iteration_complete", state=state, iteration=iteration)

        return state

    def _run_implementation(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> SubagentResult:
        """Run the implementation subagent."""
        self._state_manager.update_phase(state, LoopPhase.IMPLEMENTATION)
        log_phase_start("Implementation", config.task_id)
        self._hooks.trigger("implementation_start", state=state)

        agent_name = "execution-implementer"
        agent_path = self._get_agent_path("execution_implementer")
        runner = self._get_runner_for_agent(agent_name)

        # Build context for the agent
        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "iteration": state.current_iteration,
            "fix_info": state.context.get("fix_info"),
        }

        # Build the prompt
        prompt = self._build_implementation_prompt(state, config)
        log_agent_prompt("Implementation", prompt)

        result = runner.run_agent(agent_path, prompt, context)

        if result.success:
            self._state_manager.complete_phase(state, LoopPhase.IMPLEMENTATION, "Code implemented")
            log_phase_complete("Implementation")
            return SubagentResult(
                agent_name="implementation",
                status=ResultStatus.SUCCESS,
                output=result.output,
                structured_output=result.structured_output or {},
            )
        else:
            log_phase_failed("Implementation", result.error or "Unknown error")
            return SubagentResult(
                agent_name="implementation",
                status=ResultStatus.FAILURE,
                error=result.error,
            )

    def _run_qa(
        self,
        state: ExecutionState,
        config: LoopConfig,
        impl_result: SubagentResult,
    ) -> QAResult:
        """Run the QA subagent with verification tools.

        Automatically selects the Playwright-enabled variant if playwright_enabled
        is True in the config. This keeps Playwright MCP tools out of context
        when not needed.
        """
        self._state_manager.update_phase(state, LoopPhase.QA)
        log_phase_start("QA Verification", config.task_id)
        self._hooks.trigger("qa_start", state=state)

        # Select agent variant based on Playwright configuration
        agent_name = "execution-qa"
        if config.playwright_enabled:
            # Use Playwright-enabled variant
            agent_path = self._settings.get_agent_path("execution_qa", variant="playwright")
            logger.info("Using Playwright-enabled QA agent variant")
        else:
            # Check if there's a configured variant in settings
            agent_path = self._get_agent_path("execution_qa")

        runner = self._get_runner_for_agent(agent_name)

        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "implementation_output": impl_result.output,
            "verification_scripts": [str(s) for s in (config.verification_scripts or [])],
            "playwright_enabled": config.playwright_enabled,
        }

        prompt = self._build_qa_prompt(state, config)
        log_agent_prompt("QA", prompt)

        result = runner.run_agent(agent_path, prompt, context)

        # Run pytest if enabled
        test_output = ""
        if "pytest" in state.enabled_tools:
            pytest_result = self._tools.run_tool("pytest", config.task_path)
            test_output = pytest_result.stdout

        if result.success:
            # Parse structured output for DoD status
            dod_achieved = result.structured_output.get("dod_achieved", False) if result.structured_output else False
            fix_info = result.structured_output.get("fix_info") if result.structured_output else None

            self._state_manager.complete_phase(state, LoopPhase.QA)

            return QAResult(
                status=ResultStatus.SUCCESS if dod_achieved else ResultStatus.FAILURE,
                dod_achieved=dod_achieved,
                fix_info=fix_info or result.output if not dod_achieved else None,
                test_output=test_output,
            )
        else:
            return QAResult(
                status=ResultStatus.ERROR,
                dod_achieved=False,
                fix_info=result.error,
            )

    def _run_code_quality(
        self,
        state: ExecutionState,
        config: LoopConfig,
        impl_result: SubagentResult,
    ) -> CodeQualityResult:
        """Run code quality subagent on changed files.

        The Code Quality agent intelligently analyzes tool outputs,
        filtering false positives and pre-existing issues.
        """
        self._state_manager.update_phase(state, LoopPhase.CODE_QUALITY)
        log_phase_start("Code Quality", config.task_id)
        self._hooks.trigger("quality_start", state=state)

        agent_name = "execution-code-quality"
        agent_path = self._get_agent_path("execution_code_quality")
        runner = self._get_runner_for_agent(agent_name)

        # Extract changed files from implementation output
        files_changed = []
        files_added = []
        if impl_result.structured_output:
            files_changed = impl_result.structured_output.get("files_changed", [])
            files_added = impl_result.structured_output.get("files_added", [])

        # If no files info, fall back to checking task path
        all_files = files_changed + files_added
        if not all_files:
            logger.warning("No files_changed info from implementation, will scan task path")

        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "files_changed": files_changed,
            "files_added": files_added,
            "iteration": state.current_iteration,
            "enabled_tools": [t for t in state.enabled_tools if t in ("ruff", "ty", "complexity")],
        }

        prompt = self._build_code_quality_prompt(state, config, all_files)
        log_agent_prompt("Code Quality", prompt)

        result = runner.run_agent(agent_path, prompt, context)

        if result.success and result.structured_output:
            quality_passed = result.structured_output.get("quality_passed", False)
            fix_info = result.structured_output.get("fix_info") if not quality_passed else None

            if quality_passed:
                self._state_manager.complete_phase(state, LoopPhase.CODE_QUALITY)
            else:
                # Record the failure but don't mark the entire task as failed
                # The loop will continue and retry with fix_info
                state.record_step(
                    LoopPhase.CODE_QUALITY,
                    StepStatus.FAILED,
                    error=fix_info or "Quality check failed",
                )
                self._state_manager.save(state)

            return CodeQualityResult(
                status=ResultStatus.SUCCESS if quality_passed else ResultStatus.FAILURE,
                passed=quality_passed,
                fix_info=fix_info,
                issues=result.structured_output.get("issues", []),
                files_analyzed=result.structured_output.get("files_analyzed", []),
                blocking_issues_count=result.structured_output.get("blocking_issues_count", 0),
                ignored_issues_count=result.structured_output.get("ignored_issues_count", 0),
            )
        else:
            # Agent failed to run - fall back to passing (don't block on agent errors)
            logger.warning(f"Code quality agent failed: {result.error}, allowing to proceed")
            self._state_manager.complete_phase(state, LoopPhase.CODE_QUALITY)
            return CodeQualityResult(
                status=ResultStatus.SUCCESS,
                passed=True,
                fix_info=None,
            )

    def _build_code_quality_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
        files: list[str],
    ) -> str:
        """Build the prompt for the code quality agent."""
        parts = [
            f"Analyze code quality for task: {config.task_id}",
            f"Task path: {config.task_path}",
            f"Iteration: {state.current_iteration}",
            "",
        ]

        if files:
            parts.append("Files to analyze:")
            for f in files:
                parts.append(f"  - {f}")
        else:
            parts.append("No specific files provided. Analyze recent changes in the task directory.")

        parts.extend([
            "",
            "Run quality tools (ruff, ty, complexipy) on these files.",
            "Filter false positives and pre-existing issues.",
            "Only fail for genuine problems in the changed code.",
            "",
            'Return JSON: {"quality_passed": true/false, "fix_info": "..." if failed}',
        ])

        return "\n".join(parts)

    def _run_manager(self, state: ExecutionState, config: LoopConfig) -> None:
        """Run the manager subagent to update task status."""
        self._state_manager.update_phase(state, LoopPhase.MANAGER)
        log_phase_start("Manager", config.task_id)
        self._hooks.trigger("manager_start", state=state)

        agent_name = "execution-manager"
        agent_path = self._get_agent_path("execution_manager")
        runner = self._get_runner_for_agent(agent_name)

        if agent_path.exists():
            context = {
                "task_id": config.task_id,
                "task_path": str(config.task_path),
                "iteration": state.current_iteration,
            }

            prompt = "Update the task status based on the completed implementation iteration."
            log_agent_prompt("Manager", prompt)

            result = runner.run_agent(agent_path, prompt, context)

            if result.success:
                log_phase_complete("Manager")
            else:
                log_phase_failed("Manager", result.error or "Unknown error")

        self._state_manager.complete_phase(state, LoopPhase.MANAGER)

    def _run_dod_check(self, state: ExecutionState, config: LoopConfig) -> bool:
        """Run the DoD subagent to check if the task is complete."""
        self._state_manager.update_phase(state, LoopPhase.DOD_CHECK)
        log_phase_start("DoD Check", config.task_id)
        self._hooks.trigger("dod_check_start", state=state)

        agent_name = "execution-dod"
        agent_path = self._get_agent_path("execution_dod")
        runner = self._get_runner_for_agent(agent_name)

        if agent_path.exists():
            context = {
                "task_id": config.task_id,
                "task_path": str(config.task_path),
                "iterations_completed": state.current_iteration,
            }

            prompt = "Check if all task requirements have been satisfied and the task is complete."
            log_agent_prompt("DoD", prompt)

            result = runner.run_agent(agent_path, prompt, context)

            if result.success:
                task_complete = bool(
                    result.structured_output.get("task_complete", False)
                    if result.structured_output
                    else False
                )
                status = "complete" if task_complete else "incomplete"
                log_phase_complete("DoD Check", f"Task status: {status}")
                return task_complete
            else:
                log_phase_failed("DoD Check", result.error or "Unknown error")

        # Default: complete after one successful iteration
        log_phase_complete("DoD Check", "Default: marking complete after iteration")
        self._state_manager.complete_phase(state, LoopPhase.DOD_CHECK)
        return True

    def _finalize(self, state: ExecutionState) -> None:
        """Finalize the loop execution."""
        if state.current_phase == LoopPhase.COMPLETED:
            log_task_complete(state.task_id, state.current_iteration)
            self._hooks.trigger("loop_complete", state=state)
        elif state.current_phase == LoopPhase.FAILED:
            log_task_failed(state.task_id, state.error_message or "Unknown error")
            self._hooks.trigger("loop_failed", state=state)
        else:
            logger.warning(f"Task {state.task_id} stopped at phase: {state.current_phase}")

    def _build_implementation_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> str:
        """Build the prompt for the implementation agent."""
        parts = [
            f"Implement the next part of task: {config.task_id}",
            f"Task path: {config.task_path}",
            f"This is iteration {state.current_iteration}.",
        ]

        if state.context.get("fix_info"):
            parts.append(f"\nPrevious iteration feedback:\n{state.context['fix_info']}")

        parts.append("\nRead the task artifacts and implement according to the plan.")
        parts.append(
            "\n**IMPORTANT**: After implementation, output a JSON block with files_changed:"
        )
        parts.append("```json")
        parts.append('{"files_changed": ["path/to/file.py"], "files_added": [], "summary": "..."}')
        parts.append("```")

        return "\n".join(parts)

    def _build_qa_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> str:
        """Build the prompt for the QA agent."""
        parts = [
            f"Verify the implementation for task: {config.task_id}",
            f"Task path: {config.task_path}",
            "",
            "Check that:",
            "1. The implementation matches the task requirements",
            "2. All acceptance criteria are met",
            "3. Tests pass (if applicable)",
        ]

        if config.verification_scripts:
            parts.append(f"\nRun verification scripts: {config.verification_scripts}")

        parts.append(
            "\nReturn a JSON with: {\"dod_achieved\": true/false, \"fix_info\": \"...\" if not achieved}"
        )

        return "\n".join(parts)


class LoopError(Exception):
    """Error during loop execution."""

    pass
