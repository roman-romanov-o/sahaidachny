# Phase 04: Error Handling & Polish

**Status:** Not Started
**Estimated Effort:** S (4-6 hours)
**Dependencies:** Phase 03 (E2E tests passing, core functionality validated)

## Objective

Improve user experience when things go wrong by implementing graceful degradation for missing CLIs, clear error messages with actionable guidance, and comprehensive troubleshooting documentation.

## Scope

### Stories Included

| Story | Priority | Complexity | Estimated Hours |
|-------|----------|------------|-----------------|
| US-006: Graceful Degradation | Should Have | S | 2-3h |
| US-007: Error Messages & Troubleshooting | Should Have | S | 2-3h |

**Total: 4-6 hours**

## Implementation Steps

### Step 1: Implement CLI Availability Checks

**Description:** Enhance `is_available()` methods to check CLI availability and version compatibility.

**Files to Modify:**
- `saha/runners/codex.py` - Enhance `is_available()` with version check
- `saha/runners/gemini.py` - Enhance `is_available()` with version check
- `saha/runners/claude.py` - Add version check for consistency

**Implementation Pattern:**

**Enhanced is_available():**
```python
# saha/runners/codex.py
import shutil
import subprocess
from typing import Optional

def is_available(self) -> bool:
    """Check if Codex CLI is available and compatible."""
    try:
        # Check CLI exists
        if not shutil.which("codex"):
            logger.debug("Codex CLI not found in PATH")
            return False

        # Check version (optional but recommended)
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("Codex CLI version check failed")
            return False

        # Parse version (optional validation)
        version = result.stdout.strip()
        logger.debug(f"Codex CLI version: {version}")

        return True

    except Exception as e:
        logger.debug(f"Codex availability check failed: {e}")
        return False
```

**Acceptance Criteria:**
- [ ] `is_available()` never raises exceptions
- [ ] Returns `False` when CLI not in PATH
- [ ] Returns `False` when CLI version check fails
- [ ] Logs debug messages for troubleshooting
- [ ] Version information captured (for debugging)

**Tests:**
- TC-INT-011: is_available() never raises exceptions (already exists)
- TC-INT-016: Codex is_available() behavior (already exists)
- Manual validation with and without CLI installed

---

### Step 2: Create Custom Exception Classes

**Description:** Define custom exception classes with structured error information.

**Files to Create:**
- `saha/errors.py` - Custom exception hierarchy

**Exception Classes:**

```python
# saha/errors.py
from dataclasses import dataclass
from typing import Optional

class SahaidachnyError(Exception):
    """Base exception for all Sahaidachny errors."""
    pass

@dataclass
class RunnerUnavailableError(SahaidachnyError):
    """Runner CLI is not available or not configured."""
    runner_name: str
    reason: str
    installation_command: str
    documentation_url: str

    def __str__(self) -> str:
        return f"""
╭─ Error: {self.runner_name} CLI Not Available
│
│  {self.reason}
│
├─ Install
│  {self.installation_command}
│
├─ Verify
│  {self.runner_name.lower()} --version
│
╰─ Docs: {self.documentation_url}
""".strip()

@dataclass
class AuthenticationError(SahaidachnyError):
    """API authentication failed."""
    runner_name: str
    env_var_name: str
    signup_url: str
    setup_guide_url: str

    def __str__(self) -> str:
        return f"""
╭─ Error: Authentication Failed
│
│  {self.env_var_name} not set or invalid.
│
├─ Setup
│  export {self.env_var_name}="your-api-key-here"
│
├─ Get API Key
│  {self.signup_url}
│
├─ Security
│  • Never commit API keys to git
│  • Use .env file (excluded in .gitignore)
│  • Rotate keys regularly
│
╰─ Docs: {self.setup_guide_url}
""".strip()

class AgentTimeoutError(SahaidachnyError):
    """Agent execution exceeded timeout."""
    pass

class StateSaveError(SahaidachnyError):
    """Failed to save execution state."""
    pass
```

**Acceptance Criteria:**
- [ ] Base `SahaidachnyError` exception defined
- [ ] `RunnerUnavailableError` with structured fields
- [ ] `AuthenticationError` with structured fields
- [ ] Pretty-printed error messages with box drawing
- [ ] All errors inherit from base exception

---

### Step 3: Implement Runner Fallback Mechanism

**Description:** Add fallback logic to try alternative runners when preferred runner unavailable.

**Files to Modify:**
- `saha/config/settings.py` - Add `fallback_runner` configuration
- `saha/runners/registry.py` - Add fallback logic
- `saha/orchestrator/loop.py` - Use fallback on runner unavailability

**Configuration:**
```python
# saha/config/settings.py
class Settings(BaseSettings):
    # ...existing settings...

    # Runner fallback configuration
    fallback_runner: Optional[str] = None  # e.g., "codex" or "gemini"
    fallback_enabled: bool = True  # Allow automatic fallback

    @validator("fallback_runner")
    def validate_fallback_runner(cls, v):
        if v and v not in ["claude", "codex", "gemini"]:
            raise ValueError(f"Invalid fallback runner: {v}")
        return v
```

**Fallback Logic:**
```python
# saha/orchestrator/loop.py
def _get_runner_with_fallback(self) -> Runner:
    """Get runner with automatic fallback on unavailability."""
    try:
        runner = self.registry.get_runner(self.config.runner)
        if not runner.is_available():
            raise RunnerUnavailableError(
                runner_name=runner.get_name(),
                reason=f"{runner.get_name()} CLI not found in PATH",
                installation_command=self._get_install_command(runner.get_name()),
                documentation_url=self._get_docs_url(runner.get_name()),
            )
        return runner

    except RunnerUnavailableError as e:
        # Try fallback if configured
        if self.config.fallback_runner and self.config.fallback_enabled:
            logger.warning(f"{e.reason}. Trying fallback: {self.config.fallback_runner}")
            fallback = self.registry.get_runner(self.config.fallback_runner)

            if fallback.is_available():
                logger.info(f"Using fallback runner: {self.config.fallback_runner}")
                return fallback
            else:
                logger.error(f"Fallback runner also unavailable: {self.config.fallback_runner}")

        # No fallback or fallback failed
        raise
```

**Acceptance Criteria:**
- [ ] `fallback_runner` configuration option added
- [ ] Fallback logic tries alternative runner when primary unavailable
- [ ] Warning logged when using fallback
- [ ] Error raised if fallback also unavailable
- [ ] User can disable fallback with `fallback_enabled=False`

**Tests:**
- TC-INT-006: Fallback to available runner when preferred unavailable
- TC-INT-007: Error when all runners unavailable
- TC-INT-008: Fallback disabled when configured

---

### Step 4: Implement State Persistence on Error

**Description:** Ensure execution state is saved when runner becomes unavailable, allowing resume with different runner.

**Files to Modify:**
- `saha/orchestrator/state.py` - Add `mark_stopped()` method
- `saha/orchestrator/loop.py` - Save state on runner errors

**State Persistence:**
```python
# saha/orchestrator/state.py
def mark_stopped(self, state: ExecutionState, reason: str):
    """Mark execution as stopped (can be resumed)."""
    state.current_phase = LoopPhase.STOPPED
    state.stopped_at = datetime.now().isoformat()
    state.context["stop_reason"] = reason
    self.save(state)
    logger.info(f"Execution stopped: {reason}")

# saha/orchestrator/loop.py
def run(self):
    """Run execution loop with state persistence on errors."""
    try:
        return self._run_loop()
    except RunnerUnavailableError as e:
        # Save state before failing
        self.state_manager.mark_stopped(
            self.state,
            reason=f"Runner unavailable: {e.runner_name}"
        )
        logger.error(f"Runner unavailable. State saved. Resume with different runner.")
        raise
    except Exception as e:
        # Save state on unexpected errors
        self.state_manager.mark_stopped(self.state, reason=f"Error: {str(e)}")
        raise
```

**Acceptance Criteria:**
- [ ] State saved on runner unavailability
- [ ] State saved on unexpected errors
- [ ] Stop reason recorded in state
- [ ] User can resume with different runner
- [ ] Clear message about resumption

**Tests:**
- Manual validation (simulate runner unavailability mid-execution)

---

### Step 5: Create Error Message Templates

**Description:** Define consistent error message templates for common scenarios.

**Files to Modify:**
- `saha/errors.py` - Add template methods

**Error Templates:**

```python
# saha/errors.py

ERROR_TEMPLATES = {
    "cli_not_found": """
╭─ Error: {cli_name} CLI Not Found
│
│  The '{cli_command}' command is not available in your PATH.
│
├─ Install
│  {install_command}
│
├─ Verify
│  {cli_command} --version
│
├─ Setup Guide
│  {setup_guide_url}
│
╰─ Troubleshooting: {troubleshooting_url}#cli-not-found
""",
    "auth_failure": """
╭─ Error: Authentication Failed
│
│  API authentication failed for {runner_name}.
│
├─ Cause
│  {env_var} environment variable is not set or is invalid.
│
├─ Fix
│  1. Get API key: {signup_url}
│  2. Add to .env file (NEVER commit this file!):
│     {env_var}="your-key-here"
│  3. Load environment:
│     source .env
│  4. Verify:
│     {cli_command} --version
│
├─ Security
│  • Never commit API keys to git
│  • Use .env file (excluded in .gitignore)
│  • Rotate keys regularly
│
╰─ Docs: {troubleshooting_url}#auth-failure
""",
    "timeout": """
╭─ Error: Agent Timeout
│
│  Agent execution exceeded {timeout}s timeout.
│
├─ Possible Causes
│  • Complex task taking longer than expected
│  • Network latency or API slowness
│  • Infinite loop or stuck process
│
├─ Fix
│  1. Increase timeout in config:
│     SAHA_AGENT_TIMEOUT={suggested_timeout}
│
│  2. Simplify task or break into smaller steps
│
│  3. Check network connectivity
│
╰─ Docs: {troubleshooting_url}#timeout
""",
}

def format_error(template_name: str, **kwargs) -> str:
    """Format error message from template."""
    template = ERROR_TEMPLATES.get(template_name)
    if not template:
        return f"Error: {kwargs}"
    return template.format(**kwargs).strip()
```

**Acceptance Criteria:**
- [ ] Error templates defined for common scenarios
- [ ] Templates include clear description, cause, fix steps
- [ ] Templates link to troubleshooting docs
- [ ] Consistent formatting with box drawing characters

---

### Step 6: Create Troubleshooting Guide

**Description:** Write comprehensive troubleshooting documentation.

**Files to Create:**
- `docs/troubleshooting.md` - Main troubleshooting guide

**Guide Structure:**

```markdown
# Troubleshooting Guide

## Quick Diagnostics

### Check CLI Installation

```bash
claude --version   # Should show version
codex --version    # Should show version
gemini --version   # Should show version
```

### Check API Keys

```bash
echo $ANTHROPIC_API_KEY | grep -o '^.\{10\}'  # First 10 chars
echo $OPENAI_API_KEY | grep -o '^.\{10\}'
echo $GEMINI_API_KEY | grep -o '^.\{10\}'
```

## Common Errors

### 1. CLI Not Found

**Error:** `CodexCLINotFoundError: Codex CLI is not installed`

**Cause:** CLI not installed or not in PATH

**Solution:**
1. Install CLI:
   ```bash
   npm install -g @openai/codex
   ```

2. Verify installation:
   ```bash
   codex --version
   ```

3. Ensure CLI in PATH:
   ```bash
   echo $PATH | grep codex
   ```

### 2. Authentication Failed

**Error:** `AuthenticationError: API authentication failed`

**Cause:** API key not set or invalid

**Solution:**
1. Get API key from provider
2. Add to `.env` file (NEVER commit this file!):
   ```bash
   # Edit .env
   OPENAI_API_KEY="sk-..."
   ```
3. Load environment:
   ```bash
   source .env  # or use direnv/dotenv
   ```
4. Verify with test request:
   ```bash
   codex exec - <<< "echo test"
   ```

### 3. Agent Timeout

**Error:** `TimeoutError: Agent execution exceeded 300s`

**Cause:** Agent taking longer than configured timeout

**Solution:**
1. Increase timeout in config:
   ```bash
   export SAHA_AGENT_TIMEOUT=600
   ```
2. Simplify task requirements
3. Check network connectivity

## Runner-Specific Issues

### Claude Code

**Issue:** Permission denied errors
**Fix:** Check Claude Code permission mode, adjust in settings

### Codex

**Issue:** File tracking doesn't work
**Fix:** Ensure working directory has write permissions

### Gemini

**Issue:** Unexpected JSON parsing errors
**Fix:** Upgrade to latest Gemini CLI version

## When to File a Bug Report

File a bug if:
- Error persists after following troubleshooting steps
- Error message is unclear or incorrect
- You found a workaround we should document

Include:
- Full error message
- Output of `saha version`
- Output of diagnostic commands above
- Minimal reproduction steps
```

**Acceptance Criteria:**
- [ ] Troubleshooting guide created with diagnostic commands
- [ ] Common errors documented with solutions
- [ ] Runner-specific issues covered
- [ ] Clear guidance on when to file bugs

---

### Step 7: Update Error Handling in Runners

**Description:** Update runner implementations to raise custom exceptions.

**Files to Modify:**
- `saha/runners/codex.py` - Raise custom exceptions
- `saha/runners/gemini.py` - Raise custom exceptions
- `saha/runners/claude.py` - Raise custom exceptions

**Updated Error Handling:**

```python
# saha/runners/codex.py
from saha.errors import RunnerUnavailableError, AuthenticationError, format_error

def run_prompt(self, prompt: str, timeout: int = 300) -> RunnerResult:
    """Run prompt with proper error handling."""
    # Check availability
    if not self.is_available():
        raise RunnerUnavailableError(
            runner_name="Codex",
            reason="Codex CLI not found in PATH",
            installation_command="npm install -g @openai/codex",
            documentation_url="https://developers.openai.com/codex/cli/",
        )

    # Check authentication
    if not os.getenv("OPENAI_API_KEY"):
        raise AuthenticationError(
            runner_name="Codex",
            env_var_name="OPENAI_API_KEY",
            signup_url="https://platform.openai.com/api-keys",
            setup_guide_url="https://sahaidachny.dev/setup/codex",
        )

    # Execute with timeout
    try:
        result = self._execute_command(prompt, timeout)
        return result
    except subprocess.TimeoutExpired:
        raise AgentTimeoutError(
            format_error(
                "timeout",
                timeout=timeout,
                suggested_timeout=timeout * 2,
                troubleshooting_url="https://sahaidachny.dev/troubleshooting",
            )
        )
```

**Acceptance Criteria:**
- [ ] All runners raise custom exceptions
- [ ] Error messages use templates
- [ ] Clear, actionable error information provided
- [ ] Troubleshooting links included

**Tests:**
- TC-INT-016: Codex auth failure message (already exists)
- TC-INT-017: Clear error when CLI unavailable (already exists)
- Manual validation of error message formatting

## Definition of Done

Phase is complete when:
- [ ] **CLI availability checks:** Enhanced `is_available()` with version validation
- [ ] **Custom exceptions:** `RunnerUnavailableError`, `AuthenticationError`, etc. defined
- [ ] **Fallback mechanism:** Automatic fallback to alternative runner works
- [ ] **State persistence:** State saved on errors, resumption with different runner works
- [ ] **Error templates:** Consistent, actionable error messages for common scenarios
- [ ] **Troubleshooting guide:** Comprehensive docs with diagnostics and solutions
- [ ] **Updated error handling:** All runners raise custom exceptions with clear messages
- [ ] **Tests pass:** Existing integration tests validate graceful degradation

**Quality Gates:**
```bash
# Validate error message formatting
python -c "
from saha.errors import RunnerUnavailableError
err = RunnerUnavailableError(
    runner_name='Codex',
    reason='CLI not found',
    installation_command='npm install -g @openai/codex',
    documentation_url='https://example.com'
)
print(err)
"

# Test fallback mechanism
export SAHA_FALLBACK_RUNNER=codex
saha run task-01  # Should fallback if Claude unavailable

# Verify troubleshooting guide completeness
grep -E '(CLI Not Found|Authentication Failed|Timeout)' docs/troubleshooting.md
```

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Error messages too verbose | Medium | Low | User testing; adjust verbosity based on feedback |
| Fallback mechanism too automatic | Low | Medium | Require explicit configuration; log fallback clearly |
| Troubleshooting guide becomes outdated | High | Medium | Include in PR review checklist; update with each CLI version |
| Custom exceptions break existing code | Low | High | Comprehensive testing; backward compatibility where possible |

## Notes

**Design philosophy:**
- Errors should be **informative** (what went wrong)
- Errors should be **actionable** (how to fix)
- Errors should be **educational** (why it matters)
- Errors should **link to docs** (deeper guidance)

**Error message principles:**
- Start with clear description (what failed)
- Explain root cause (why it failed)
- Provide specific fix steps (how to resolve)
- Include examples when helpful
- Link to troubleshooting docs

**Graceful degradation strategy:**
- Try preferred runner first
- Fall back to configured alternative
- Save state if all runners fail
- Provide clear instructions for recovery

**Testing error handling:**
- Unit tests for exception formatting
- Integration tests for fallback mechanism
- Manual tests for error message clarity
- User testing for troubleshooting guide effectiveness

## Related

- **Stories:** [US-006](../user-stories/US-006-graceful-degradation.md), [US-007](../user-stories/US-007-error-messages-troubleshooting.md)
- **Research:** [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md), [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)
- **Test Specs:** [integration/02-runner-compliance.md](../test-specs/integration/02-runner-compliance.md)
- **Previous Phase:** [Phase 03: E2E Validation](phase-03-e2e-validation.md)
