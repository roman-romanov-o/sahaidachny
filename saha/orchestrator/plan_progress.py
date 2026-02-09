"""Helpers for updating implementation plan execution progress."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from saha.models.state import ExecutionState, LoopPhase


_PHASE_TO_STAGE = {
    LoopPhase.IMPLEMENTATION: "Implementation",
    LoopPhase.TEST_CRITIQUE: "Test Critique",
    LoopPhase.QA: "QA Verification",
    LoopPhase.CODE_QUALITY: "Code Quality",
    LoopPhase.DOD_CHECK: "DoD Check",
}

_STATUS_SYMBOLS = {
    "pending": "⏳ Pending",
    "in_progress": "🔄 In Progress",
    "passed": "✅ Passed",
    "failed": "❌ Failed",
    "skipped": "⏭️ Skipped",
}

_STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.IGNORECASE)
_ALT_STATUS_LINE_RE = re.compile(r"^Status:\s*(.+)$", re.IGNORECASE)


@dataclass
class PlanPhaseSelection:
    """Represents the selected active implementation phase."""

    phase_path: Path
    updated_context: bool


class PlanProgressUpdater:
    """Update execution progress in implementation plan phase files."""

    def __init__(self, task_path: Path):
        self._task_path = task_path
        self._plan_dir = task_path / "implementation-plan"

    def select_active_phase(self, state: ExecutionState | None = None) -> PlanPhaseSelection | None:
        """Select the active phase file (first incomplete)."""
        if not self._plan_dir.exists():
            return None

        if state:
            stored = state.context.get("current_plan_phase") if state.context else None
            if stored:
                candidate = (self._task_path / stored).resolve()
                if candidate.exists():
                    updated = self._ensure_phase_context(state, candidate)
                    return PlanPhaseSelection(candidate, updated)

        phases = sorted(self._plan_dir.glob("phase-*.md"))
        if not phases:
            return None

        for phase in phases:
            status = self._read_status_line(phase)
            if not status:
                updated = self._ensure_phase_context(state, phase) if state else False
                return PlanPhaseSelection(phase, updated)
            if status.strip().lower() not in {"complete", "completed", "done"}:
                updated = self._ensure_phase_context(state, phase) if state else False
                return PlanPhaseSelection(phase, updated)

        last_phase = phases[-1]
        updated = self._ensure_phase_context(state, last_phase) if state else False
        return PlanPhaseSelection(last_phase, updated)

    def update_execution_progress(
        self,
        phase_path: Path,
        loop_phase: LoopPhase,
        status_kind: str,
        iteration: int,
        note: str | None = None,
        timestamp: datetime | None = None,
        update_status_line: bool = True,
    ) -> bool:
        """Update the execution progress table for a phase."""
        stage = _PHASE_TO_STAGE.get(loop_phase)
        if not stage:
            return False

        status_symbol = _STATUS_SYMBOLS.get(status_kind)
        if not status_symbol:
            raise ValueError(f"Unknown status kind: {status_kind}")

        content = phase_path.read_text()
        trailing_newline = content.endswith("\n")
        lines = content.splitlines()
        changed = False

        if update_status_line:
            status_line_value = stage
            changed |= self._replace_status_line(lines, status_line_value)

        ts = timestamp or datetime.now()
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M")
        note_value = self._normalize_note(note, iteration)
        changed |= self._update_progress_row(lines, stage, status_symbol, timestamp_str, note_value)

        if changed:
            phase_path.write_text("\n".join(lines) + ("\n" if trailing_newline else ""))

        return changed

    def mark_all_complete(self, note: str | None = None) -> int:
        """Mark all phase files as complete and update DoD check row."""
        phases = sorted(self._plan_dir.glob("phase-*.md")) if self._plan_dir.exists() else []
        if not phases:
            return 0

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        count = 0
        for phase in phases:
            content = phase.read_text()
            trailing_newline = content.endswith("\n")
            lines = content.splitlines()
            changed = False

            changed |= self._replace_status_line(lines, "Complete")
            note_value = self._normalize_note(note, 0) if note else "task complete"
            changed |= self._update_progress_row(
                lines,
                "DoD Check",
                _STATUS_SYMBOLS["passed"],
                timestamp_str,
                note_value,
            )

            if changed:
                phase.write_text("\n".join(lines) + ("\n" if trailing_newline else ""))
                count += 1

        return count

    def _ensure_phase_context(self, state: ExecutionState | None, phase_path: Path) -> bool:
        if state is None:
            return False
        relative = phase_path.relative_to(self._task_path).as_posix()
        if state.context.get("current_plan_phase") != relative:
            state.context["current_plan_phase"] = relative
            return True
        return False

    def _read_status_line(self, phase_path: Path) -> str | None:
        content = phase_path.read_text()
        match = _STATUS_LINE_RE.search(content)
        if match:
            return match.group(1).strip()
        match = _ALT_STATUS_LINE_RE.search(content)
        if match:
            return match.group(1).strip()
        return None

    def _replace_status_line(self, lines: list[str], status_value: str) -> bool:
        for idx, line in enumerate(lines):
            if _STATUS_LINE_RE.match(line):
                lines[idx] = f"**Status:** {status_value}"
                return True
            if _ALT_STATUS_LINE_RE.match(line):
                lines[idx] = f"Status: {status_value}"
                return True
        return False

    def _update_progress_row(
        self,
        lines: list[str],
        stage: str,
        status_symbol: str,
        timestamp: str,
        note: str,
    ) -> bool:
        section = self._find_section(lines, "## Execution Progress")
        if not section:
            return False

        start, end = section
        for idx in range(start, end):
            line = lines[idx]
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells:
                continue
            if cells[0].lower() != stage.lower():
                continue

            while len(cells) < 4:
                cells.append("-")

            cells[1] = status_symbol
            cells[2] = timestamp
            cells[3] = note
            lines[idx] = "| " + " | ".join(cells[:4]) + " |"
            return True

        return False

    def _find_section(self, lines: list[str], header: str) -> tuple[int, int] | None:
        start = None
        header_lower = header.lower()
        for idx, line in enumerate(lines):
            if line.strip().lower() == header_lower:
                start = idx
                break
        if start is None:
            return None

        end = len(lines)
        for idx in range(start + 1, len(lines)):
            line = lines[idx].strip()
            if line.startswith("## "):
                end = idx
                break
        return start, end

    def _normalize_note(self, note: str | None, iteration: int) -> str:
        if note:
            cleaned = re.sub(r"\s+", " ", note.strip())
            if len(cleaned) > 120:
                cleaned = cleaned[:117] + "..."
            return cleaned
        if iteration > 0:
            return f"iter {iteration}"
        return "-"

