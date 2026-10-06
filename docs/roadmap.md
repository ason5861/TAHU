# Roadmap and release gates

## Completed in v0.2

Persistent policy gateway; task-scoped role credentials; expiring one-use approvals; restart-safe stop; local outbox idempotency; transactional rollback; redacted audit chain; regression tests; separate-process HTTP demo; preserved v0.1 reference.

## Next: v0.3 — real agent integration

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

Maintain a threat register, incident response process and independent assessment. Compare with established information-flow control and systems such as CaMeL. State novelty only after that comparison. Model alignment, societal governance and international coordination are separate workstreams; this software alone cannot implement them.
