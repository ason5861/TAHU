# Changelog

## Unreleased — English-only documentation, 2026-10-25

- Use English throughout the project presentation and documentation, including the archived v0.1 guide.
- Replace the localized overview with `docs/overview.md` and update its entry point.
- Retain non-ASCII SMTP round-trip coverage with a Unicode symbol fixture. Prototype code, historical reports and authorization policy are unchanged.

## Unreleased — public context preparation, 2026-10-19

- Add host-configured public record ID/hash pins and a fresh trusted request to minimize inputs before drafting; changed, ambiguous or nonpublic records fail closed.
- Add an opt-in public-context mail workflow applied equally to three independent model arms. Keep the frozen original corpus, full-input control and four-task utility denominator.
- Record the changed input/instruction scope explicitly; previously held-out failures now inform development, so the new workflow is not presented as unseen validation.
- Add five context/transport tests, a scoped offline demo option and Chinese documentation updates. Core authorization, exact approval and stop rules are unchanged.
- Publish full-input and scoped runs with 44 real calls and zero runtime errors: TAHU completion changes from 2/4 to 3/4 under the explicit input change; one safe webpage refusal remains, and no added live attack interception benefit is established.

## Unreleased — independent mail comparison, 2026-10-16

- Add frozen development/held-out synthetic mail tasks, independent real-model whitelist, simulated-review and TAHU runs, plus a loopback HTTP page and SMTP receiver.
- Verify received message bytes and reconcile deliveries even after a lost SMTP acknowledgement; record actual effects, model refusals, runtime errors, utility, review burden, tokens and latency separately.
- Publish both live runs, including the initial reviewer label-contract ambiguity. Final free-text TAHU completion is 2/4, below the predeclared 75% target; no unsafe model proposals occurred, so no added live interception benefit is established.
- Add six offline transport/accounting regression tests and a one-command no-model mail demonstration. Preserve all gate and exact-template approval rules.
- Add a lightweight SVG mark, adoption instructions, owner-only license choices and unpublished community-feedback drafts.

## Unreleased — live agent evaluation, 2026-10-13

- Add an explicit exact-template review workflow to recover harmless course summaries from conservative denials using independently trusted public records.
- Bind review rules to task, destination, exact complete text and allowed sources; keep labels and exposure unchanged.
- Add optional operator-only expected-content-hash checking inside the approval transaction, preventing review of one text from granting another stored artifact.
- Record initial denials separately from final unresolved refusals and keep the first reviewed run with its runtime error.
- Add 8 review-control tests and sanitized error diagnostics; native model/tool errors remain separate from successful blocks.

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
