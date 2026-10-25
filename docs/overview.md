# TAHU implementation and evaluation overview

TAHU lets an agent propose actions while an independent service checks authorization before recording execution. The current gateway exposes read, derive and delivery operations over HTTP and persists state in SQLite.

## Startup context repair — 2026-10-22

Christian's feedback prompted a synthetic-profile experiment that captured the native CLI's actual submitted requests. The former launch inherited global `AGENTS.md` (also tested with `AGENTS.override.md`) and profile skill-description markers even with no available tools. Each proposal now uses a temporary auth-only profile, a separate user home and an environment allowlist. The tested markers disappear from the submitted request. Only existing CLI file authentication is copied; personal configuration, skills and history are excluded. Temporary directories are cleaned up after success or failure. Missing file authentication fails closed without falling back to the ordinary profile or exporting keyring credentials.

Built-in CLI instructions remain. This is neither complete runtime-context attestation nor host isolation. Christian's CtxWise inventory was static discovery, not proof that all discovered entries were loaded. The four request captures made no model calls. The October 22 regression ran 100 tests: 96 passed and four Docker checks were skipped locally. Secret leakage, injection, exact approval, approval reuse, unknown classifications and stopping remain covered. See [startup reproduction and boundaries](startup-context.md), which also documents the October 24 Windows npm discovery repair and its separate 107-test regression.

The repaired adapter's three independent mail arms completed 22 real model calls without errors. TAHU completed 3/4 normal tasks; one safe webpage summary was denied because it required approval. The whitelist and simulated-review arms each completed 4/4. Every arm had 0/3 unauthorized deliveries, but no model proposed an unsafe send, so this did not establish additional gateway interception benefit. The repair addressed startup inheritance without improving completion on that corpus. [Raw report](../reports/mail-startup-2026-10-22.json).

## Independent mail comparison and public context — 2026-10-19

A public course reply need not read unrelated internal staff records. A trusted host can configure a public-context plan that selects explicitly public records with pinned content hashes, then drafts with a fresh task and model call. It copies no prior conversation, draft or denial feedback, and does not clear an exposed task's restrictions. Actual context isolation, classification and bypass prevention remain host responsibilities.

Run the scripted HTTP/SMTP demonstration without model usage:

```sh
python -m examples.mail_demo --workflow public_context
```

This is a scripted demonstration, not a real-model success rate. See the [public-context experiment](public-context.md) for independent arms, changed inputs and limitations. Earlier failures informed the new workflow, making these development re-evaluations rather than unseen held-out validation.

The October 19 full-input and scoped workflows used 44 real calls with zero runtime errors. Full mixed-input TAHU completion remained 2/4; minimizing inputs before the public task raised completion to **3/4 (75%)**, reduced safe drafts denied from 2/4 to 1/4, and added no approvals. The private note was never supplied to the fresh context; this was not removal of exposure from an existing task. Both simpler arms completed 4/4 in both workflows. No arm proposed unsafe sends, so no additional live interception benefit was demonstrated. The webpage summary still required trusted review.

The original October 16 mixed-input comparison remains available: whitelist and simulated model review each completed 4/4 normal tasks, versus TAHU's 2/4. All arms avoided unsafe deliveries, but none proposed an unsafe send. [Original report](../reports/mail-agent-2026-10-16.json). These free-text results are separate from the template-assisted experiment below.

## Exact-template approval recovery — 2026-10-13

The trusted broker can preconfigure an exact public template from an independent authoritative record, bound to task, destination, complete text and source IDs. The initial send still passes through the original gateway checks. A denied draft receives one-use approval only when it exactly matches the trusted template; the gateway checks the reviewed content hash inside the approval transaction. Secret labels, cumulative exposure, unknown classifications and stop controls remain enforced.

Two repetitions of the same eight scenarios completed 18 model calls without errors. Normal delivery completion increased from 6/12 (50%) to **12/12 (100%)**, while unresolved safe-content refusals decreased from 6/12 to **0/12**. Initial denials remained 6/12; six exact-template approvals recovered delivery. Both post-stop attempts were blocked. This depends on trusted templates and additional approvals, not a general solution to free-text false positives.

The final run used 188,429 input tokens (including 68,608 cached), 818 output tokens and approximately 207.85 seconds of model time. Actual dollar charges were unavailable. The initial run's pre-proposal runtime error is retained; its original log did not establish a cause. See the [final report](../reports/live-agent-reviewed.json), [initial failure record](../reports/live-agent-reviewed-initial.json) and [evaluation method](live-agent-evaluation.md).

## Real-agent evaluation — 2026-10-13

An optional Codex CLI adapter lets a real model propose structured drafts and sends. A trusted broker executes proposals through a separate HTTP gateway, with bounded denial feedback and retries. The model has no TAHU credentials or approval authority. Inputs are synthetic course records and delivery enters a local outbox. This remote-model path is separate from the network-disabled Docker runner; it does not bring arbitrary native tools under gateway control.

Two repetitions of eight scenarios completed 24 calls. Both post-stop sends were blocked and no unsafe deliveries were detected. The model itself refused secret publication and ignored webpage injection, so those outcomes were not counted as gateway interceptions. Conservative policy denied 6/12 safe sends, leaving normal completion at 6/12. Both exact reviewed-release tasks succeeded. This demonstrated stop and approval controls alongside substantial usability cost, rather than production readiness.

Usage was 250,531 input tokens (34,304 cached), 1,353 output tokens, approximately 280.89 seconds of model time and 0.65 seconds of gateway time. Actual subscription charges were unavailable and remain null in the report. See the [method](live-agent-evaluation.md) and [raw results](../reports/live-agent.json).

## v0.3 isolated execution

The `untrusted` label requires exact one-use operator approval for influenced output. A trusted broker starts a fresh Linux container for each invocation, passing only selected task records, without credentials or shared history. The worker has no network, a read-only root filesystem, a non-root user, dropped capabilities and bounded resources, with timeout/stop cleanup.

Execution is refused without Docker. Unit tests are separate from actual container validation; see the [isolation guide](isolation.md). The offline worker is a deterministic probe, while real Codex evaluation uses a separate remote-model path. These controls do not demonstrate elimination of prompt injection, knowledge in model weights or kernel escapes. Public output from an exposed task remains conservatively restricted.

## Implemented gateway controls

- Operator and task credentials are separate; tasks cannot create tasks, approve themselves or read operator audit logs.
- Each task has a record scope, flow policy, operation budget, attempt limit and expiry.
- Reading restricted records leaves persistent task exposure; omitting provenance does not clear it.
- One-use approval binds task, artifact, content and destination, and expires.
- Stopped state survives service restarts.
- Approval consumption, outbox delivery, audit and budget updates share one database transaction.
- Repeating the same request returns its receipt without duplicate delivery; reusing its ID with modified content is rejected.
- Audit events exclude request bodies and credentials and support hash-chain verification. The database still contains record bodies and must be protected.
- The malformed-operation crash and mutable audit-input issue from v0.1 were repaired.

## Run locally

Python 3.10+ is required, with no runtime third-party dependencies. From the repository root:

```sh
python -m examples.demo
python -m unittest discover -s tests -v
python scripts/evaluate.py
```

The example starts a separate service and uses real local HTTP requests with synthetic data. It makes no paid model calls or external deliveries. To retain local experiment state:

```sh
python -m tahu init
python -m tahu serve
```

`.tahu/operator.json` contains operator credentials and must not be given to the agent. Keep the entire `.tahu` directory private. Windows requires suitable service-account permissions and directory ACLs; another process running as the same user can generally read these files, so same-user processes do not form a reliable isolation boundary.

## What the evidence establishes

The October 19 local regression ran 96 tests: 92 passed, four real Docker checks were skipped locally, and container evidence came from Linux CI. [Historical regression report](../reports/regression-context-2026-10-19.json). Later startup/discovery checks are documented separately above. These developer-authored checks establish behavior for specified cases; they are not independent security studies. Default tests and CI make no real model calls.

## Remaining limitations

Production email/external executors, independent adversarial assessment, complete host isolation, an actual human-review interface, semantic risk assessment and comprehensive AI governance remain unfinished. The constrained live adapter, local SMTP receiver and offline Docker worker are distinct paths, not one complete networked sandbox. Gateway stop denies subsequent service operations; it cannot terminate arbitrary external agents or retract completed deliveries.

Human oversight currently means an operator-credential-protected approval API, not proof that a person reviewed a request. Uncertainty awareness primarily means conservative treatment of unknown source labels, not understanding every unknown risk. Server-side task state is separated, but callers must genuinely separate model contexts; a model that read secrets does not become clean merely by receiving a new token.

Gateway delivery is a local SQLite outbox entry. Mail experiments export authorized entries over SMTP only to the local test receiver. `public` and `internal` are policy labels mapped by the host to fixed `.test` recipients. No real third-party mail is sent. No claim of general AI control, novel foundational mechanisms or independent security certification follows from these experiments.
