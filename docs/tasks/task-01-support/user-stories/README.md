# User Stories

User stories define features from the user's perspective.

## Contents

| ID | Title | Priority | Status | Complexity |
|----|-------|----------|--------|------------|
| US-001 | Validate Codex Runner with Real CLI | Must Have | Draft | S (2-4h) |
| US-002 | Fix Gemini Runner Bugs | Must Have | Draft | M (4-6h) |
| US-003 | Create Authenticated Container Test Infrastructure | Must Have | Draft | M (3-4h) |
| US-004 | Write Smoke Tests for All Runners | Must Have | Draft | S (2-3h) |
| US-005 | Write Full Loop E2E Tests | Must Have | Draft | L (6-8h) |
| US-006 | Implement Graceful Degradation for Missing CLIs | Should Have | Draft | S (2-3h) |
| US-007 | Improve Error Messages and Add Troubleshooting Guide | Should Have | Draft | S (2-3h) |

**Total Estimated Effort:** 21-32 hours

## Story Map

### Runner Validation & Fixes (Must Have)
Critical path for enabling multi-platform support:

- **US-001: Validate Codex Runner** (2-4h)
  - Test with real Codex CLI
  - Verify file tracking, skill loading, agent invocation
  - Research shows 80% confidence it already works

- **US-002: Fix Gemini Runner** (4-6h)
  - Remove `--yolo` flag (doesn't exist)
  - Add file change tracking (copy from Codex)
  - Add skill loading (copy from Codex)
  - Improve JSON parsing (copy from Codex)

### E2E Testing Infrastructure (Must Have)
Foundation for validating all runners work correctly:

- **US-003: Authenticated Container Infrastructure** (3-4h)
  - Docker containers with API key injection
  - Environment variable authentication
  - Auto-skip when credentials missing
  - Module-scoped fixtures for performance

- **US-004: Smoke Tests** (2-3h)
  - Fast validation (<30s per runner)
  - Simple agent invocations
  - Verify basic functionality before expensive tests

- **US-005: Full Loop E2E Tests** (6-8h)
  - Complete workflow: Implementer → QA → Quality → Manager → DoD
  - Test with real "add string utils" feature
  - 4-level verification (process, artifacts, functional, structured)
  - QA/quality failure recovery testing

### Error Handling & UX (Should Have)
Improve user experience when things go wrong:

- **US-006: Graceful Degradation** (2-3h)
  - Handle missing CLIs gracefully
  - Clear error messages with installation instructions
  - Automatic fallback to available runners
  - State persistence on failure

- **US-007: Error Messages & Troubleshooting** (2-3h)
  - Structured error message templates
  - Comprehensive troubleshooting guide
  - Diagnostic commands
  - Clear fix instructions

## Dependencies

```
US-001 (Validate Codex)
  ↓
US-002 (Fix Gemini) ----→ US-003 (Container Auth)
  ↓                            ↓
  └───────────────────────→ US-004 (Smoke Tests)
                               ↓
                          US-005 (Full Loop Tests)
                               ↓
                          US-006 (Graceful Degradation)
                               ↓
                          US-007 (Error Messages)
```

**Critical path:** US-001 → US-002 → US-003 → US-004 → US-005 (15-25 hours)

## Implementation Strategy

### Phase 1: Runner Validation (1 week, 6-10h)
Focus: Prove runners work before building test infrastructure
- US-001: Validate Codex runner works as-is
- US-002: Fix Gemini runner bugs

**Why first:** Research shows Codex likely works; validate before spending time on tests

### Phase 2: Test Infrastructure (1 week, 5-7h)
Focus: Build foundation for E2E testing
- US-003: Create authenticated containers
- US-004: Write smoke tests

**Why next:** Need test infrastructure to validate fixes work correctly

### Phase 3: E2E Validation (1 week, 6-8h)
Focus: Validate complete workflows work
- US-005: Write full loop E2E tests

**Why next:** Comprehensive validation before improving error handling

### Phase 4: Error Handling (1 week, 4-6h)
Focus: Polish user experience
- US-006: Graceful degradation
- US-007: Error messages & troubleshooting

**Why last:** Core functionality must work first; UX improvements are polish

## Success Metrics

**Must Have (US-001 to US-005):**
- ✅ Codex runner validated and working
- ✅ Gemini runner bugs fixed
- ✅ E2E tests pass for all 3 runners (Claude, Codex, Gemini)
- ✅ Full loop test completes in <15 minutes per runner

**Should Have (US-006 to US-007):**
- ✅ Clear error messages for all common failure scenarios
- ✅ Troubleshooting guide with >80% issue resolution rate
- ✅ Graceful fallback prevents hard failures

## Out of Scope

Per task description, these are explicitly OUT OF SCOPE:
- Planning phase support (focus: execution only)
- Documentation (minimal inline docs only, no full setup guides)
- Platform equivalence validation (functional parity via tests is sufficient)
- CI integration (local validation only for now)
- Performance optimization (functionality first)
- Additional platforms (only Claude, Codex, Gemini)

## Research References

All stories are grounded in comprehensive research:
- [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md) - Codex implementation analysis
- [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md) - Gemini bugs and fixes
- [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md) - Test architecture
- [07-docker-auth-real-runners.md](../research/07-docker-auth-real-runners.md) - Container authentication

## Next Steps

1. Review and approve user stories
2. Run `/saha:verify` to validate artifacts
3. Run `/saha:plan` to create phased implementation plan
4. Begin implementation with Phase 1 (US-001, US-002)
