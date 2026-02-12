"""Codex CLI subprocess runner implementation."""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from saha.runners.base import Runner, RunnerResult
from saha.runners.usage import normalize_token_usage

logger = logging.getLogger(__name__)


class _FileChangeTracker:
    """Track file changes under a root directory."""

    _SKIP_DIRS = {
        ".git",
        ".sahaidachny",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        ".codex",
        ".claude",
    }

    _SKIP_FILES = {".DS_Store"}

    def __init__(self, root: Path) -> None:
        self._root = root
        self._snapshot = self._take_snapshot()

    def diff(self) -> tuple[list[str], list[str]]:
        """Return (files_changed, files_added) relative to the root."""
        new_snapshot = self._take_snapshot()
        if not new_snapshot:
            return [], []

        if not self._snapshot:
            return [], sorted(new_snapshot.keys())

        files_added = [p for p in new_snapshot if p not in self._snapshot]
        files_changed = [
            p
            for p, meta in new_snapshot.items()
            if p in self._snapshot and meta != self._snapshot[p]
        ]

        return sorted(files_changed), sorted(files_added)

    def _take_snapshot(self) -> dict[str, tuple[int, int]]:
        """Snapshot files under the root with (mtime_ns, size)."""
        if not self._root.exists():
            return {}

        snapshot: dict[str, tuple[int, int]] = {}
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in self._SKIP_DIRS]
            for filename in filenames:
                if filename in self._SKIP_FILES:
                    continue
                path = Path(dirpath) / filename
                try:
                    if not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                rel_path = path.relative_to(self._root).as_posix()
                snapshot[rel_path] = (stat.st_mtime_ns, stat.st_size)

        return snapshot


class CodexRunner(Runner):
    """Runner that executes prompts via Codex CLI subprocess."""

    def __init__(
        self,
        model: str | None = None,
        working_dir: Path | None = None,
        sandbox: str | None = "workspace-write",
        dangerously_bypass: bool = False,
    ) -> None:
        self._model = model
        self._working_dir = working_dir or Path.cwd()
        self._sandbox = sandbox
        self._dangerously_bypass = dangerously_bypass

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent-style prompt via Codex CLI.

        Codex CLI does not support native agent specs, so we embed the
        agent spec content (and referenced skills) into the prompt.
        """
        system_prompt = self._extract_system_prompt(agent_spec_path)
        skills_prompt = self._extract_skills_prompt(agent_spec_path)
        full_prompt = self._build_prompt_with_context(prompt, context, system_prompt, skills_prompt)
        return self._run(full_prompt, timeout)

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt via Codex CLI."""
        full_prompt = self._build_prompt_with_context(prompt, None, system_prompt, None)
        return self._run(full_prompt, timeout)

    def is_available(self) -> bool:
        """Check if codex CLI is available."""
        return shutil.which("codex") is not None

    def get_name(self) -> str:
        """Get runner name."""
        if self._model:
            return f"codex-cli ({self._model})"
        return "codex-cli"

    def _run(self, prompt: str, timeout: int) -> RunnerResult:
        """Execute the Codex CLI command."""
        tracker = _FileChangeTracker(self._working_dir)

        output_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                output_file = Path(tmp.name)

            cmd = self._build_command(output_file)

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._working_dir,
            )

            try:
                stdout, stderr = process.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return RunnerResult.failure(
                    f"Command timed out after {timeout} seconds",
                    exit_code=124,
                )
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise

            if process.returncode != 0:
                return RunnerResult(
                    success=False,
                    output=stdout,
                    error=stderr or f"Exit code: {process.returncode}",
                    exit_code=process.returncode,
                )

            raw_stdout = stdout
            text_output = stdout
            if output_file and output_file.exists():
                try:
                    last_message = output_file.read_text()
                    if last_message.strip():
                        text_output = last_message
                except OSError:
                    logger.debug("Failed to read Codex output file")

            structured_output = self._try_parse_json(text_output) or {}
            token_usage = self._extract_token_usage(text_output, structured_output, raw_stdout)
            if token_usage is None:
                token_usage = self._extract_token_usage_from_session_logs()

            files_changed, files_added = tracker.diff()
            if files_changed or files_added:
                structured_output["files_changed"] = files_changed
                structured_output["files_added"] = files_added

            return RunnerResult.success_result(
                output=text_output,
                structured_output=structured_output if structured_output else None,
                token_usage=token_usage,
            )

        except FileNotFoundError:
            return RunnerResult.failure(
                "Codex CLI not found. Is it installed?",
                exit_code=127,
            )
        except Exception as e:
            return RunnerResult.failure(str(e), exit_code=1)
        finally:
            if output_file and output_file.exists():
                try:
                    output_file.unlink()
                except OSError:
                    logger.debug("Failed to remove Codex output file")

    def _build_command(self, output_file: Path) -> list[str]:
        """Build the codex exec command."""
        cmd = [
            "codex",
            "exec",
            "-",  # Read prompt from stdin
            "--output-last-message",
            str(output_file),
            "--color",
            "never",
            "--cd",
            str(self._working_dir),
            "--skip-git-repo-check",
        ]

        if self._model:
            cmd.extend(["--model", self._model])

        if self._dangerously_bypass:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        elif self._sandbox:
            cmd.extend(["--sandbox", self._sandbox])

        return cmd

    def _build_prompt_with_context(
        self,
        prompt: str,
        context: dict[str, Any] | None,
        system_prompt: str | None,
        skills_prompt: str | None,
    ) -> str:
        """Build prompt with optional system prompt, skills, and context."""
        parts: list[str] = []

        prelude_parts: list[str] = []
        if system_prompt:
            prelude_parts.append(system_prompt.strip())
        if skills_prompt:
            prelude_parts.append(skills_prompt.strip())

        if prelude_parts:
            parts.extend(
                [
                    "\n\n".join(prelude_parts),
                    "",
                    "---",
                    "",
                ]
            )

        parts.append(prompt)

        if context:
            parts.extend(
                [
                    "",
                    "## Context",
                    "",
                    "```json",
                    json.dumps(context, indent=2, default=str),
                    "```",
                ]
            )

        return "\n".join(parts)

    def _extract_system_prompt(self, agent_spec_path: Path) -> str | None:
        """Extract system prompt from agent spec markdown file."""
        content = self._read_agent_spec(agent_spec_path)
        if content is None:
            return None

        _, body = self._split_frontmatter(content)
        return body.strip() if body else None

    def _extract_skills_prompt(self, agent_spec_path: Path) -> str | None:
        """Extract and render referenced skills for Codex prompts."""
        content = self._read_agent_spec(agent_spec_path)
        if content is None:
            return None

        frontmatter, _ = self._split_frontmatter(content)
        skill_names = self._parse_skills(frontmatter)
        if not skill_names:
            return None

        skills_dir_candidates = self._candidate_skills_dirs(agent_spec_path)
        rendered_skills: list[str] = []

        for skill_name in skill_names:
            skill_text = self._load_skill_text(skill_name, skills_dir_candidates)
            if not skill_text:
                logger.debug(f"CodexRunner: skill not found: {skill_name}")
                continue
            rendered_skills.append(f"## Skill: {skill_name}\n\n{skill_text}")

        if not rendered_skills:
            return None

        return "\n\n".join(rendered_skills)

    def _read_agent_spec(self, agent_spec_path: Path) -> str | None:
        """Read the agent spec content if available."""
        if not agent_spec_path.exists():
            return None
        return agent_spec_path.read_text()

    def _split_frontmatter(self, content: str) -> tuple[str, str]:
        """Split YAML frontmatter from markdown content."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        return "", content

    def _parse_skills(self, frontmatter: str) -> list[str]:
        """Parse skills list from YAML frontmatter text."""
        if not frontmatter:
            return []

        skills: list[str] = []
        lines = frontmatter.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue
            if line.startswith("skills:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    parts = [p.strip() for p in value.split(",") if p.strip()]
                    skills.extend(parts)
                    i += 1
                    continue
                # Parse YAML list entries following skills:
                i += 1
                while i < len(lines):
                    item_line = lines[i].strip()
                    if not item_line:
                        i += 1
                        continue
                    if item_line.startswith("-"):
                        skill = item_line[1:].strip()
                        if skill:
                            skills.append(skill)
                        i += 1
                        continue
                    if ":" in item_line:
                        break
                    i += 1
                continue
            i += 1

        return skills

    def _candidate_skills_dirs(self, agent_spec_path: Path) -> list[Path]:
        """Return candidate skills directories."""
        candidates: list[Path] = []
        agent_dir = agent_spec_path.parent
        if agent_dir.name == "agents":
            candidates.append(agent_dir.parent / "skills")
        candidates.append(self._working_dir / "claude_plugin" / "skills")
        return candidates

    def _load_skill_text(self, skill_name: str, candidates: list[Path]) -> str | None:
        """Load skill markdown body by searching candidate directories."""
        for base_dir in candidates:
            skill_path = base_dir / skill_name / "SKILL.md"
            if not skill_path.exists():
                continue
            try:
                content = skill_path.read_text()
            except OSError:
                continue
            _, body = self._split_frontmatter(content)
            return body.strip()
        return None

    def _try_parse_json(self, output: str) -> dict[str, Any] | None:
        """Try to extract JSON from output."""
        json_block_pattern = r"```json\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, output, re.DOTALL)

        if matches:
            for match in reversed(matches):
                try:
                    parsed = json.loads(match.strip())
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        lines = output.strip().split("\n")
        json_blocks: list[list[str]] = []
        current_block: list[str] = []
        brace_count = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("{") and brace_count == 0:
                brace_count = stripped.count("{") - stripped.count("}")
                current_block = [line]
                if brace_count == 0:
                    json_blocks.append(current_block)
                    current_block = []
            elif brace_count > 0:
                current_block.append(line)
                brace_count += stripped.count("{") - stripped.count("}")
                if brace_count <= 0:
                    json_blocks.append(current_block)
                    current_block = []
                    brace_count = 0

        for block in reversed(json_blocks):
            try:
                parsed = json.loads("\n".join(block))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        return None

    def _extract_token_usage(
        self,
        text_output: str,
        structured_output: dict[str, Any] | None,
        raw_stdout: str,
    ) -> dict[str, int] | None:
        """Extract token usage from codex outputs."""
        raw_candidates: list[dict[str, Any]] = []

        if structured_output:
            self._collect_usage_candidates(structured_output, raw_candidates)

        for payload in self._parse_json_payloads(raw_stdout):
            self._collect_usage_candidates(payload, raw_candidates)

        if text_output and text_output != raw_stdout:
            for payload in self._parse_json_payloads(text_output):
                self._collect_usage_candidates(payload, raw_candidates)

        if not raw_candidates:
            return None

        return normalize_token_usage(raw_candidates[-1])

    def _parse_json_payloads(self, text: str) -> list[Any]:
        """Parse JSON payloads from a string (single JSON or JSONL)."""
        payloads: list[Any] = []
        if not text:
            return payloads

        stripped = text.strip()
        if stripped:
            try:
                payloads.append(json.loads(stripped))
                return payloads
            except json.JSONDecodeError:
                pass

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        parsed_block = self._try_parse_json(text)
        if parsed_block is not None:
            payloads.append(parsed_block)

        return payloads

    def _collect_usage_candidates(self, payload: Any, raw_candidates: list[dict[str, Any]]) -> None:
        """Collect raw usage dicts from nested payloads."""
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict):
                raw_candidates.append(usage)
            token_usage = payload.get("token_usage")
            if isinstance(token_usage, dict):
                raw_candidates.append(token_usage)

            normalized = normalize_token_usage(payload)
            if normalized:
                raw_candidates.append(payload)

            for value in payload.values():
                self._collect_usage_candidates(value, raw_candidates)
        elif isinstance(payload, list):
            for item in payload:
                self._collect_usage_candidates(item, raw_candidates)

    def _extract_token_usage_from_session_logs(self) -> dict[str, int] | None:
        """Best-effort extraction from Codex session JSONL logs."""
        codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        sessions_dir = codex_home / "sessions"
        if not sessions_dir.exists():
            return None

        log_files = sorted(
            sessions_dir.rglob("rollout-*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not log_files:
            return None

        latest_log = log_files[0]
        try:
            lines = latest_log.read_text().splitlines()
        except OSError:
            return None

        raw_candidates: list[dict[str, Any]] = []
        for line in lines[-200:]:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._collect_usage_candidates(payload, raw_candidates)

        if not raw_candidates:
            return None

        return normalize_token_usage(raw_candidates[-1])
