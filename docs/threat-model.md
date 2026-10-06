# Threat model and limitations

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

Exposure is monotonic. An unrelated public derivation is overblocked after a sensitive read. Independent task state reduces this only when a trusted host also separates contexts. A malicious agent must not choose a fresh task token for an already contaminated context. Legitimate approvals intentionally release exact sensitive content and therefore rely on a trustworthy operator.

The audit chain is unkeyed and has no remote anchor. It detects accidental or partial edits, but not a database owner rewriting all history. `purpose` is descriptive metadata, not an enforceable semantic goal. Attempt limits are counts, not time-based rate limiting. The local outbox is not a transactional guarantee for a future external email/payment connector.

## Production release blockers

No production security claim until OS isolation/egress controls, external executor failure handling, authenticated approval UX, live-model adversarial evaluation and independent review are implemented and tested. Keep experiments on synthetic data meanwhile.
