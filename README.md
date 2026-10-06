# TAHU · 知道

**Traceability · Authorization · Human Oversight · Uncertainty Awareness**

A research authorization gateway for AI agents. An agent proposes actions; a separate local service checks task permissions, information flow, approvals and stop state before recording an authorized delivery.

**Status: v0.2.0, runnable research software.** No live AI model has been evaluated. Deliveries go to a local SQLite outbox, not email or the internet. This project does not claim to solve general AI loss of control or provide an operating-system sandbox.

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

The committed [machine-readable report](reports/latest.json) records the actual local run. Initially **39 automated tests passed**, plus a separate-process HTTP demonstration. Tests cover malformed requests, privilege separation, provenance omission, cross-task access, replay, approval reuse, concurrent grant consumption, expiry, restart persistence, audit mutation and transactional rollback.

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
