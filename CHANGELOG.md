# Changelog

All notable changes to Vibe-Upgrader are documented here.

## [1.0.0] - 2026-07-19

### Added

- Standard and Experimental upgrade tracks with explicit routing.
- `decision_task` schema 3.0 for permission, provenance, prototype, and verification decisions.
- Read-only MotionSites mechanism search and React Bits component evaluation.
- Adopt, reject, and equivalent custom-fallback decisions.
- Isolated experimental prototypes with a required human `approved | revise_once | rejected` gate.
- Deterministic installation, runtime-write regression coverage, and source/installed manifest verification.

### Verified

- Stage 9 Standard and Experimental acceptance flows.
- 17 unit tests, helper compilation, and validation of the canonical and installed Skill.
- An 18-file installed runtime manifest with no behavior or protocol changes during release closeout.

### Distribution note

- The complete local MotionSites corpus is excluded from the public repository because public bulk-redistribution permission could not be confirmed.
