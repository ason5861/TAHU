# Changelog

## 0.3.0

- Add untrusted-input integrity labels and exact one-use review.
- Add an optional offline Docker broker with task-local input, fresh execution state, constrained OS access, bounded pipes, cancellation and cleanup.
- Add regression tests, real-container checks, an isolated demo and Linux CI.
- Preserve same-task overblocking and disclose missing live-model evaluation and kernel-escape defenses.

## 0.2.0 — 2026-10-06

- Added authenticated loopback HTTP gateway and provider-neutral Python client.
- Added per-task SQLite persistence, action/attempt limits and task expiry.
- Added destination/content-bound expiring one-use approvals.
- Added durable stop, transactional outbox and request-id replay protection.
- Added redacted audit chain, schema validation and fail-closed rollback.
- Fixed v0.1 malformed-op crash and mutable input/audit aliasing.
- Added 39 regression/integration tests and separate-process demo.
- Preserved original v0.1 files and disclosed current limitations.

## 0.1 — 2026-09-24

Original in-memory information-flow demonstrator supplied by the project owner, with 17 synthetic scenarios and six control-property checks. Preserved under `legacy/v0_1`.
