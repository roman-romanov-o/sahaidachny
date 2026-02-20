# Implementation Plan

Phased execution plan for TASK-01: Multi-Platform Support for Agentic Coding.

## Overview

| Phase | Name | Status | Stories | Estimated Effort |
|-------|------|--------|---------|------------------|
| [01](phase-01-runner-validation.md) | Runner Validation | ✅ Complete (iter 2) | US-001, US-002 | M (6-10h) |
| [02](phase-02-test-infrastructure.md) | Test Infrastructure | Not Started | US-003, US-004 | M (5-7h) |
| [03](phase-03-e2e-validation.md) | E2E Validation | Not Started | US-005 | M (6-8h) |
| [04](phase-04-error-handling.md) | Error Handling & Polish | Not Started | US-006, US-007 | S (4-6h) |

**Total Estimated Effort:** 21-31 hours

## Dependency Graph

```
Phase 01: Runner Validation
    ↓
Phase 02: Test Infrastructure
    ↓
Phase 03: E2E Validation
    ↓
Phase 04: Error Handling & Polish
```

## Phase Summaries

### Phase 01: Runner Validation (6-10h) ✅ COMPLETE

**Objective:** Validate Codex runner works as-is and fix confirmed bugs in Gemini runner.

**Key Deliverables (Iteration 2):**
- ✅ Created shared utilities in `saha/runners/_utils.py`
  - `FileChangeTracker` class for file change detection
  - `build_prompt_with_context()` for prompt assembly
  - `build_skills_prompt()` for skill injection
  - `extract_system_prompt()` for spec parsing
  - `try_parse_json()` for robust JSON extraction
- ✅ Refactored Codex runner to use shared utilities
- ✅ Fixed Gemini runner (all 4 bugs):
  - ✅ Remove `--yolo` flag (never added)
  - ✅ Add file change tracking via `FileChangeTracker`
  - ✅ Add skill loading via `build_skills_prompt()`
  - ✅ Improve JSON parsing via `try_parse_json()`
- ✅ Created integration tests

**Success Criteria:**
- ✅ Both Codex and Gemini runners properly implemented
- ✅ No regressions in Claude runner (backward compat maintained)
- ✅ Ready for test infrastructure (Phase 02)

### Phase 02: Test Infrastructure (5-7h)

**Objective:** Build authenticated Docker container fixtures and fast smoke tests.

**Key Deliverables:**
- Docker container fixtures with API key injection
- Container infrastructure tests (5 tests)
- Smoke tests for all 3 runners (3 tests)
- Unit tests for runner utilities (23 tests)
- Integration tests for runner compliance (10 tests)

**Success Criteria:**
- All container tests pass
- Smoke tests pass on all 3 runners in <2 min total
- Unit tests pass in <5s
- Ready for E2E tests

### Phase 03: E2E Validation (6-8h)

**Objective:** Write comprehensive end-to-end tests validating complete execution workflows.

**Key Deliverables:**
- Test project fixture (simple Python project)
- Full loop happy path tests (3 runners)
- QA retry tests with fix_info
- Code quality retry tests
- State resumption tests
- 4-level verification (Process, Artifacts, Functional, Structured)

**Success Criteria:**
- Full loop tests pass on all 3 runners
- Tests complete in <10 min per runner
- QA and quality retry mechanisms work
- State resumption works
- Cost per test run <$0.65

### Phase 04: Error Handling & Polish (4-6h)

**Objective:** Improve UX with graceful degradation and clear error messages.

**Key Deliverables:**
- Enhanced `is_available()` with version checks
- Custom exception classes with structured errors
- Fallback mechanism to alternative runners
- State persistence on errors
- Error message templates
- Troubleshooting guide

**Success Criteria:**
- Clear error messages for common failures
- Fallback to alternative runner works
- State saved on errors (can resume)
- Comprehensive troubleshooting docs

## Critical Path

The following items block all downstream work:

1. **Phase 01, Step 1:** Validate Codex runner works
   - Blocks: Gemini fixes (need reference implementation)
   - Risk: If Codex has bugs, impacts timeline

2. **Phase 01, Step 2:** Fix Gemini runner bugs
   - Blocks: All test phases
   - Risk: Copy-paste errors from Codex adaptation

3. **Phase 02, Step 1:** Docker container fixtures
   - Blocks: All E2E tests
   - Risk: Container startup too slow

4. **Phase 03, Step 2:** Full loop happy path tests
   - Blocks: Confidence in multi-platform support
   - Risk: LLM non-determinism causes flaky tests

## Timeline Visualization

```
Week 1: Phase 01 ████████░░░░░░░░░░░░░░░░░░░░░░
Week 2: Phase 02 ░░░░░░░░████████░░░░░░░░░░░░░░░░
Week 3: Phase 03 ░░░░░░░░░░░░░░░░████████░░░░░░░░
Week 4: Phase 04 ░░░░░░░░░░░░░░░░░░░░░░░░██████░░
```

**Estimated Duration:** 3-4 weeks (part-time, ~8h/week)

## Risks Summary

| Phase | Key Risks | Mitigation |
|-------|-----------|------------|
| 01 | Codex runner has undiscovered bugs | Thorough manual testing; budget extra time |
| 02 | Docker startup too slow (>1 min) | Use module scope; optimize base image |
| 03 | LLM non-determinism causes flaky tests | Clear requirements; retry logic; accept variations |
| 04 | Error messages too verbose | User testing; iterate based on feedback |

## Execution Notes

### Prerequisites

Before starting Phase 01:
- [ ] Install Claude Code CLI (`claude --version` works)
- [ ] Install Codex CLI (`npm install -g @openai/codex`)
- [ ] Install Gemini CLI (`npm install -g @google/gemini-cli`)
- [ ] Set up API keys in `.env` file:
  ```bash
  # Copy template and fill in your keys
  cp .env.example .env
  # Edit .env with your actual API keys (NEVER commit this file!)
  ```
- [ ] Docker installed and daemon running
- [ ] Python 3.11+ with development dependencies

### Development Workflow

**For each phase:**
1. Read phase document thoroughly
2. Set phase status to "In Progress"
3. Complete steps sequentially (unless parallelizable)
4. Run quality gates after each step
5. Mark step complete when DoD met
6. Update phase status to "Complete" when all steps done
7. Update task README with progress

**Quality gates at each phase:**
```bash
# Lint and type check
ruff check saha/runners/
ty check saha/runners/

# Run tests
pytest tests/ -v

# Verify no regressions
pytest tests/ -k "not slow"  # Fast tests only
```

### Testing Strategy

**Phase 01 (Manual):**
- Manual validation scripts
- No automated tests yet

**Phase 02 (Automated):**
- Unit tests (fast, mocked)
- Integration tests (real CLIs, containers)
- Smoke tests (quick E2E validation)

**Phase 03 (E2E):**
- Full loop tests (expensive, comprehensive)
- 4-level verification
- Recovery scenarios

**Phase 04 (Polish):**
- Error handling validation
- Manual UX testing
- Documentation review

### Cost Management

**Estimated costs per phase:**
- Phase 01: $0 (manual validation)
- Phase 02: $0.10-0.20 (smoke tests)
- Phase 03: $2-5 (multiple full loop runs during development)
- Phase 04: $0.10-0.20 (error handling validation)

**Total development cost:** ~$2.20-5.40

**Per-test-run cost (after development):** ~$0.30-0.65

**Cost optimization:**
- Use smallest models (Haiku, GPT-4o-mini, Flash)
- Run expensive tests less frequently
- Cache test results when possible

## Success Metrics

### Must-Have (Phases 1-3)

Task is successful when:
- [ ] Codex runner validated and working
- [ ] Gemini runner bugs fixed
- [ ] E2E tests pass for all 3 runners (Claude, Codex, Gemini)
- [ ] Full loop test completes in <15 minutes per runner
- [ ] All 6 success criteria from task-description.md met

### Should-Have (Phase 4)

Enhanced UX when:
- [ ] Clear error messages for all common failure scenarios
- [ ] Troubleshooting guide with >80% issue resolution rate
- [ ] Graceful fallback prevents hard failures

## Related Documents

- **Task Description:** [task-description.md](../task-description.md)
- **User Stories:** [user-stories/](../user-stories/)
- **Test Specifications:** [test-specs/](../test-specs/)
- **API Contracts:** [api-contracts/](../api-contracts/)
- **Research Reports:** [research/](../research/)
- **Verification Report:** [verification-report.md](../verification-report.md)

## Phase Files

- [Phase 01: Runner Validation](phase-01-runner-validation.md)
- [Phase 02: Test Infrastructure](phase-02-test-infrastructure.md)
- [Phase 03: E2E Validation](phase-03-e2e-validation.md)
- [Phase 04: Error Handling & Polish](phase-04-error-handling.md)
