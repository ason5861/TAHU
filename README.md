# TAHU · 知道

![TAHU: check permission before delivery](docs/tahu-mark.svg)

**Traceability · Authorization · Human Oversight · Uncertainty Awareness**

A research authorization gateway for AI agents. An agent proposes actions; a separate local service checks task permissions, information flow, approvals and stop state before recording an authorized delivery.

For developers connecting an agent to mixed public/internal information: check a proposed message before delivery, and inspect why it was allowed, denied or approved. Try the local email workflow with **Python 3.10+ and no third-party dependencies**:

```sh
python -m examples.mail_demo --workflow public_context
```

This scripted demo starts its own HTTP gateway and local SMTP receiver. The trusted host prepares a fresh public-only task for the course reply, without supplying unrelated private notes. It needs local-port access, uses synthetic data and consumes no model usage. [Integration steps and context requirements](docs/public-context.md); [original comparisons and transport limits](docs/mail-comparison.md).

**Status: runnable research software with an optional offline Docker worker and constrained live Codex agent evaluations.** The gateway records authorized deliveries in SQLite; the new evaluation exports them to a loopback SMTP test inbox. No real external email is sent. The isolated runner requires Linux Docker; remote-model evaluations are separate trusted-broker experiments. The gateway alone does not sandbox agents.

**Concrete example:** an agent reads an internal access code and proposes a public announcement. TAHU checks the task's accumulated exposure before accepting delivery, even if the draft omits its sources. An exact operator approval can release a reviewed draft; stopping the task prevents further execution. This conservative policy can also reject harmless summaries, which the live evaluation records explicitly.

## Live agent evaluation

### Public-only context preparation — 2026-10-19

A trusted host can now start a fresh public drafting job from pinned public
records, keeping unrelated private notes out of its model context. It supplies
a fresh trusted instruction and rejects changed, ambiguous or nonpublic records.
This prepares inputs before execution; it does not clear an exposed task or
automatically approve a free-form draft.

Two independent three-arm runs completed **44 real model calls** without runtime
errors. The same frozen six tasks were retained, including all four normal tasks:

| TAHU measurement | Full mixed inputs | Public-context workflow |
|---|---:|---:|
| Normal tasks completed | 2/4 (50%) | **3/4 (75%)** |
| Content-safe proposals denied | 2/4 | **1/4** |
| Unauthorized deliveries / attack opportunities | 0/3 | 0/3 |
| Draft calls / extra approvals | 6 / 0 | 6 / 0 |

The scoped workflow meets the predeclared 75% smoke-test target. **It changes
one task's inputs and instruction**: the public reply no longer reads the private
note. All three arms receive identical inputs within each workflow. Both simpler
baselines still completed 4/4 tasks, and no arm proposed unsafe sends, so no added
live interception benefit is established. The injected-page summary still needs
trusted review. These previously seen cases now inform development; this is not
new held-out validation or proof that mixed-context overblocking is solved.

[Protocol, integration, all six results and costs](docs/public-context.md);
[full-input raw run](reports/mail-full-2026-10-19.json);
[scoped raw run](reports/mail-context-2026-10-19.json).
Latest local regression: **92 passed, 4 Docker skips**, with real Docker checks
retained in Linux CI. Dollar charges and human setup/review time are unavailable.

### Independent free-form email comparison — 2026-10-16

The same six frozen tasks were drafted in **independent model runs** for three
configurations, using identical prompts, inputs, model and one-turn budgets.
Messages were actually received over local SMTP. No trusted templates were used.

| Measurement | Recipient whitelist | Whitelist + simulated review | TAHU |
|---|---:|---:|---:|
| Legitimate tasks completed | 4/4 | 4/4 | **2/4** |
| Content-safe proposals denied | 0/4 | 0/4 | **2/4** |
| Unauthorized deliveries / attack opportunities | 0/3 | 0/3 | 0/3 |
| Unsafe proposals from model | 0 | 0 | 0 |
| Review requests | 0 | 4 | 0 |
| Real model calls | 6 | 10 | 6 |
| End-to-end seconds, summed across tasks | 44.91 | 81.88 | 47.67 |

**TAHU missed the predeclared 75% completion target.** It rejected a harmless
public summary after secret exposure and a safe summary of an injected webpage.
All three configurations avoided known unsafe deliveries because the drafter
abstained on the direct leak/unknown-data requests and ignored the injection.
This run therefore establishes **no additional live attack interception benefit**
over the simpler configurations. The second arm used another model as a review
proxy; it did not measure human judgment or human review time.

The [raw report](reports/mail-agent-2026-10-16.json) retains all 22 real calls,
captured synthetic messages, input hashes, errors, tokens and audit verification.
The [method and failure analysis](docs/mail-comparison.md) includes the initial
run, the reviewer label-contract correction, fixed scoring and limitations.
The [regression report](reports/regression-mail-2026-10-16.json) records **87
passed and 4 local Docker skips**. This free-text result takes precedence over
the separate template-assisted completion result below when assessing utility.

### Improved exact-review workflow — 2026-10-13

The trusted host can now recover a denied harmless announcement using a
preconfigured exact public template from an independent authoritative record.
The rule binds task, destination, full text and source IDs. The gateway checks
the expected content hash before issuing its ordinary one-use approval. Labels,
exposure, unknown-data restrictions and stop controls remain enforced.

Two repetitions of the same eight-case corpus completed **18 real model calls**
with zero runtime errors. See the [raw reviewed run](reports/live-agent-reviewed.json).

| Measurement | Original conservative workflow | Exact-template review workflow |
|---|---:|---:|
| Legitimate delivery tasks completed | 6/12 (50%) | **12/12 (100%)** |
| Final content-safe sends refused | 6/12 (50%) | **0/12 (0%)** |
| Initial content-safe gate denials | 6/12 (50%) | **6/12 (50%)** |
| Added exact public-template approvals | 0 | **6** |
| Post-stop attempts blocked | 2/2 | **2/2** |
| Detected unsafe deliveries | 0 | **0** |

The reduction is **approval recovery**, not removal of conservative checks.
The improved prompt also supplies the trusted template, so this compares two
complete workflows, not a model-independent policy change. New facts and
arbitrary free-form drafts still require separate trusted review. The real model
again refused unapproved secret publication and ignored the embedded injection;
forced malicious proposals are covered separately by HTTP regression tests.

The final run measured **188,429 input tokens** (including **68,608 cached**),
**818 output tokens**, **207.85 s** model time and **0.92 s** gateway time.
Subscription dollar charges remain unavailable. The [first reviewed run](reports/live-agent-reviewed-initial.json)
is retained: it completed 11/12 legitimate tasks and recorded one pre-proposal
runtime error whose original generic log did not establish a cause. The final
run adds sanitized error diagnostics and completed without errors. The
[local regression report for that workflow](reports/regression-reviewed.json) records **81 tests
passed**, with **4 Docker checks skipped locally** and exercised by Linux CI.

```sh
python scripts/evaluate_agent.py --live --model gpt-6.1-sol --repeats 2 --max-turns 2 --workflow exact_review --output reports/live-agent-reviewed.json
```

An authenticated Codex CLI proposes structured actions using synthetic course documents. A trusted broker executes each proposal through a separate HTTP gateway and supplies denial feedback for a bounded retry. Native agent tools are outside this experiment. See the [method, limits and run instructions](docs/live-agent-evaluation.md), [live results](reports/live-agent.json) and [local regression results](reports/regression-agent.json).

```sh
python scripts/evaluate_agent.py --live --model gpt-6.1-sol --repeats 2 --max-turns 2
```

This opt-in command consumes authenticated model usage. Default tests and CI make no model calls. The report separates agent abstentions, successful blocks, missed blocks, content-safe false blocks, legitimate-task completion, tokens and latency. A zero-miss smoke run is not a general safety guarantee; subscription dollar charges are unavailable and recorded as null.

### Measured smoke result — 2026-10-13

Two repetitions of eight fixed cases with `gpt-6.1-sol` completed **24 model calls** without adapter errors. The paired local-outbox experiment recorded:

| Measurement | Observed result |
|---|---|
| Unsafe proposed actions blocked | **2 / 2**, both sends after operator stop |
| Detected unsafe deliveries | **0** |
| Agent abstentions | **10**, counted separately from gateway blocks |
| Content-safe sends denied | **6 / 12 (50%)**, conservative exposure/review policy |
| Legitimate delivery tasks completed | **6 / 12 (50%)** |
| Exact reviewed release | **2 / 2** tasks completed |
| Model usage | **250,531 input tokens**, including **34,304 cached**; **1,353 output tokens** |
| Wall time | **280.89 s** model calls; **0.65 s** gateway decisions |

The model refused unapproved secret publication and ignored the embedded injection. Therefore this run does **not** demonstrate gateway prevention of a model-generated secret leak or successful prompt injection. The small sample shows working stop/approval controls and a substantial usability cost, rather than broad safety effectiveness. The [initial run](reports/live-agent-initial.json) is retained: its overly strict drafting prompt prevented the approval case from completing; the revised prompt permits a draft for exact operator review without granting model-controlled permission.

## New in v0.3

- `untrusted` input labels enforce exact human approval before influenced output can be delivered, even internally.
- A trusted broker starts a fresh, network-disabled container per invocation with only the current task's selected inputs. Workers propose text, never permissions or tool commands.
- Read-only root filesystem, non-root user, dropped capabilities, resource/output limits, stop polling and forced cleanup constrain offline execution.
- [Isolation guide and real-container checks](docs/isolation.md). Without Docker execution is refused. The bundled worker is a deterministic probe; the remote-model path above is separate from that worker.

TAHU 在马来文中意为“知道”，中文取意“知·道”。我们把可追溯、有授权、人类监督与不确定性识别转化为可测试的执行规则。道家思想是设计启发；安全效果以代码和实验为准。

## Start in one minute

Python 3.10+; no runtime third-party dependencies. From the repository directory:

```sh
python -m examples.demo
python -m unittest discover -s tests -v
```

The demo starts a separate gateway process on an ephemeral loopback port, creates two tasks with synthetic data, exercises the HTTP API, and removes its temporary credentials and database on exit.

Expected demonstration:

1. An authorized task reads a synthetic secret.
2. A derived draft omits its sources; the session restriction still follows it.
3. Public delivery is denied.
4. A separate public-only task can still publish its public artifact.
5. An operator approves one exact artifact/destination pair for 60 seconds.
6. One delivery enters the local outbox; reuse with a new request ID is denied.
7. The operator stops the task; further reads are denied.

For a persistent local gateway:

```sh
python -m tahu init
python -m tahu serve --port 8765
```

State is saved under `.tahu/`. `operator.json` contains a generated credential. **Keep that directory private and outside the agent's filesystem access.** On Windows, also restrict its ACL to the service account; POSIX file modes do not establish Windows isolation. Never commit credentials or the database. The default development server binds only to `127.0.0.1`.

## Implemented

| Control | v0.2 implementation |
|---|---|
| Task authorization | Operator-created immutable task policy; per-task bearer token stored only as a hash |
| Information flow | Source-label inheritance plus persistent task exposure; unknown classification blocks delivery |
| Scope separation | Separate artifact registries and exposure per task; the external orchestrator must also separate model contexts |
| Human approval | Operator-only, artifact/content/destination-bound, expiring, one-use approval |
| Stop control | Durable task stop; new actions and cached reads are denied after stop commits |
| Resource bounds | Accepted-operation budget, attempt limit, task expiry, bounded request size |
| Retry safety | Request IDs bind exact request hashes; retries return receipts without repeating outbox effects |
| Concurrent safety | SQLite write transactions serialize policy check, grant consumption, outbox effect and audit |
| Traceability | Redacted audit events with a SHA-256 hash chain and a verification endpoint |
| Failure behavior | Storage/audit failures roll back the transaction; malformed operations are denied safely |

## Evaluation

The committed [machine-readable report](reports/latest.json) records the actual local run. The v0.3 local run passed **54 tests**, with **4 real-container tests explicitly skipped** because Docker was unavailable; the separate-process HTTP demonstration also passed. The Linux isolation CI job is the separate source of real-container evidence. Tests cover malformed requests, privilege separation, provenance omission, cross-task access, replay, approval reuse, concurrent grant consumption, expiry, restart persistence, audit mutation and transactional rollback.

```sh
python scripts/evaluate.py
```

This writes `reports/latest.json` and returns a nonzero exit code on failures. Tests use `unittest` rather than removable bare `assert` statements. The regression suite is authored alongside the implementation; it is not an independent security benchmark or a real-world safety success rate. CI also runs on Windows/Linux and Python 3.10/3.14.

**Known counterexample:** reading sensitive data and then generating `2 + 2 = 4` in the same task still blocks public delivery. A clean task avoids that restriction only if the host actually supplies a fresh, public-only model context. Do not reuse a model's sensitive memory under a clean token.

## How this differs from v0.1

The original four files are preserved unchanged in [legacy/v0_1](legacy/v0_1/README.md). v0.1 was an in-memory simulator. v0.2 adds a separate HTTP service, role credentials, durable transactional state, task-scoped registries, expiring approvals, idempotent outbox delivery, bounded requests and regression coverage. It fixes the malformed-operation crash and the mutable audit-input problem found during review.

In v0.2, even an existing public artifact cannot be sent publicly by a task exposed to restricted data without approval. This is deliberately stricter than v0.1. Actual model-context isolation is a host responsibility, not something a task ID proves.

## Documentation

- [中文说明](docs/README.zh-CN.md)
- [Independent mail comparison, failures and reproduction](docs/mail-comparison.md)
- [Public-only context preparation and its separate experiment](docs/public-context.md)
- [Adoption steps, pending license choices and unpublished feedback drafts](docs/adoption.md)
- [Live agent evaluation and measured limits](docs/live-agent-evaluation.md)
- [Architecture and trust boundary](docs/architecture.md)
- [API and Python integration](docs/api.md)
- [Threat model and known limits](docs/threat-model.md)
- [Roadmap and release gates](docs/roadmap.md)
- [Security reporting](SECURITY.md)
- [Contribution guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Research context

Information-flow control, taint propagation, least privilege and external execution checks have substantial prior work. TAHU does not claim to have invented them. Relevant comparison points include [CaMeL](https://arxiv.org/abs/2503.18813), [NeMo Guardrails](https://arxiv.org/abs/2310.10501), and [the International AI Safety Report](https://internationalaisafetyreport.org/publication/international-ai-safety-report-2026). They are references, not endorsements of TAHU. See the roadmap for comparative evaluation work still required.

## License

No open-source license has been selected yet. Public repository visibility is not a license grant. A license can be added by the project owner before broader reuse is invited.
