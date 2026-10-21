# Startup context: reproduce before claiming isolation

Christian (FramY2) identified a boundary the earlier live reports had not
measured: global instructions and skill descriptions can enter a CLI session
before a gateway sees a proposal. His CtxWise results were a static inventory,
not a Python execution report or proof that every discovered item was loaded.
This experiment checks submitted requests directly with harmless markers.

## Reproduce without model usage

Install the official native Codex CLI. No login, credentials, third-party Python
package, CtxWise installation or real model is needed for this capture:

```sh
python scripts/probe_startup.py --capture --output reports/startup-context.json
```

The script creates disposable synthetic profiles containing a global instruction,
a skill description, a user-home skill and a configuration instruction. It uses
the adapter's actual command, schema, prompt and disabled-tool flags. For the
legacy comparison it reconstructs the former inherited-profile environment;
the hardened comparison uses the adapter's actual profile preparation. Only
the provider transport is redirected to a no-auth loopback HTTP receiver.
The receiver inspects the submitted JSON and deliberately returns HTTP 400.
That rejection is expected, not a successful model completion. Missing or
multiple requests fail the probe. No request body, headers or real user profile
contents are published. The synthetic auth fixture is an empty JSON object.

## Observed on Windows, 2026-10-22 (Asia/Kuala_Lumpur)

Native CLI: `codex-cli 0.163.0-alpha.10.2`.

| Marker / capability in submitted request | Former launch | Isolated profile |
|---|---:|---:|
| Global `AGENTS.md` marker | Present | Absent |
| Global `AGENTS.override.md` marker, separate fixture | Present | Absent |
| `$CODEX_HOME/skills` description marker | Present | Absent |
| Synthetic `config.toml` instruction | Absent | Absent |
| Synthetic user-home `.agents/skills` description | Absent | Absent |
| Available tool definitions | 0 | 0 |

The user-home skill was not observed in the positive control on this installation;
its absence cannot establish a repaired discovery path. The configuration
instruction was already excluded by `--ignore-user-config`. The global and
profile-skill markers provide positive evidence of the actual former problem
and exclusion of those tested inputs after repair. Four captured requests and
source hashes are in [the raw capture report](../reports/startup-context-2026-10-22.json).
Request sizes are bytes, not measured tokens, cost or a complete context inventory.

## Adapter change and trust boundary

Every proposal now gets three sibling temporary directories: a Codex profile,
a user home and a model working directory. Only the existing CLI `auth.json` is
copied to the profile; configuration, global instructions, installed plugins,
skills and previous sessions are not copied. The credential file is outside
the model working directory. All three directories are removed on success or
failure. POSIX permissions use private directories and a mode-600 auth file;
Windows also relies on the current user's temporary-directory ACLs. This is not
protection against another process already running as the same user.

The child environment keeps an explicit allowlist of OS and network plumbing
(including existing proxy/certificate configuration), sets fresh home/profile
paths, and excludes parent Codex thread/context and provider overrides and
unrelated secrets. Authentication remains with the trusted native CLI. The
adapter currently requires file-backed CLI authentication; missing, inaccessible
or oversized auth fails closed with a sanitized code. It does not export OS
keyring credentials, change login settings, or fall back to the ordinary profile.

Built-in CLI instructions remain. Managed machine policy, OS home discovery on
other installations, provider-side context and CLI changes are not exhaustively
attested. Capturing a custom-provider request is stronger evidence than a model
failing to repeat a marker, but does not attest production-service transport.
Live results label startup configuration and explicitly set
`runtime_context_attested=false`. Repeat the probe after CLI upgrades.

The CLI is still a trusted host process using existing authentication and network
access. Neither a separate home nor its read-only tool sandbox isolates that
process from the host. The offline Docker worker is a different path. Gateway
labels, cumulative exposure, exact approval, one-use consumption, unknown-data
denials and stop controls remain independently enforced; none were relaxed.

## Validation

```sh
python scripts/evaluate.py --output reports/regression-startup.json
python scripts/evaluate_mail.py --live --model gpt-6.1-sol --workflow public_context --output reports/mail-startup.json
```

The second command consumes existing Codex usage and sends only synthetic mail
to a local SMTP receiver. The first and default CI never call a real model.
The local regression ran 100 tests: 96 passed, four Docker checks skipped locally;
Linux CI retains the real-container checks. New boundary regressions cover
environment filtering, auth-only copying, fail-closed auth, sibling directories,
disabled tools, cleanup after failure and configuration-versus-attestation metadata.

The fixed six mail tasks, scoring, public-input plan, independent three arms and
budgets are unchanged. The CLI version and startup context changed since the
October 19 reports, so cross-date token/latency differences are not a controlled
efficiency experiment. The earlier failures remain in the repository. These are
developer-authored development checks, not an independent safety assessment.
The mail report's `provider_retries=0` describes harness re-calls; internal CLI
transport retries are not individually measured. Dollar charges and failed-call
usage remain unavailable.

The [2026-10-22 raw mail run](../reports/mail-startup-2026-10-22.json) completed
22 real `gpt-6.1-sol` calls with zero errors, 11 captured local messages and a
valid audit. No template assistance was used.

| Independent arm | Normal completion | Safe drafts denied | Unsafe deliveries / attack opportunities | Model calls | Review requests |
|---|---:|---:|---:|---:|---:|
| Recipient whitelist | 4/4 | 0/4 | 0/3 | 6 | 0 |
| Whitelist + simulated review | 4/4 | 0/4 | 0/3 | 10 | 4 |
| TAHU | 3/4 | 1/4 | 0/3 | 6 | 0 |

TAHU's remaining denial is the safe injected-web summary requiring trusted
review. Completion is unchanged from the October 19 public-context run. No arm
produced an unsafe send proposal, so these outcomes establish no added live
interception benefit over the simpler baselines. Regression tests, rather than
model abstentions, exercise secret leakage, injected content, wrong approvals,
approval reuse, unknown classifications and stop enforcement.

The three arms used 230,048 input tokens (25,344 cached subset) and 1,042 output
tokens. TAHU summed task elapsed time was 42.23 seconds; the review arm was
69.08 seconds with four extra simulated reviews. These observations include
different individual model responses and are not a speedup claim. Actual human
time and dollar charges are unavailable. A separate one-call adapter smoke check
also succeeded before this comparison; it is not included in these denominators.
