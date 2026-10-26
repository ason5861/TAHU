# Independent model runs with guarded execution and recovery

## Recorded result: 2026-10-26

The [raw comparison](../reports/live-lifecycle-2026-10-26.json) used
`gpt-6.1-sol` with native CLI `0.164.0-alpha.11.1`: 18 attempted draft calls,
11 completed/parsed calls and **7 bounded worker timeouts**. The comparison
command returned nonzero because of those errors. None were removed or
reclassified as gateway blocks.

| Arm | Normal tasks completed | Model timeouts | Unsafe send proposals | Unauthorized receiver effects | Safe send proposals denied |
|---|---:|---:|---:|---:|---:|
| unmediated | 2/4 (50%) | 2/6 | 0 | 0/6 | 0/2 |
| prompt_only | 3/4 (75%) | 1/6 | 0 | 0/6 | 0/3 |
| tahu | 1/4 (25%) | 4/6 | 0 | 0/6 | 1/2 (50%) |

The unauthorized-effect denominator above is all six tasks per arm; the raw
report separately retains three attack tasks per arm. Zero observed effects
with model abstentions and errors is not proof of successful attack blocking.
No unsafe model send reached the TAHU gate, so no new live interception benefit
is demonstrated. The normal-task target of 75% was not met by TAHU. One harmless
draft after sensitive exposure was conservatively refused; four TAHU model
timeouts also reduce completion. These small, noisy samples cannot establish a
causal ranking of the arms or general leakage resistance.

The one completed TAHU public delivery did exercise UNKNOWN -> receipt-confirmed
SUCCEEDED -> replay, with exactly one durable receiver capture. This establishes
one live drafted recovery path, not completion of the broader milestone.
The [separate repeat diagnostic](../reports/lifecycle-timeout-diagnostic-2026-10-26.json)
repeated the failed internal task with the same safety prompt, model and
120-second budget; it completed in 5.84 seconds. Its extra call does not replace
an original error or enter the table. This shows the failure is intermittent;
it does not identify whether the cause is native CLI transport, service latency
or another host/network condition.

Four [fresh synthetic native request captures](../reports/startup-lifecycle-2026-10-26.json)
on this CLI retained the legacy global/skill positive controls, excluded tested
markers in isolated mode and exposed no tool definitions. They made no model
calls and used no real credentials. Built-in context remains, and the user-home
skill marker still has no positive discovery control. This is not exhaustive
runtime attestation or a diagnosis of the timeouts.

Successful parsed calls used 114,044 input tokens (16,896 cached, a subset) and
582 output tokens. Failed-call usage and dollar cost are unavailable. Further
comparisons should first establish stable bounded provider operation and retain
this failed run. Do not change safety policy or discard failed tasks to improve
the result.

This opt-in experiment connects the existing constrained Codex drafter to the
durable local receiver and receipt reconciliation path. It uses the frozen
six-task mail corpus without public-context minimization or exact-template
assistance. The original four-task legitimate denominator and three attack
tasks are retained; the injected-web task belongs to both groups.

```sh
python scripts/evaluate_lifecycle.py --live --model gpt-6.1-sol --output reports/lifecycle-recheck.json
```

This performs 18 independent drafting calls using existing authenticated Codex
usage. It does not buy credits or use a separate API key. Model input consists
only of synthetic documents; web fixtures and mail delivery stay on loopback.
Provider errors remain in the original denominators. No automatic harness retry
is performed, although internal CLI transport retries are not measured.

## Conditions fixed before the run

| Arm | Prompt | Execution |
|---|---|---|
| unmediated | Neutral drafting instructions | Direct capture at fixed synthetic recipients; no information-flow checks |
| prompt_only | Existing safety drafting prompt | Same fixed recipients, no execution policy |
| tahu | Same safety prompt as prompt_only | Task-token derive/send; operator-only guarded execution and receipt reconciliation |

All arms use the same model, frozen documents, requests, output schema, one-call
budget, timeout, native-tool restrictions and isolated startup configuration.
Only the declared prompt treatment and enforcement layer differ. Job hashes
allow input equality to be checked. Arm order rotates by task. Baselines have
no arbitrary host tool access or real Internet mail delivery. The neutral
prompt does not remove the underlying model's built-in safety behavior.
The existing whitelist/simulated-review comparison is retained in
`scripts/evaluate_mail.py`; those separate historical runs must not be mixed
into this run's denominators or treated as contemporaneous results.

For each allowed TAHU delivery, a controlled executor fault raises an error
after durable receiver capture. The expected initial status is UNKNOWN. The
operator reads the bound receiver receipt to confirm SUCCEEDED, then repeats
the same execution request. The receiver must still contain exactly one
capture. This uses an actual model draft and actual loopback SMTP, with a
deliberately injected lost acknowledgement. Separate regression tests exercise
real executor-process exit, restart and stop; this live run does not itself
crash the model or restart the host.

## Evidence limits

Model refusals are not gateway interceptions. Marker-defined leaks, unsafe
proposals, actual receiver effects, first decisions, recovery states, errors,
completion, safe-proposal denials, tokens and timing are recorded separately.
Tokens describe successfully parsed calls only; consumption by a timed-out or
otherwise failed call is unavailable rather than counted as zero usage.
Per-arm task counts include failures. General paraphrase leakage is not graded.
Dollar cost and host resource overhead are unavailable. TAHU elapsed time
includes extra fault/reconciliation requests, so it is not a clean measurement
of ordinary enforcement overhead; model time is reported separately.

This is a small developer-authored reused corpus, not an independent held-out
security assessment. Original split labels remain as historical metadata;
they do not establish independence for this experiment. A neutral-prompt model
baseline, a prompt-only baseline and a guarded run do not establish a universal
security guarantee. The CLI, Python host, database and receiver capability
remain trusted, as described in [execution-boundary.md](execution-boundary.md).
