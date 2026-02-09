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
    log_task_stopped,
    log_token_usage,
)
from saha.models.result import (
    CodeQualityResult,
    QAResult,
    ResultStatus,
    SubagentResult,
    TestCritiqueResult,
)
from saha.models.state import ExecutionState, LoopPhase, StepStatus
from saha.orchestrator.plan_progress import PlanProgressUpdater
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
    1. Run Implementation Subagent → produces code diff
    2. Run Test Critique Subagent → analyzes test quality for hollow tests
    3. If tests are hollow (D/F) → back to step 1 with fix info
    4. Run QA Subagent → verifies DoD with tools
    5. If DoD not achieved → back to step 1 with fix info
    6. Run Code Quality Subagent → checks Ruff, ty, complexity
    7. If quality fails → back to step 1 with fix info
    8. Run Manager Subagent → updates task status
    9. Run DoD Subagent → checks if task is complete
    10. If complete → end, else → back to step 1

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

        except KeyboardInterrupt:
            logger.warning("Interrupt received. Stopping agentic loop gracefully.")
            self._handle_interrupt(state, config)

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
        if state.current_phase in (LoopPhase.COMPLETED, LoopPhase.FAILED, LoopPhase.STOPPED):
            return False

        if state.current_iteration >= state.max_iterations:
            logger.warning(f"Max iterations ({state.max_iterations}) reached")
            return False

        return True

    def _handle_interrupt(self, state: ExecutionState, config: LoopConfig) -> None:
        """Handle a user interrupt (Ctrl+C) gracefully."""
        reason = "Interrupted by user"

        # Attempt to update task status with manager, unless already in/after manager
        try:
            if self._should_run_manager_on_interrupt(state):
                self._run_manager(state, config, None, None)
        except KeyboardInterrupt:
            logger.warning("Interrupt received during manager cleanup. Skipping manager update.")
        except Exception as e:
            logger.warning(f"Manager update during interrupt failed: {e}")

        self._state_manager.mark_stopped(state, reason)
        self._finalize(state)

    def _should_run_manager_on_interrupt(self, state: ExecutionState) -> bool:
        """Determine if manager should run when interrupting."""
        if state.current_iteration == 0:
            return False

        if state.current_phase in (LoopPhase.MANAGER, LoopPhase.DOD_CHECK, LoopPhase.COMPLETED, LoopPhase.FAILED):
            return False

        iteration = state.current_iteration_record
        if iteration:
            for step in iteration.steps:
                if step.phase == LoopPhase.MANAGER and step.status == StepStatus.COMPLETED:
                    return False

        return True

    def _prepare_plan_progress(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> tuple[PlanProgressUpdater | None, Path | None]:
        """Select the active implementation phase for progress updates."""
        updater = PlanProgressUpdater(config.task_path)
        selection = updater.select_active_phase(state)
        if selection is None:
            return None, None
        if selection.updated_context:
            self._state_manager.save(state)
        return updater, selection.phase_path

    def _update_plan_progress(
        self,
        updater: PlanProgressUpdater | None,
        phase_path: Path | None,
        loop_phase: LoopPhase,
        status_kind: str,
        iteration: int,
        note: str | None = None,
        update_status_line: bool = True,
    ) -> None:
        """Best-effort update of the plan execution progress table."""
        if updater is None or phase_path is None:
            return
        try:
            updater.update_execution_progress(
                phase_path,
                loop_phase,
                status_kind,
                iteration,
                note=note,
                update_status_line=update_status_line,
            )
        except Exception as exc:  # pragma: no cover - best effort update
            logger.debug(f"Plan progress update failed: {exc}")

    def _run_iteration(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> ExecutionState:
        """Run a single iteration of the loop."""
        iteration = state.start_iteration()
        log_iteration_start(iteration.iteration, state.max_iterations)
        self._hooks.trigger("iteration_start", state=state, iteration=iteration)

        plan_updater, plan_phase_path = self._prepare_plan_progress(state, config)

        # Phase 1: Implementation
        impl_result = self._run_implementation(state, config, plan_updater, plan_phase_path)
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

        # Phase 2: Test Critique (analyze test quality before running)
        critique_result = self._run_test_critique(state, config, impl_result, plan_updater, plan_phase_path)
        if not critique_result.passed:
            # Loop back with fix info - tests are hollow
            state.context["fix_info"] = critique_result.fix_info
            iteration.fix_info = critique_result.fix_info
            self._state_manager.save(state)
            self._hooks.trigger("test_critique_failed", state=state, critique_result=critique_result)
            return state

        iteration.test_critique_passed = True

        # Phase 3: QA Verification
        qa_result = self._run_qa(state, config, impl_result, plan_updater, plan_phase_path)
        if not qa_result.dod_achieved:
            # Loop back with fix info
            state.context["fix_info"] = qa_result.fix_info
            iteration.fix_info = qa_result.fix_info
            self._state_manager.save(state)
            self._hooks.trigger("qa_failed", state=state, qa_result=qa_result)
            return state

        iteration.dod_achieved = True

        # Phase 4: Code Quality
        quality_result = self._run_code_quality(state, config, impl_result, plan_updater, plan_phase_path)
        if not quality_result.passed:
            # Loop back with fix info
            state.context["fix_info"] = quality_result.fix_info
            iteration.fix_info = quality_result.fix_info
            self._state_manager.save(state)
            self._hooks.trigger("quality_failed", state=state, quality_result=quality_result)
            return state

        iteration.quality_passed = True

        # Phase 5: Manager updates
        self._run_manager(state, config, plan_updater, plan_phase_path)

        # Phase 6: DoD Check
        task_complete = self._run_dod_check(state, config, plan_updater, plan_phase_path)
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
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> SubagentResult:
        """Run the implementation subagent."""
        self._state_manager.update_phase(state, LoopPhase.IMPLEMENTATION)
        log_phase_start("Implementation", config.task_id)
        self._hooks.trigger("implementation_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.IMPLEMENTATION,
            "in_progress",
            state.current_iteration,
            note="implementation running",
        )

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
        log_token_usage("Implementation", result.token_usage, result.tokens_used)

        if result.success:
            self._state_manager.complete_phase(state, LoopPhase.IMPLEMENTATION, "Code implemented")
            log_phase_complete("Implementation")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.IMPLEMENTATION,
                "passed",
                state.current_iteration,
                note="implementation complete",
                update_status_line=False,
            )
            return SubagentResult(
                agent_name="implementation",
                status=ResultStatus.SUCCESS,
                output=result.output,
                structured_output=result.structured_output or {},
                tokens_used=result.tokens_used,
            )
        else:
            log_phase_failed("Implementation", result.error or "Unknown error")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.IMPLEMENTATION,
                "failed",
                state.current_iteration,
                note=result.error or "implementation failed",
                update_status_line=False,
            )
            return SubagentResult(
                agent_name="implementation",
                status=ResultStatus.FAILURE,
                error=result.error,
                tokens_used=result.tokens_used,
            )

    def _run_test_critique(
        self,
        state: ExecutionState,
        config: LoopConfig,
        impl_result: SubagentResult,
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> TestCritiqueResult:
        """Run test critique agent to analyze test quality before QA.

        This phase detects hollow tests that would give false confidence.
        If tests are hollow (score D or F), QA should not run.
        """
        self._state_manager.update_phase(state, LoopPhase.TEST_CRITIQUE)
        log_phase_start("Test Critique", config.task_id)
        self._hooks.trigger("test_critique_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.TEST_CRITIQUE,
            "in_progress",
            state.current_iteration,
            note="test critique running",
        )

        agent_name = "execution-test-critique"
        agent_path = self._get_agent_path("execution_test_critique")
        runner = self._get_runner_for_agent(agent_name)

        if not agent_path.exists():
            logger.warning(f"Test critique agent not found at {agent_path}, skipping")
            self._state_manager.complete_phase(state, LoopPhase.TEST_CRITIQUE)
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.TEST_CRITIQUE,
                "skipped",
                state.current_iteration,
                note="agent not configured",
                update_status_line=False,
            )
            return TestCritiqueResult(
                status=ResultStatus.SUCCESS,
                passed=True,
                test_quality_score="B",
                summary="Test critique agent not configured, skipping",
            )

        # Extract files from implementation output for focused analysis
        files_changed = []
        files_added = []
        if impl_result.structured_output:
            files_changed = impl_result.structured_output.get("files_changed", [])
            files_added = impl_result.structured_output.get("files_added", [])

        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "files_changed": files_changed,
            "files_added": files_added,
            "iteration": state.current_iteration,
        }

        prompt = self._build_test_critique_prompt(state, config, files_changed + files_added)
        log_agent_prompt("Test Critique", prompt)

        result = runner.run_agent(agent_path, prompt, context)
        log_token_usage("Test Critique", result.token_usage, result.tokens_used)

        if result.success and result.structured_output:
            critique_passed = result.structured_output.get("critique_passed", True)
            score = result.structured_output.get("test_quality_score", "C")
            fix_info = result.structured_output.get("fix_info") if not critique_passed else None

            if critique_passed:
                log_phase_complete("Test Critique", f"Score: {score}")
                self._state_manager.complete_phase(state, LoopPhase.TEST_CRITIQUE)
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.TEST_CRITIQUE,
                    "passed",
                    state.current_iteration,
                    note=f"score {score}",
                    update_status_line=False,
                )
            else:
                log_phase_failed("Test Critique", f"Score: {score} - tests are hollow")
                state.record_step(
                    LoopPhase.TEST_CRITIQUE,
                    StepStatus.FAILED,
                    error=fix_info or "Test quality check failed",
                )
                self._state_manager.save(state)
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.TEST_CRITIQUE,
                    "failed",
                    state.current_iteration,
                    note=f"score {score}",
                    update_status_line=False,
                )

            return TestCritiqueResult(
                status=ResultStatus.SUCCESS if critique_passed else ResultStatus.FAILURE,
                passed=critique_passed,
                test_quality_score=score,
                tests_analyzed=result.structured_output.get("tests_analyzed", 0),
                hollow_tests=result.structured_output.get("hollow_tests", 0),
                issues=result.structured_output.get("issues", []),
                summary=result.structured_output.get("summary", ""),
                fix_info=fix_info,
            )
        else:
            # Agent failed - don't block, but warn
            logger.warning(f"Test critique agent failed: {result.error}, proceeding")
            self._state_manager.complete_phase(state, LoopPhase.TEST_CRITIQUE)
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.TEST_CRITIQUE,
                "skipped",
                state.current_iteration,
                note="agent error",
                update_status_line=False,
            )
            return TestCritiqueResult(
                status=ResultStatus.SUCCESS,
                passed=True,
                test_quality_score="C",
                summary=f"Agent error: {result.error}, proceeding with caution",
            )

    def _build_test_critique_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
        files: list[str],
    ) -> str:
        """Build the prompt for the test critique agent."""
        # Filter to only test files
        test_files = [f for f in files if "test" in f.lower() or f.endswith("_test.py")]

        parts = [
            f"Analyze test quality for task: {config.task_id}",
            f"Task path: {config.task_path}",
            f"Iteration: {state.current_iteration}",
            "",
        ]

        if test_files:
            parts.append("Test files to analyze (from this iteration):")
            for f in test_files:
                parts.append(f"  - {f}")
        else:
            parts.append("No specific test files identified. Search for test files in the project.")

        parts.extend([
            "",
            "Analyze tests for hollow patterns:",
            "- Over-mocking (>3 mocks per test)",
            "- Mocking the System Under Test",
            "- Placeholder tests (pass, ..., assert True)",
            "- Assertions that only check mock calls, not outcomes",
            "",
            "Score A/B/C = proceed, D/F = block QA (tests are hollow)",
            "",
            'Return JSON: {"critique_passed": true/false, "test_quality_score": "A-F", "fix_info": "..."}',
        ])

        return "\n".join(parts)

    def _run_qa(
        self,
        state: ExecutionState,
        config: LoopConfig,
        impl_result: SubagentResult,
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> QAResult:
        """Run the QA subagent with verification tools.

        Automatically selects the Playwright-enabled variant if playwright_enabled
        is True in the config. This keeps Playwright MCP tools out of context
        when not needed.
        """
        self._state_manager.update_phase(state, LoopPhase.QA)
        log_phase_start("QA Verification", config.task_id)
        self._hooks.trigger("qa_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.QA,
            "in_progress",
            state.current_iteration,
            note="qa running",
        )

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
        log_token_usage("QA Verification", result.token_usage, result.tokens_used)

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
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.QA,
                "passed" if dod_achieved else "failed",
                state.current_iteration,
                note="criteria met" if dod_achieved else (fix_info or "qa failed"),
                update_status_line=False,
            )

            return QAResult(
                status=ResultStatus.SUCCESS if dod_achieved else ResultStatus.FAILURE,
                dod_achieved=dod_achieved,
                fix_info=fix_info or result.output if not dod_achieved else None,
                test_output=test_output,
            )
        else:
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.QA,
                "failed",
                state.current_iteration,
                note=result.error or "qa error",
                update_status_line=False,
            )
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
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> CodeQualityResult:
        """Run code quality subagent on changed files.

        The Code Quality agent intelligently analyzes tool outputs,
        filtering false positives and pre-existing issues.
        """
        self._state_manager.update_phase(state, LoopPhase.CODE_QUALITY)
        log_phase_start("Code Quality", config.task_id)
        self._hooks.trigger("quality_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.CODE_QUALITY,
            "in_progress",
            state.current_iteration,
            note="quality running",
        )

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
        log_token_usage("Code Quality", result.token_usage, result.tokens_used)

        if result.success and result.structured_output:
            quality_passed = result.structured_output.get("quality_passed", False)
            fix_info = result.structured_output.get("fix_info") if not quality_passed else None

            if quality_passed:
                self._state_manager.complete_phase(state, LoopPhase.CODE_QUALITY)
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.CODE_QUALITY,
                    "passed",
                    state.current_iteration,
                    note="quality passed",
                    update_status_line=False,
                )
            else:
                # Record the failure but don't mark the entire task as failed
                # The loop will continue and retry with fix_info
                state.record_step(
                    LoopPhase.CODE_QUALITY,
                    StepStatus.FAILED,
                    error=fix_info or "Quality check failed",
                )
                self._state_manager.save(state)
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.CODE_QUALITY,
                    "failed",
                    state.current_iteration,
                    note=fix_info or "quality failed",
                    update_status_line=False,
                )

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
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.CODE_QUALITY,
                "skipped",
                state.current_iteration,
                note="agent error",
                update_status_line=False,
            )
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

    def _run_manager(
        self,
        state: ExecutionState,
        config: LoopConfig,
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> None:
        """Run the manager subagent to update task status."""
        self._state_manager.update_phase(state, LoopPhase.MANAGER)
        log_phase_start("Manager", config.task_id)
        self._hooks.trigger("manager_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.MANAGER,
            "in_progress",
            state.current_iteration,
            note="manager updating",
        )

        agent_name = "execution-manager"
        agent_path = self._get_agent_path("execution_manager")
        runner = self._get_runner_for_agent(agent_name)

        if not agent_path.exists():
            logger.warning(f"Manager agent not found at {agent_path}, skipping")
            self._state_manager.complete_phase(state, LoopPhase.MANAGER)
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.MANAGER,
                "skipped",
                state.current_iteration,
                note="agent not configured",
                update_status_line=False,
            )
            return

        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "iteration": state.current_iteration,
        }

        prompt = self._build_manager_prompt(state, config)
        log_agent_prompt("Manager", prompt)

        result = runner.run_agent(agent_path, prompt, context)
        log_token_usage("Manager", result.token_usage, result.tokens_used)

        if result.success:
            log_phase_complete("Manager")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.MANAGER,
                "passed",
                state.current_iteration,
                note="manager complete",
                update_status_line=False,
            )
        else:
            log_phase_failed("Manager", result.error or "Unknown error")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.MANAGER,
                "failed",
                state.current_iteration,
                note=result.error or "manager failed",
                update_status_line=False,
            )

        self._state_manager.complete_phase(state, LoopPhase.MANAGER)

    def _run_dod_check(
        self,
        state: ExecutionState,
        config: LoopConfig,
        plan_updater: PlanProgressUpdater | None,
        plan_phase_path: Path | None,
    ) -> bool:
        """Run the DoD subagent to check if the task is complete.

        This is a CRITICAL gate - the agent MUST actually verify all user stories
        and acceptance criteria are met. No auto-completion fallbacks.
        """
        self._state_manager.update_phase(state, LoopPhase.DOD_CHECK)
        log_phase_start("DoD Check", config.task_id)
        self._hooks.trigger("dod_check_start", state=state)
        self._update_plan_progress(
            plan_updater,
            plan_phase_path,
            LoopPhase.DOD_CHECK,
            "in_progress",
            state.current_iteration,
            note="dod check running",
        )

        agent_name = "execution-dod"
        agent_path = self._get_agent_path("execution_dod")
        runner = self._get_runner_for_agent(agent_name)

        if not agent_path.exists():
            logger.error(f"DoD agent not found at {agent_path}")
            log_phase_failed("DoD Check", "DoD agent not found")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.DOD_CHECK,
                "failed",
                state.current_iteration,
                note="agent not configured",
                update_status_line=False,
            )
            # Don't auto-complete - this is a configuration error
            return False

        context = {
            "task_id": config.task_id,
            "task_path": str(config.task_path),
            "iterations_completed": state.current_iteration,
        }

        prompt = self._build_dod_prompt(state, config)
        log_agent_prompt("DoD", prompt)

        result = runner.run_agent(agent_path, prompt, context)
        log_token_usage("DoD Check", result.token_usage, result.tokens_used)

        if result.success and result.structured_output:
            task_complete = bool(result.structured_output.get("task_complete", False))
            status = "complete" if task_complete else "incomplete"
            remaining = result.structured_output.get("remaining_items", [])

            if task_complete:
                log_phase_complete("DoD Check", f"Task status: {status}")
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.DOD_CHECK,
                    "passed",
                    state.current_iteration,
                    note="task complete",
                    update_status_line=False,
                )
                if plan_updater:
                    plan_updater.mark_all_complete(note="task complete")
            else:
                remaining_str = ", ".join(remaining[:3]) if remaining else "see agent output"
                log_phase_complete("DoD Check", f"Task incomplete: {remaining_str}")
                self._update_plan_progress(
                    plan_updater,
                    plan_phase_path,
                    LoopPhase.DOD_CHECK,
                    "failed",
                    state.current_iteration,
                    note=remaining_str,
                    update_status_line=False,
                )

            self._state_manager.complete_phase(state, LoopPhase.DOD_CHECK)
            return task_complete
        else:
            # Agent failed or didn't return structured output
            error_msg = result.error or "No structured output from DoD agent"
            log_phase_failed("DoD Check", error_msg)
            logger.warning("DoD agent did not return structured output, continuing loop")
            self._update_plan_progress(
                plan_updater,
                plan_phase_path,
                LoopPhase.DOD_CHECK,
                "failed",
                state.current_iteration,
                note=error_msg,
                update_status_line=False,
            )
            # Don't auto-complete - require explicit verification
            return False

    def _finalize(self, state: ExecutionState) -> None:
        """Finalize the loop execution."""
        if state.current_phase == LoopPhase.COMPLETED:
            log_task_complete(state.task_id, state.current_iteration)
            self._hooks.trigger("loop_complete", state=state)
        elif state.current_phase == LoopPhase.FAILED:
            log_task_failed(state.task_id, state.error_message or "Unknown error")
            self._hooks.trigger("loop_failed", state=state)
        elif state.current_phase == LoopPhase.STOPPED:
            log_task_stopped(state.task_id, state.error_message or "Stopped")
            self._hooks.trigger("loop_stopped", state=state)
        else:
            logger.warning(f"Task {state.task_id} stopped at phase: {state.current_phase}")

    def _build_implementation_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> str:
        """Build the prompt for the implementation agent.

        Provides TDD-focused context to guide the agent through:
        1. Interface definition (from API contracts)
        2. Test writing (from test specs) - RED
        3. Implementation - GREEN
        """
        parts = [
            f"Implement task: {config.task_id}",
            f"Task path: {config.task_path}",
            f"Iteration: {state.current_iteration}",
            "",
        ]

        current_phase = state.context.get("current_plan_phase")
        if current_phase:
            parts.extend([
                f"Current plan phase: {current_phase}",
                "",
            ])

        if state.context.get("fix_info"):
            # Retry iteration - focus on fixing specific issues
            parts.extend([
                "## Fix Mode",
                "",
                "Previous iteration failed. Focus on fixing these issues:",
                "",
                state.context["fix_info"],
                "",
                "Run tests after each fix to verify progress.",
            ])
        else:
            # First iteration - full TDD cycle
            parts.extend([
                "## TDD Development Cycle",
                "",
                "Follow the TDD approach:",
                "",
                "### Phase 1: Interfaces",
                f"- Read API contracts at `{config.task_path}/api-contracts/`",
                "- Create Pydantic models and Protocol classes for the contracts",
                "",
                "### Phase 2: Tests (Red)",
                f"- Read test specs at `{config.task_path}/test-specs/`",
                "- Write pytest tests based on the specs",
                "- Tests WILL fail initially (this is expected)",
                "",
                "### Phase 3: Implementation (Green)",
                "- Implement code to make all tests pass",
                "- Run tests after implementation to verify",
                "",
                "Read the task artifacts and follow TDD strictly.",
            ])

        # NOTE: File changes are automatically extracted by the runner
        # (Claude tool metadata or filesystem diff), so we don't ask the LLM
        # to self-report them.

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

    def _build_manager_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> str:
        """Build the prompt for the manager agent."""
        parts = [
            f"Update task artifacts after iteration {state.current_iteration} for: {config.task_id}",
            f"Task path: {config.task_path}",
            "",
        ]

        current_phase = state.context.get("current_plan_phase")
        if current_phase:
            parts.extend([
                f"Current plan phase: {current_phase}",
                "",
            ])

        parts.extend([
            "Your job:",
            "1. Read the user stories at {task_path}/user-stories/",
            "2. Read the implementation plan at {task_path}/implementation-plan/",
            "3. Based on what was implemented this iteration, update:",
            "   - Mark completed acceptance criteria with [x]",
            "   - Update user story status if all criteria are met",
            "   - Mark completed phases in the implementation plan",
            "",
            "Only mark items as done that are actually implemented.",
            "Be conservative - if unsure, leave it as pending.",
            "",
            'Return JSON: {"status": "success", "updates_made": [...], "items_completed": [...]}',
        ])

        return "\n".join(parts)

    def _build_dod_prompt(
        self,
        state: ExecutionState,
        config: LoopConfig,
    ) -> str:
        """Build the prompt for the DoD agent."""
        parts = [
            f"Verify if task is COMPLETE: {config.task_id}",
            f"Task path: {config.task_path}",
            f"Iterations completed: {state.current_iteration}",
            "",
            "CRITICAL: You must actually read and verify the task artifacts.",
            "",
            "Steps:",
            "1. Read task-description.md for the overall goals",
            "2. Read ALL user stories in user-stories/",
            "   - Count total acceptance criteria",
            "   - Count how many are marked [x] done",
            "3. Read implementation-plan/ phases",
            "   - Check if all phases are marked complete",
            "",
            "Task is COMPLETE only if:",
            "- ALL user stories have status 'Done'",
            "- ALL acceptance criteria are checked [x]",
            "- ALL implementation phases are complete",
            "",
            "Task is NOT complete if ANY work remains.",
            "",
            'Return JSON: {"task_complete": true/false, "remaining_items": [...], "reasoning": "..."}',
        ]

        return "\n".join(parts)


class LoopError(Exception):
    """Error during loop execution."""

    pass
