# Research Report: Multi-Platform Runner Support

**Task:** TASK-01 - Support for Codex and Gemini CLI Runners
**Date:** 2026-02-12
**Researcher:** Sahaidachny Research Agent
**Status:** Complete

## Executive Summary

Research into Codex and Gemini runner implementations reveals **the problem is validation, not architecture**. The claim that runners are "broken" is partially correct but misleading:

- **Codex Runner**: Well-implemented, follows correct patterns, matches official API documentation. Status: **Likely works but untested**.
- **Gemini Runner**: Has actual bugs (wrong CLI flags), missing features (file tracking, skill loading). Status: **Genuinely broken**.
- **Architecture**: Excellent design, no refactoring needed. Status: **Production-ready**.

**Bottom line:** This is 90% validation work, 10% coding. The Codex runner probably works as-is. The Gemini runner needs 4-6 hours of fixes.

## Research Documents

### 01. Codex Runner Analysis
**File:** `01-codex-runner-analysis.md`

**Key Findings:**
- Implementation architecture is sound
- Command structure matches official Codex CLI documentation
- File change tracking uses proven snapshot approach
- Skill loading is correctly implemented and tested
- **No bugs found** - only untested against real CLI

**Critical Issues:**
- Stdin input method (`codex exec -`) not explicitly documented
- Session log parsing may be brittle
- No real-world validation performed

**Recommendation:** Install Codex CLI and run integration test. Expect minimal or no changes needed.

**Confidence Level:** High (80%) that runner works as-is

---

### 02. Gemini Runner Analysis
**File:** `02-gemini-runner-analysis.md`

**Key Findings:**
- Missing file change tracking (CRITICAL)
- Wrong CLI flags: `--yolo` does not exist
- No skill loading implementation
- Oversimplified JSON parsing
- No token usage extraction

**Critical Issues:**
- Runner will fail immediately with unknown flag error
- Cannot track which files were modified (blocks orchestrator)
- Agents requiring skills won't work correctly

**Recommendation:** Substantial refactoring required before runner can work.

**Confidence Level:** Zero (0%) that runner works as-is - confirmed broken

---

### 03. Claude Runner Reference
**File:** `03-claude-runner-reference.md`

**Key Findings:**
- Claude runner is fully functional and well-tested
- Demonstrates correct patterns for all runner concerns
- Native agent support simplifies implementation
- File tracking via tool metadata is Claude-specific advantage
- Serves as template for other runners

**Patterns to Replicate:**
- Error handling (timeout, interrupt, not found)
- JSON parsing with fallbacks (code blocks + brace counting)
- Token usage extraction from events
- Subprocess lifecycle management

**Comparison:**
- Codex: Correctly adapts patterns (agent embedding, snapshot tracking) ✓
- Gemini: Does not follow patterns (bugs, missing features) ✗

---

### 04. CLI API Validation
**File:** `04-cli-api-validation.md`

**Key Findings:**
- Codex CLI has good documentation, all flags confirmed
- Gemini CLI has poor documentation, many flags unconfirmed
- Stdin input method for Codex is undocumented but likely works
- `--yolo` flag definitely doesn't exist in Gemini CLI

**Documentation Quality:**
- Claude Code: Grade A (comprehensive)
- Codex: Grade B (good, some gaps)
- Gemini: Grade D (minimal, mostly interactive mode)

**Validation Needed:**
- Codex: Test stdin input, verify output file format
- Gemini: Test all flags, document actual API, verify tool support

**Recommendation:** Create validation scripts for both CLIs before claiming they work.

---

### 05. Architecture Analysis
**File:** `05-architecture-analysis.md`

**Key Findings:**
- Runner abstraction is well-designed (4-method interface)
- Registry pattern enables multi-backend support
- Per-agent configuration works correctly
- Fail-fast validation at startup
- Clean integration with orchestrator

**Design Patterns:**
- Abstract Factory (runner creation)
- Registry (runner management)
- Strategy (interchangeable runners)
- Dependency Injection (orchestrator assembly)

**Extensibility:**
- Adding new runners is straightforward
- No architectural changes needed for requirements
- All design patterns used correctly

**Recommendation:** Do not refactor architecture. Focus on implementation fixes and validation.

---

### 06. E2E Testing Strategy
**File:** `06-e2e-testing-strategy.md`

**Key Findings:**
- Existing test infrastructure is excellent (IntelligentMockRunner, testcontainers, sample projects)
- **Critical gap:** Zero tests use real runners - all use mocks
- User's "eval" approach is fundamentally sound but needs significant refinement
- Verification must be multi-level (file → test → quality → structured output)
- Functional equivalence, not code equivalence (different LLMs write different code)

**Critical Refinements to User Proposal:**
- ❌ "From scratch" → ✅ Minimal pre-existing project
- ❌ "Automated eval" (vague) → ✅ Three-tier verification (file, test, quality)
- ❌ Happy path only → ✅ Include failure scenarios (QA retry, quality retry)
- ❌ Undefined comparison → ✅ Functional equivalence strategy
- ✅ Local-first approach (correct) → ✅ Phased: smoke → loop → equivalence → CI

**Test Architecture:**
```
tests/
├── fixtures/                        # NEW: Reusable test projects
│   └── projects/
│       └── simple-python/           # Minimal Python project template
├── integration/
│   └── runners/                     # NEW: Real runner tests
│       ├── test_claude_runner_real.py
│       ├── test_codex_runner_real.py
│       ├── test_gemini_runner_real.py
│       └── test_runner_equivalence.py
```

**Test Hierarchy (by priority):**
1. **Smoke tests** (~2 min each): Single agent invocation, basic functionality
2. **Loop tests** (~5-10 min each): Full agentic loop, happy path
3. **Retry tests** (~10-15 min each): QA/quality failures and recovery
4. **Equivalence tests** (~30-45 min): All runners, compare outcomes

**Verification Strategy (multi-level):**
- **Level 1:** Process success (exit code 0, no errors)
- **Level 2:** Artifacts (files exist, functions present, type hints, docstrings)
- **Level 3:** Functional (tests pass, ruff passes, mypy passes)
- **Level 4:** Structured output (files_changed, dod_achieved, quality_passed, task_complete)

**Key Infrastructure Needs:**
- Pytest markers: `@pytest.mark.slow`, `@skipif_no_codex`, `@pytest.mark.real_runner`
- Fixtures: Real runner instances, sample projects, agent specs, verification helpers
- Temp project isolation per test
- Timeout protection (5-10 min max per test)

**Sample Test Project Characteristics:**
- Minimal but realistic (basic Python package)
- Clear target file (e.g., `sample_project/utils.py`)
- Verifiable changes (pytest can check)
- Pre-existing structure (not from scratch)
- 2-3 functions to implement (~5-10 min task)

**Good Feature Example:**
```
Task: Add string utilities
- reverse_string(s: str) -> str
- capitalize_words(s: str) -> str
- Type hints + docstrings required
- Tests must pass
Target: sample_project/utils.py
```

**CI Considerations (Phase 4, future):**
- Nightly runs, not per-commit (too slow, too expensive)
- GitHub secrets for API keys
- Conditional skip if credentials unavailable
- Cost limits and monitoring
- Retry logic for flaky tests
- Use smaller models where possible

**Roadmap:**
1. **Week 1:** Local validation, smoke tests, setup docs
2. **Week 2:** Full loop tests, failure scenarios, fixtures
3. **Week 3:** Equivalence testing, comparison framework
4. **Week 4:** CI integration, credential management, cost control

**Effort Estimate:** 40-60 hours total (10-15 hours per week)

**Success Metrics:**
- Week 1: All CLIs installed, smoke tests pass, docs complete
- Week 2: Full loop works, retry scenarios work, fixtures created
- Week 3: Equivalence verified, differences documented
- Week 4: CI runs successfully, cost under control

**Risk Assessment:**
- **High:** CLIs may not work as expected → Validate manually first
- **High:** Tests too slow for regular use → Mark slow, nightly CI only
- **Medium:** Outputs too different → Functional equivalence, not code equivalence
- **Medium:** API costs → Usage limits, smaller models
- **Medium:** Flaky tests → Retries, generous timeouts

**Recommendation:** Phased approach starting with Claude runner (known to work), then replicate for Codex/Gemini. Focus on functional equivalence, not code identity.

**Confidence Level:** High (90%) that approach will succeed with proper phasing

---

## Critical Assessments

### Is Codex Runner Broken?

**Answer:** Probably not.

**Evidence:**
- All unit tests pass
- Command structure matches official docs
- Architecture follows Claude runner patterns
- File tracking implementation is tested and works

**What's missing:** Real-world validation against actual CLI

**Recommendation:** Install Codex CLI, run integration test, expect it to work.

### Is Gemini Runner Broken?

**Answer:** Yes, definitely.

**Evidence:**
- Uses non-existent `--yolo` flag (will fail immediately)
- Missing file change tracking (blocks orchestrator)
- Missing skill loading (agents won't work)
- Oversimplified JSON parsing (will fail on complex outputs)

**What's missing:** Core functionality, not just validation

**Recommendation:** Fix bugs first, then validate.

### Does Architecture Support Requirements?

**Answer:** Yes, perfectly.

**Evidence:**
- Multi-backend support: ✓ Registry + per-agent config
- Feature parity: ✓ Common interface enforces consistency
- Extensibility: ✓ Easy to add new runners
- Testing: ✓ Mock runner + conditional tests
- Configuration: ✓ Hierarchical env vars

**What's missing:** Nothing architectural

**Recommendation:** Build on existing foundation, don't rebuild.

## Validation Gaps

### What We Know

1. **Claude runner works** - Tested in production
2. **Codex implementation matches docs** - All flags confirmed
3. **Gemini has bugs** - Wrong flags, missing features
4. **Architecture is sound** - No refactoring needed

### What We Don't Know

1. **Does Codex actually work?** - Untested with real CLI
2. **What does Gemini CLI actually support?** - Poor documentation
3. **What output format do they produce?** - Unknown
4. **Do they support required tools?** - Unconfirmed

### How to Fill Gaps

**Phase 1: Manual Validation (1-2 hours)**
```bash
# Install CLIs
npm install -g @openai/codex
npm install -g @google/gemini-cli

# Run validation scripts
./scripts/validate-codex-cli.sh
./scripts/validate-gemini-cli.sh

# Document findings
# Update implementations based on reality
```

**Phase 2: Fix Gemini (4-6 hours)**
- Remove `--yolo` flag
- Add file change tracking (copy from Codex)
- Add skill loading (copy from Codex)
- Fix JSON parsing (copy from Codex)
- Test incrementally

**Phase 3: Automated Tests (2-3 hours)**
- Write integration tests requiring real CLIs
- Mark with `@pytest.mark.codex` and `@pytest.mark.gemini`
- Add to CI with conditional execution
- Document test setup

**Phase 4: E2E Validation (2-3 hours)**
- Run full orchestrator loop with each runner
- Compare outputs with Claude runner
- Validate artifact equivalence
- Document any platform-specific quirks

## Recommendations

### Immediate Actions

1. **Create validation scripts**
   - `scripts/validate-codex-cli.sh` - Test Codex CLI behavior
   - `scripts/validate-gemini-cli.sh` - Test Gemini CLI behavior
   - Quick smoke tests for manual validation

2. **Fix Gemini runner**
   - Priority: Critical bugs (file tracking, wrong flags)
   - Copy proven patterns from Codex runner
   - Test incrementally with validation script

3. **Test Codex runner**
   - Run with actual CLI installation
   - Expect minimal or no changes needed
   - Document any discovered issues

4. **Add integration tests**
   - Mark as requiring real CLIs
   - Skip if CLI not installed
   - Cover all runner methods

### Task Approach

**Do NOT start with:**
- ❌ Architectural refactoring (not needed)
- ❌ Adding new features (scope creep)
- ❌ Optimizing performance (premature)
- ❌ Creating plugin system (overkill)

**DO start with:**
- ✅ Installing CLIs and validating actual behavior
- ✅ Fixing confirmed bugs in Gemini runner
- ✅ Running integration tests with real CLIs
- ✅ Documenting what actually works

### Success Criteria

**Codex Runner:**
- [ ] CLI installed and authenticated
- [ ] Validation script passes
- [ ] Integration test passes
- [ ] Can run execution-implementer agent
- [ ] File changes are tracked correctly
- [ ] Skills are loaded and embedded
- [ ] Tokens are tracked (or gracefully fail if unavailable)

**Gemini Runner:**
- [ ] CLI installed and authenticated
- [ ] Wrong flags removed
- [ ] File tracking implemented
- [ ] Skill loading implemented
- [ ] JSON parsing improved
- [ ] Validation script passes
- [ ] Integration test passes
- [ ] Can run execution-qa agent

**Both:**
- [ ] End-to-end test produces equivalent artifacts to Claude
- [ ] Documentation updated with setup instructions
- [ ] CI tests run (with conditional execution)
- [ ] No regressions in Claude runner

## Effort Estimate

| Task | Codex | Gemini | Notes |
|------|-------|--------|-------|
| CLI Installation | 0.5h | 0.5h | Download, setup, authenticate |
| Validation Scripts | 1h | 1h | Test flags, output format, tools |
| Bug Fixes | 0h | 4h | Codex likely works, Gemini has bugs |
| Integration Tests | 1h | 1h | Write tests, mark conditional |
| E2E Testing | 1h | 1h | Run full loop, compare outputs |
| Documentation | 1h | 1h | Setup guides, troubleshooting |
| **Total** | **4.5h** | **8.5h** | **~13 hours** for both |

**With Focus:** Could be done in 2-3 focused work sessions

## Risk Assessment

### Low Risk (Likely to succeed)

- Codex runner works as-is or needs minor tweaks
- Architecture supports all requirements
- Claude runner serves as proven template
- Codex CLI has good documentation

### Medium Risk (May encounter issues)

- Codex stdin input method might not work (alternative: temp files)
- Token usage extraction may not work for all CLIs (acceptable: log warning)
- Some agents may need platform-specific adjustments

### High Risk (Likely problems)

- Gemini CLI may not support required tools (blocks entire runner)
- Gemini documentation gaps may hide critical issues
- Gemini output format may be incompatible with parsing

**Mitigation:** Validate Gemini CLI capabilities early. If it lacks file tools, document limitation and focus on Codex only.

## Conclusion

The research reveals a **validation problem, not a design problem**. The architecture is excellent, Codex implementation appears sound, but Gemini has actual bugs.

**Key Insights:**

1. **Codex runner is probably fine** - well-implemented, follows docs, needs testing
2. **Gemini runner is genuinely broken** - wrong flags, missing features, needs fixes
3. **Architecture is production-ready** - no refactoring needed, build on it
4. **Documentation is the blocker** - especially for Gemini CLI

**Recommended Approach:**

1. Install CLIs and validate actual behavior (1-2 hours)
2. Fix Gemini bugs based on validation findings (4-6 hours)
3. Add integration tests for both runners (2-3 hours)
4. Run E2E tests and document results (2-3 hours)
5. Update setup guides and troubleshooting docs (1-2 hours)

**Total effort: ~13 hours** spread across 2-3 focused work sessions.

**Critical path:** Gemini CLI validation → if tools not supported, document limitation and reduce scope.

---

**Research Completed:** 2026-02-12
**Next Steps:** Install CLIs, create smoke tests, document setup process

## Sources

- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
- [Codex GitHub Repository](https://github.com/openai/codex)
- [Gemini CLI GitHub Repository](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI Documentation](https://geminicli.com/docs/)
- [OpenAI Codex Overview](https://openai.com/codex/)
