# US-006: Implement Graceful Degradation for Missing CLIs

**Priority:** Should Have
**Status:** Draft
**Persona:** Sahaidachny Developer
**Estimated Complexity:** S (2-3 hours)

## User Story

As a **Sahaidachny Developer**,
I want **the system to gracefully handle missing or unavailable CLIs**,
So that **users get clear error messages and can continue working with available platforms**.

## Acceptance Criteria

1. **Given** Codex CLI is not installed
   **When** user runs `saha run task-01 --runner codex`
   **Then** clear error message is shown: "Codex CLI not found. Install with: npm install -g @openai/codex"

2. **Given** Gemini CLI is not installed
   **When** user runs `saha run task-01 --runner gemini`
   **Then** clear error message is shown: "Gemini CLI not found. Install with: npm install -g @google/gemini-cli"

3. **Given** API key is missing for selected runner
   **When** user attempts to run execution loop
   **Then** clear error message is shown: "OPENAI_API_KEY not set. See: docs/setup/codex.md"

4. **Given** user configured `fallback_runner=codex` in settings and preferred runner (claude) is unavailable
   **When** execution starts
   **Then** system tries codex fallback and shows warning "Claude unavailable, using Codex fallback" (if codex also unavailable, raises clear error listing all tried runners)

5. **Given** runner becomes unavailable mid-execution
   **When** agent invocation fails
   **Then** state is saved, loop stops gracefully, user can resume with different runner

## Edge Cases

1. **CLI installed but wrong version**
   - Trigger: User has old CLI version with incompatible flags
   - Expected behavior: Version check, clear upgrade instructions

2. **API key exists but is invalid**
   - Trigger: Expired or revoked API key
   - Expected behavior: Auth error with instructions to refresh credentials

3. **All runners unavailable**
   - Trigger: None of the CLIs are installed
   - Expected behavior: Clear setup guide, list all required CLIs

## Technical Notes

**Implementation approach:**

**1. CLI availability checks** (startup validation):
```python
# saha/runners/codex.py
def is_available(self) -> bool:
    """Check if codex CLI is available."""
    return shutil.which("codex") is not None
```

**2. Clear error messages** (runner registry):
```python
# saha/runners/registry.py
def get_runner(self, runner_type: RunnerType) -> Runner:
    if runner_type == RunnerType.CODEX:
        if not shutil.which("codex"):
            raise RunnerUnavailableError(
                "Codex CLI not found.\n"
                "Install: npm install -g @openai/codex\n"
                "Docs: https://developers.openai.com/codex/cli/"
            )
```

**3. Fallback mechanism** (orchestrator):
```python
# saha/orchestrator/loop.py
def _get_runner_with_fallback(self) -> Runner:
    try:
        return self.registry.get_runner(self.config.runner)
    except RunnerUnavailableError as e:
        if self.config.fallback_runner:
            logger.warning(f"{e}. Falling back to {self.config.fallback_runner}")
            return self.registry.get_runner(self.config.fallback_runner)
        raise
```

**4. State persistence on error** (state manager):
```python
# saha/orchestrator/state.py
def mark_stopped(self, state: ExecutionState, reason: str):
    """Mark execution as stopped (can be resumed)."""
    state.current_phase = LoopPhase.STOPPED
    state.context["stop_reason"] = reason
    self.save(state)
```

**Key files to modify:**
- `saha/runners/base.py` - Add `RunnerUnavailableError` exception
- `saha/runners/codex.py` - Enhance `is_available()` with version check
- `saha/runners/gemini.py` - Enhance `is_available()` with version check
- `saha/runners/registry.py` - Add fallback logic
- `saha/orchestrator/loop.py` - Handle runner unavailability gracefully
- `saha/config/settings.py` - Add `fallback_runner` configuration

**Error message templates:**
```
CLI Not Found:
  {runner} CLI not found in PATH.

  Install:
    {installation_command}

  Verify:
    {cli_name} --version

  Docs:
    {documentation_url}

API Key Missing:
  {env_var_name} not set.

  Setup:
    export {env_var_name}="your-api-key-here"

  Get API key:
    {signup_url}

  Docs:
    {setup_guide_url}
```

## Dependencies

- **Requires:**
  - US-001 completed (Codex validation)
  - US-002 completed (Gemini fixes)
- **Enables:**
  - Better user experience
  - Easier onboarding for new users

## Questions

- [ ] Should fallback be automatic or require explicit user confirmation?
- [ ] What's the priority order for fallbacks? (Claude → Codex → Gemini?)
- [ ] Should we validate API keys at startup or on first use?

## Related

- Task: [task-description.md](../task-description.md)
- Research: [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md)
- Research: [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)
