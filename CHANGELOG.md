# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.4] - 2026-02-20

### Added
- Multi-target artifact sync (`saha sync`) supporting Claude Code, Codex CLI, and Gemini CLI — copies agents, skills, and commands into `.claude/`, `.codex/`, and `.gemini/` directories
- `codex` and `gemini` launcher commands alongside existing `claude` command
- Enhanced test critique schema with per-dimension quality scores (mocking, assertions, structure, coverage, independence)
- Coverage tracking in test critique output: `files_with_coverage` and `files_missing_coverage` fields
- 19 additional test quality patterns for richer issue detection (vague assertions, flaky timing, shared state, missing edge cases, etc.)

### Changed
- Manager agent now runs on every iteration stop rather than only at task end
- `TestCritiqueOutput.critique_passed` now requires grade A or B (previously A/B/C passed)

### Fixed
- Codex runner CI compatibility with mocked subprocess processes
- MyPy type narrowing in `CodexRunner` stream path
- Ruff formatting compliance in CI

## [0.7.1] - 2026-02-16

### Fixed
- Codex runner now properly streams JSON output with `--json` flag
- Added structured event display for Codex CLI output (commands, reasoning, messages)
- Real-time progress visibility when using `saha run` with Codex runner

## [0.7.0] - 2026-02-14

### Added
- Responsive interrupt handling (Ctrl+C) with graceful shutdown
- Runner visibility improvements
- Enhanced progress tracking

## [0.6.2] - 2026-02-11

### Added
- GitHub Actions CI workflow for automated testing
- GitHub Actions publish workflow for PyPI releases
- MIT License file
- This CHANGELOG

### Changed
- Updated installation instructions in README
- Added CI badges to README

### Fixed
- Repository URL in pyproject.toml

## [0.6.1] - 2026-02-09

### Added
- Execution loop enhancements and skills
- Plan progress tracking

## [0.6.0] - 2026-02-07

Initial public release

### Added
- Hierarchical task planning with Claude Code plugin
- Autonomous agentic execution loop
- Support for Claude Code and Codex runners
- Integration with ruff, ty, complexipy, and pytest
- Comprehensive documentation

[Unreleased]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.7.4...HEAD
[0.7.4]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.7.1...v0.7.4
[0.7.1]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/roman-romanov-o/sahaidachny/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/roman-romanov-o/sahaidachny/releases/tag/v0.6.0
