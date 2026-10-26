# Threat model and limitations

## v0.3 optional isolation

An offline Docker runner and an `untrusted` integrity label now address specific worker boundary failures. See [isolation.md](isolation.md) for trusted host/image assumptions, task-local inputs, enforced review and real-container tests. These controls apply only when the runner is used; a bare gateway does not isolate arbitrary agents. Correct initial labeling remains essential.

## Protected scope

An attacker controls JSON proposals submitted using a legitimate task token. It may omit provenance, claim public sources, change fields, reuse IDs, race approvals, request unknown operations or continue after stop. The trusted gateway, host, operator, schema, initial labels and database remain intact. All relevant information starts inside the task's approved inputs, and all supported effects pass through this gateway.

Within that scope the tests exercise default-deny action validation, source/exposure constraints, role separation, bounded task lifetime, transactional approvals and durable stop. Test success does not prove there are no implementation bugs.

## Explicit exclusions

- Untrusted Python code sharing the gateway process or privileged access to its database.
- OS sandbox escapes, host compromise, stolen bearer credentials or a malicious operator.
- Internet-facing denial of service, disk exhaustion and credential theft over plaintext transport.
- Secrets already in model weights, earlier context, other tools or a shared multi-agent memory.
- Semantic deception, manipulation, harmful decisions within permitted actions or incomplete labeling.
- Timing, refusal, task creation and other covert channels. Restricting public selection after sensitive reads only addresses one simple channel.
- Stopping arbitrary external processes, canceling other providers' tasks or recalling information already released.
- Global AI governance, alignment guarantees, control of other companies' models or certification of catastrophic-risk safety.

## Known tradeoffs

The constrained Codex adapter now uses temporary auth-only and user profiles
to exclude ordinary inherited global instructions, installed skills and parent
session/provider environment overrides. Synthetic native-request capture
reproduced the former inheritance and verifies exclusion of the tested markers.
This is not exhaustive runtime attestation: built-in instructions, managed
machine policies, OS credential exposure and other installations remain outside
that evidence. The CLI remains a trusted host process with network access and
its existing authentication; its read-only tool sandbox does not isolate the
CLI itself. See [startup-context.md](startup-context.md).

Exposure is monotonic. An unrelated public derivation is overblocked after a sensitive read. Independent task state reduces this only when a trusted host also separates contexts. A malicious agent must not choose a fresh task token for an already contaminated context. Legitimate approvals intentionally release exact sensitive content and therefore rely on a trustworthy operator.

The audit chain is unkeyed and has no remote anchor. It detects accidental or partial edits, but not a database owner rewriting all history. `purpose` is descriptive metadata, not an enforceable semantic goal. Attempt limits are counts, not time-based rate limiting. The local outbox is not a transactional guarantee for a future external email/payment connector.

## Execution paths and current evidence (2026-10-26)

The [guarded local executor](execution-boundary.md) closes the experiment's
export-then-send stop gap within the trusted host. It does not remove the host
from the trusted computing base. New task IDs do not erase model context.

| Path / threat | Enforced control and evidence | Residual risk / priority |
|---|---|---|
| Proposed sends, direct/indirect injection | Source/exposure checks; eight forced HTTP requests reach the gate and are denied; `tests.test_gateway`, fixed boundary probe | Semantic manipulation within approved data, malicious tool results/third-party agents and broader live attacks still need validation; P0/P1 |
| Local SMTP execution and bypass | Operator-only execution; full payload/policy/version binding; guarded receiver rejects raw SMTP; `tests.test_execution` | Compromised Python host/capability holder can bypass private APIs; OS separation and egress control remain P0 deployment work |
| Stop, replay, concurrent execution, crash | Serialized execution/stop; durable start; no retry of UNKNOWN; execution tests | In-flight accepted effect cannot be recalled; manual reconciliation and general external compensation remain P1 |
| Arbitrary file, HTTP, browser or enterprise tool side effects | Not supported as gateway execution connectors; unknown proposed operations denied | Giving an agent independent host tools bypasses this gateway; do not advertise coverage; P0 |
| Native model CLI and cross-task information | Temporary startup profiles and request captures; separate context tests | CLI networking, prior memory/cache/weights and machine policy remain host responsibilities; P0/P1 |
| Offline Docker computation | Separate optional runner, Linux CI integration and documented resource controls | Does not establish kernel-escape resistance or protect a compromised host; P0/P1 |
| Credentials, administrator compromise and privilege escalation | Distinct task/operator roles; expiring tasks; no credentials in audit text | Bearer theft, malicious operator, rotation/role separation and Internet deployment remain outside current guarantees; P0/P1 |
| Database and audit mutation | Transaction rollback; binding checks; unkeyed hash-chain regression tests | Database owner can rewrite bindings and history; no external signed anchor; P1 |
| Resource exhaustion and supply chain | Bounded requests, SMTP body size/timeouts and optional worker limits; pinned CI actions | No Internet DoS or comprehensive dependency/image vulnerability audit; P1 |

These are implementation-owned tests and measurements, not an independent
review. Unmeasured threats remain unmeasured even when related tests pass.

## Remaining production release blockers

No production security claim until OS isolation/egress controls, external executor failure handling, authenticated approval UX, live-model adversarial evaluation and independent review are implemented and tested. Keep experiments on synthetic data meanwhile.
