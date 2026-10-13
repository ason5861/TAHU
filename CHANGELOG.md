# Changelog

## Unreleased — live agent evaluation, 2026-10-13

- Add an opt-in constrained Codex agent adapter with structured proposals, fresh contexts, bounded CLI execution and native-tool event rejection.
- Execute proposals through a separate HTTP gateway; preserve task exposure across bounded denial feedback and retries.
- Add eight fixed synthetic scenarios, paired proposal replay, explicit block/miss/false-block denominators, fixture task utility, token usage and latency.
- Record initial and revised real-model runs without treating model refusals or provider errors as gateway blocks.
- Add 18 offline adapter/evaluation tests. Keep live calls out of default CI and retain the existing independent Docker isolation job.
- Disclose conservative overblocking, synthetic review, the limited marker oracle, unavailable monetary charges and the difference between remote-model evaluation and offline Docker isolation.

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
