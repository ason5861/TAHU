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

## Review register: 25 concerns, checked against merged evidence

This register responds to the supplied technical/product/investment review.
It is a work queue, not confirmation that every concern is an exploitable bug.
The baseline is merged PRs #1 and #2 (`824f277`); current changes add evidence,
not production isolation or a new safety-effectiveness result. External market,
customer, company and IP assertions have not been independently verified.

| # | Concern | Status / priority | Evidence and next acceptance condition |
|---|---|---|---|
| 1 | Initial source labels | Trusted-input assumption; P0 | New `tests.test_trust_boundary` rejects missing fields and agent label forgery, but deliberately wrong operator labels allow synthetic delivery. Require a reviewed trusted ingestion contract. |
| 2 | Semantic, encoded and composed leaks | Partially tested; P0 | Six transformed/split/benign proposals retain exposure and are refused, including harmless math. This tests monotonic flow, not semantic detection; expand separately authored multi-turn cases and grading. |
| 3 | Context isolation | Reproduced host limit; P0 | New test carries an old task's synthetic secret into an empty new task and delivers it. Token separation is insufficient; validate host context/cache/file isolation before claims. |
| 4 | Uncovered execution paths | Explicit deployment gap; P0 | `execution-boundary.md` scopes guarded SMTP only; arbitrary file/HTTP/browser tools are unsupported. Demonstrate one OS-separated deployment and deny independent egress with actual bypass tests. |
| 5 | Conservative false refusals | Measured open defect; P0 | `live-lifecycle.md` retains safe-draft refusal and failed utility target. Improve a defined workflow with trusted input separation or exact review, preserving mixed-input controls and arbitrary-text restrictions. |
| 6 | Injection effectiveness | Evidence gap; P0 | Forced proposals reach the gate; no unsafe model sends in latest live comparison. Require actual dangerous proposals, effects and matched simple baselines; distinguish model refusals. |
| 7 | Stop scope | Local tests; wider gap; P0/P1 | `tests.test_execution` covers queued work and serialization. Define asynchronous/in-flight cancellation and compensation per connector; do not promise recall. |
| 8 | Approval burden | Unmeasured human cost; P1 | Exact approvals and template recovery exist. Measure real review frequency/time and abandonment; synthetic reviewers do not supply these data. |
| 9 | Audit as proof | Explicit limit; P1 | Unkeyed chain has no independent anchor. Test event completeness and external rollback/truncation detection; no production signing keys or storage have been provisioned. |
| 10 | Deployment complexity | Unvalidated adoption cost; P1 | Python/HTTP/SQLite and optional Docker documented. Time one independent, reproducible setup and identify every host obligation. |
| 11 | Framework integration | Unsupported claims excluded; P1 | Generic HTTP client exists; LangGraph/AutoGen/CrewAI/MCP integrations are not validated. Choose an actual user need before adding an adapter. |
| 12 | Human-review volume | Product hypothesis; P1 | No real approval-time study. Keep hypothetical enterprise arithmetic separate from measured data; record per-task review distributions. |
| 13 | Enterprise product readiness | Not implemented comprehensively; P2 | Multi-tenant controls, console and central management are not established. Specify only after the core boundary and a real pilot justify them. |
| 14 | Operational failures | Partial local evidence; P1 | Transaction rollback, restart and UNKNOWN receipt reconciliation exist. Exercise DB/timeout/unavailable-receipt faults; quantify recovery and never default-open or blindly retry. |
| 15 | Developer experience | No confirmed independent run; P1 | Invitations/static review are not completed trials. Obtain version, environment, commands, failure output and willingness to continue without repeated pings. |
| 16 | Realistic adversarial evaluation | Small author-owned corpus; P0/P1 | Same-model arms exist but errors/utility failed; developer split labels do not establish independence. Pre-register new cases/criteria and bounded resource budgets, retain all failures. |
| 17 | Host OS boundary | Open deployment blocker; P0 | CLI/Python host and database remain trusted. Test account separation, credential/file ACLs, IPv4/IPv6/DNS and actual egress restrictions without weakening host protection. |
| 18 | Audit coverage | Partly tested; P1 | Step/approval/stop/execution events exist. Enumerate unlogged paths and test missing events, truncation, rollback and clock changes; chain validity alone is insufficient. |
| 19 | Performance and cost | Incomplete measurements; P1 | Successful-call tokens/timing exist; dollars and real review cost are unknown. Measure authorization P50/P95/P99, throughput, concurrency, storage growth and recovery separately from model latency. |
| 20 | External security assessment | Not established; P1/P2 | Author tests, CI, scans and AI reviews are not independent audits or certification. Prepare reproducible review materials; external services/access require separate authorization. |
| 21 | Competitor differentiation | Market hypothesis; P2 | Verify current vendor claims from primary sources before comparison. Demonstrate incremental value over simpler controls, not a feature-count claim. |
| 22 | Built-in substitutes | Market hypothesis; P2 | Identify when ordinary IAM/tool permissions/approval already suffice; compare measured integration cost and residual risk in the same scenario. |
| 23 | Paying customers | Unknown; P1/P2 | No revenue or buyer claims inferred from traffic. Validate a real problem, budget owner and pilot outcome through an authorized channel. |
| 24 | License and IP | License resolved; provenance still scoped; P0/P2 | Complete Apache-2.0/NOTICE are on main. Old preview-license language is stale; retain third-party rights, verify contributions and ask owner about company/IP facts if needed. Do not change license or invent ownership. |
| 25 | Team/commercial execution | Unknown; owner decision | Maintenance activity cannot establish company/team/sales capability. Confirm facts with the owner when required; do not imply titles, customers or delivery credentials. |

The review's four-week schedule is a suggested sequence, not a committed audit,
customer acquisition deadline or certification plan. These tests do not provide
independent validation. Run the new scoped boundary evidence with:

```sh
python -m unittest tests.test_trust_boundary -v
```

Six transformed/split/benign public proposals are denied under recorded restricted
exposure, three attempted agent classification overrides are rejected, and
unknown exposure still blocks both destinations. Two **separate counterexamples**
deliberately violate trusted-host assumptions and produce two guarded local
captures of a synthetic secret: wrong initial labels and carried-over context.
They are not gateway interception successes. No model is called and no Internet
mail is sent. The harmless-math refusal remains a visible usability counterexample.

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
