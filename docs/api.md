# HTTP API

## v0.3 additions

Artifact labels additionally accept `untrusted`. It cannot be a destination clearance. Any influenced send requires exact one-use approval or returns `untrusted_review_required`. Unknown classification remains non-approvable. See [isolation.md](isolation.md) for the operator-only `tahu.isolation.execute_isolated` Python API. No worker execution HTTP endpoint is exposed.

Base URL for local development: `http://127.0.0.1:8765`.
All POST routes require `Content-Type: application/json`, one bounded Content-Length and `Authorization: Bearer TOKEN`. Browser Origin headers are rejected. There is no CORS support. Maximum request size: 65,536 bytes. Duplicate JSON keys and nonfinite numbers are rejected.

| Route | Credential | Purpose |
|---|---|---|
| GET `/health` | None | Version and local sink information |
| POST `/v1/tasks` | Operator | Create immutable task policy and receive a task token once |
| POST `/v1/step` | Task | Read, derive or send within that task |
| POST `/v1/approve` | Operator | Approve exact release, TTL 1–300 seconds |
| POST `/v1/stop` | Operator | Persistently stop task and delete its approvals |
| POST `/v1/audit` | Operator | Read redacted audit records, body `{}` |
| POST `/v1/audit/verify` | Operator | Verify internal hash chain, body `{}` |
| POST `/v1/outbox` | Operator | Inspect local deliveries, body `{}` |

## Create a task

```json
{
  "id": "report",
  "purpose": "Prepare a synthetic internal report",
  "budget": 20,
  "attempt_limit": 40,
  "ttl": 3600,
  "destinations": {"public": [], "internal": ["restricted"]},
  "artifacts": [
    {"id": "note", "text": "SYNTHETIC SECRET", "labels": ["restricted"]}
  ]
}
```

The response contains `task` and a newly generated `token`. Keep it out of logs and prompts. Operators decide which initial artifacts are readable by a task. Providing an artifact grants that task read access to it.

## Agent proposals

```json
{"request_id":"read_1","op":"read","id":"note"}
```

```json
{"request_id":"derive_1","op":"derive","id":"draft","sources":["note"],"text":"Synthetic summary"}
```

```json
{"request_id":"send_1","op":"send","id":"draft","destination":"public"}
```

An action decision returns HTTP 200 with `allowed` and `reason`; successful reads include text in `result`. A send's `delivery_id` identifies a **local outbox entry**, not an email or external message. Rejected steps have no outbox side effects. Validation before authenticated task dispatch may return HTTP 400/401/403/413/415 instead and does not create a task audit event.

Each request ID identifies one exact proposal. Retry the same body with the same ID for transport uncertainty; use a new ID after policy circumstances change, including a new approval. Previously denied receipts remain denied. Retries count toward attempt limits. Stop, expiry and exhausted attempts take precedence over cached responses.

## Approval and stop

```json
{"task":"report","artifact":"draft","destination":"public","ttl":60}
```

Approval permits an exact content release; the authenticated operator must inspect that content before approving. `content_hash` in the response identifies the bound artifact text. Approvals cannot add a destination outside the original policy.

Trusted reviewers may additionally send `expected_content_hash`, the 64-character
lowercase SHA-256 from `tahu.core.digest(reviewed_text)`. The gateway compares it
with the stored immutable artifact inside the approval transaction and refuses
any mismatch before creating a grant. Omit it for legacy clients. This digest is
over TAHU's canonical JSON encoding of the string, not raw UTF-8 text bytes.

`tahu.review.TemplateReviewer` uses this field for preconfigured exact-template
rules bound to a task, destination and allowed source IDs. Only independently
trusted records may supply a rule; the model, its draft and untrusted documents
cannot create rules. A matched rule still uses the ordinary expiring, one-use
operator approval. Stop, unknown classification and destination policy remain
enforced. After approval, use a **new** send request ID; the original denial
receipt remains denied.

```json
{"task":"report"}
```

Send the latter to `/v1/stop`. No resume endpoint exists. A trusted operator can create a new task; stopping one task does not revoke the operator's authority.

## Model integration contract

### Optional guarded local mail executor

When `make_server(..., mail_executor=...)` is configured by the trusted host,
the operator can call `/v1/execute-mail` with `{"delivery_id":"<outbox ID>"}`.
Task tokens receive HTTP 403. Without an executor this endpoint returns HTTP 503.
The caller cannot supply text, destinations, network addresses or executable
commands. The executor uses the stored, revalidated outbox entry only.

Responses distinguish `SUCCEEDED`, `DENIED` and `UNKNOWN`. A completed replay
returns its recorded result without another SMTP effect. An interrupted
`EXECUTING` record is returned as `UNKNOWN`; do not retry it automatically.
`SUCCEEDED` means the local receiver acknowledged capture, not Internet delivery.
See [execution-boundary.md](execution-boundary.md) for stop ordering, durability,
fixture setup and the trusted-host limits. The ordinary CLI remains outbox-only.

```python
from tahu.client import Client

client = Client("http://127.0.0.1:8765", task_token)
decision = client.step(proposal)
if not decision["allowed"]:
    # Return the denial to the orchestrator. Never execute the action directly.
    print(decision["reason"])
```

The trusted orchestrator provisions fresh contexts and mediates the model's only tool channel. Do not put `operator_token` in model context, tool arguments or agent-readable files. The optional Codex CLI adapter and [live evaluation](live-agent-evaluation.md) exercise this contract with synthetic data. A transport failure means execution is unconfirmed; use exact-ID retry, never fallback direct execution.
