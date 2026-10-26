# Guarded local execution boundary

## Problem and supported repair

The previous mail experiment exported an accepted outbox row and called an
unguarded SMTP sink. Stopping the task after enqueue did not prevent this later
send. The [pre-repair probe](../reports/execution-boundary-2026-10-26.json)
records one such receiver effect. Its script hash describes an unpublished
pre-repair working snapshot, not the current probe. Historical live reports
also describe the previous transport; they are not evidence for this repair.

The TAHU arm now executes via `/v1/execute-mail`, which requires the operator
credential and an explicitly configured trusted executor. The model submits
proposals; it receives neither this credential nor the receiver capability.
The ordinary CLI is still outbox-only. The local experiment fixture
`tahu.mail_fixture.mail_gateway` configures the guarded executor. Its HTTP
gateway runs in a thread of the trusted fixture host; this is process-local
integration evidence, not OS separation of that host.

Each accepted send now creates an execution manifest containing the digest of
task, action, artifact, full text and destination; the task policy digest; the
enforcement version; and the exact approval expiry, if used. Existing database
outbox rows without manifests are denied rather than silently grandfathered in.
Task policies remain immutable through the public API. Future changes to policy
semantics must update `POLICY_VERSION`, invalidating queued older authorizations.

Immediately before execution, the gateway rechecks this binding, the current
task stop/expiry, artifact identity/text, destination, accumulated exposure,
unknown classification and approval expiry. It never accepts caller-supplied
replacement mail content. Approval remains a one-use enqueue authorization;
the resulting delivery ID is separately executable at most once.

## Stop ordering and uncertain results

`AUTHORIZED -> EXECUTING -> SUCCEEDED / DENIED / UNKNOWN`

Execution start is committed before attempting an effect. The second SQLite
write transaction holds its lock across revalidation and the bounded local SMTP
callback. If stop commits first, execution is denied. If execution acquires the
lock first, stop waits for that effect to finish; it cannot recall mail already
captured. This deliberate serialization is appropriate for a short local
fixture, not a scalable general external transaction. Other writes can wait
or receive the existing storage-unavailable error while the lock is held.

An exception after DATA may mean capture occurred but the acknowledgement was
lost. The state is UNKNOWN, never an automatic retry. A crash can leave a durable
EXECUTING record; later calls return UNKNOWN without executing again. The local
receiver transcript can support manual reconciliation; a production recovery
and compensation interface is not implemented. Even an audit failure after an
effect leaves the durable start as evidence of uncertainty rather than reopening
the delivery. A successful recorded replay does not send again.

## Receiver and host responsibilities

The guarded receiver rejects ordinary `send()` and raw unauthenticated SMTP.
Only the configured executor uses a random host-held capability to access this
loopback-only `.test` sink. Unguarded receivers still exist solely for explicit
no-enforcement/comparison fixtures. They must never be used as TAHU executors.

The capability, database, operator, Python code and host are trusted. A hostile
Python program sharing their process can inspect objects, obtain the capability
or call private internals; this repair does not sandbox it. The model adapter
has no SMTP tool and supplies structured proposals, but the native CLI itself
remains a trusted networked process. OS egress restrictions and host compromise
protection remain deployment responsibilities. The fixture protocol is local
test infrastructure, not TLS-authenticated production SMTP.

Arbitrary file writes, HTTP side effects, browser actions, payments and remote
tool execution are not connected to this executor. The offline Docker runner
is a separate restricted computation path. No universal unbypassable execution
boundary or independent security audit is claimed.

## Reproduction and evidence

```sh
python -m unittest tests.test_execution tests.test_http tests.test_mail -v
python scripts/probe_execution_boundary.py --output reports/execution-boundary-recheck.json
python -m examples.mail_demo --workflow public_context
```

All data is synthetic. Only temporary files and loopback HTTP/SMTP are used;
there are no real-model calls, account credentials or third-party deliveries.
The [fixed probe](../reports/execution-boundary-fixed-2026-10-26.json) retains
eight forced attack requests and two normal controls: zero guarded attack
effects, two normal captures, direct send refused, pending execution after stop
denied. The eight unguarded captures are sink-availability positive controls
using a fixed synthetic body; they are not matched independent model baselines.
The stop/bypass checks are reported separately, not hidden by changing the
eight-request denominator. These cases are a development set.

Tests additionally exercise concurrent execution/replay, full payload and
destination changes, policy/version changes, expiry, new exposure, missing old
manifests, lost acknowledgement, crash recovery and stop while an effect is in
flight. This is developer-authored integration/regression evidence. Existing
free-text utility failures and the need for independent live adversarial
validation remain.
