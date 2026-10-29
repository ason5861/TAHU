# Roadmap and release gates

## Completed in v0.2

Persistent policy gateway; task-scoped role credentials; expiring one-use approvals; restart-safe stop; local outbox idempotency; transactional rollback; redacted audit chain; regression tests; separate-process HTTP demo; preserved v0.1 reference.

## Completed: constrained real agent integration

Exact-template recovery now completes the fixed legitimate delivery suite using
independently trusted public records and content-hash-bound one-use approvals.
Initial denials remain visible; no broad arbitrary-text declassification is
implemented. Deployment-specific template governance, held-out attacks and
independent semantic utility grading remain required.

The opt-in Codex CLI adapter now proposes structured actions and receives bounded denial feedback. A separate HTTP gateway enforces synthetic task policy; the report measures marker-defined blocks/misses, content-safe false blocks, fixture task completion, tokens and wall time. This is an initial live-model experiment, not completion of the held-out evaluation or deployment gates below. See [evaluation method](live-agent-evaluation.md).

## Next: broader real agent validation

1. Integrate one model provider through the client interface. Keep provider keys in a trusted orchestrator and use synthetic data.
2. Enforce fresh model contexts per task. Add tests that deliberately attempt to carry restricted memory into a public task.
3. Compare plain tool permissions, explicit provenance tracking, conservative exposure and isolated-context policies on the same model and tasks.
4. Add a held-out attack set authored separately from policy implementation. Record seeds, model/version, task success, unauthorized effects, false positives, latency and actual cost.
5. Publish all failures. Do not reinterpret simulation results as real deployment evidence.

Gate: reproducible live-model results with a predetermined task-utility threshold and no unauthorized effects in the declared held-out suite. This is a scoped release criterion, not a universal safety proof.

## v0.4 — deployment boundary

Separate service and agent OS identities; deny direct agent egress; protect state ACLs; add resource limits and hardened transport; persist independent audit checkpoints; deliver to one allowlisted external connector with idempotency and crash recovery. Exercise actual process termination and child-job cleanup.

Gate: attempts to bypass the gateway or reach credentials fail under independent review; connector failures have tested recovery semantics. Test stop races and already in-flight work explicitly.

## Broader programme

## Security-validation milestones (2026-10-26)

| Milestone | Current evidence | Remaining acceptance work |
|---|---|---|
| A: security invariants | Scoped action inventory, gateway/guarded-mail bypass tests, immutable policy and payload binding, stop serialization | Independent host/agent OS identities and egress restrictions; no arbitrary file/browser/API executor coverage |
| B: adversarial validation | Versioned eight-case forced-request development corpus in CI; independent neutral-prompt, prompt-only and TAHU runs retain 7/18 model errors and below-target completion | Establish stable bounded operation before repeating the comparison; independently authored held-out attacks, paraphrase grading and resource metrics |
| C: end-to-end execution | One real-model public draft completed guarded local delivery, lost-ack reconciliation and deduplicated replay; deterministic subprocess crash/restart tests remain separate | Broader successful live lifecycle evidence; full process/host isolation and production connector compensation |
| D: adoption/readiness | Apache-2.0, public threat/security docs, Windows/Linux tests and explicit evidence levels | External security review, independently protected audit anchors, release artifacts and suitable dependency/secret scanning |

These milestones are scoped work gates. Deterministic forced proposals are not
live-model comparisons; AI-assisted review is not an independent audit.

Maintain a threat register, incident response process and independent assessment. Compare with established information-flow control and systems such as CaMeL. State novelty only after that comparison. Model alignment, societal governance and international coordination are separate workstreams; this software alone cannot implement them.
