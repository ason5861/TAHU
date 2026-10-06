# Isolated execution (v0.3)

This optional **offline, one-shot** runner mitigates specific input-integrity,
cross-task state and OS-access failures. It does not make an LLM immune to prompt
injection, erase model weights, or defeat container/kernel exploits.

## Input integrity

The trusted operator must label web pages, retrieved text and other attacker-controlled
inputs `untrusted`. This is independent of confidentiality: public text can be malicious.
Reads and derivations monotonically propagate it through the task, even when a worker
omits provenance or selects an existing public artifact. Sending to **any** destination
requires an exact, expiring, one-use operator grant. The grant does not cleanse context.
`unknown` classification still cannot be approved. Existing unlabeled inputs are NOT
automatically reclassified; review their provenance before use.

This enforces review of potentially influenced output; it does not detect malicious
language or guarantee correct human judgment. Effects remain local SQLite outbox entries.

## Trusted host and disposable worker

`execute_isolated` is an operator-only Python API, not an agent HTTP endpoint.
The trusted host chooses an existing task, source IDs, output ID and destination.
It reads sources through the gateway before handing them to the worker, recording
exposure. Only the task purpose and selected documents go to stdin. No tokens,
database, shared chat history or host paths are handed to the worker. Each invocation
starts a new container; no worker process or writable file is reused. Repeated calls
on the same task still inherit that task's gateway exposure.

Workers return exactly `{"text":"..."}`. Extra fields, tool calls, task IDs, approvals,
malformed JSON and oversized output fail closed. The host stores text as a derived
artifact and checks delivery through the gateway. Raw worker text and stderr are
not returned as a successful public result.

## OS controls and remaining trust

Requires a Linux Docker engine advertising seccomp and a reviewed, secret-free image
selected by immutable local `sha256:...` image ID. Images with declared volumes are
rejected. No bind mounts, shared volumes, Docker socket, provider keys or host network
are supplied. Network is disabled; the root filesystem is read-only; UID is 65534;
all capabilities are dropped; no-new-privileges, memory/CPU/process limits and bounded
tmpfs are applied. Both output pipes and wall time are bounded. Docker logs are disabled.
Workers are polled for task stop/expiry and forcibly removed. The gateway independently
rejects results after stop. Cleanup failure is reported.

Docker, its daemon account, image contents, host and kernel remain trusted. Container
escapes and operator compromise are outside the guarantee. Prefer a dedicated VM/host
for hostile workloads. A host crash or daemon failure can prevent prompt cleanup;
there is no instantaneous universal shutdown guarantee. Reads and derivations consume
the existing task action budget; CPU/time limits apply separately per invocation.

No provider API adapter is implemented. The bundled worker is a deterministic test
probe, not Claude, Codex or an LLM. A future API broker must own credentials, use
task-isolated conversation state, authorize outbound data, and avoid shared provider
threads/caches. Do not enable unrestricted networking to add a model.

## Run real container checks

With a trusted Linux Docker engine (or Docker Desktop in Linux-container mode):

```sh
docker build -t tahu-probe:local sandbox
docker image inspect tahu-probe:local --format '{{.Id}}'
```

The test Dockerfile resolves `python:3.12-slim` at build time. Review/update that base
in your deployment; runtime accepts only the resulting immutable ID.

Linux:

```sh
export TAHU_TEST_IMAGE=$(docker image inspect tahu-probe:local --format '{{.Id}}')
python -m unittest tests.test_isolation.DockerIntegrationTests -v
python -m examples.isolated_demo --image "$TAHU_TEST_IMAGE"
```

PowerShell:

```powershell
$env:TAHU_TEST_IMAGE = docker image inspect tahu-probe:local --format '{{.Id}}'
python -m unittest tests.test_isolation.DockerIntegrationTests -v
python -m examples.isolated_demo --image $env:TAHU_TEST_IMAGE
```

Without Docker, execution refuses to start; there is no host fallback. Ordinary tests
explicitly skip container checks unless the test image is set. Skips are NOT evidence
that OS isolation works. Linux CI builds the probe, runs real-container checks and
the end-to-end isolated demo.

The original same-task `2 + 2 = 4` overblocking example remains. A clean task plus a
fresh worker avoids previous runtime history; clearing labels on contaminated context
would reopen a leak. Shared model weights and externally reintroduced history remain
outside this protection.
