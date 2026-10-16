# Trying TAHU and collecting useful feedback

TAHU currently serves developers experimenting with mixed public/internal agent
workflows. Start with `python -m examples.mail_demo` from a Python 3.10+ checkout.
It uses only the standard library, ephemeral loopback HTTP/SMTP servers and
synthetic data. It needs permission to bind local ports; it does not require
Docker, an account, paid usage or sending mail outside this computer. The
scripted output demonstrates mechanisms, not model effectiveness.

For real-model evaluation, use the explicit opt-in command in
[the mail comparison](mail-comparison.md). A logged-in native Codex CLI and
available model usage are required. The host owns labels, recipient mapping,
credentials and context separation. Connecting a production agent still needs
host isolation and a durable delivery connector. Remote-model calls do not
inherit the separate offline Docker worker's network isolation.

The verified one-command local example is the current entry point. A Codespaces
configuration has not been tested; none is advertised as ready. Adding a cloud
environment before it improves this small standard-library example would add
account, permission and potential billing steps.

## License decision for the owner

No license has been selected. This is an adoption obstacle: developers do not
have a clear general grant to reuse or redistribute the code. This document
does not grant a license. Two choices worth reviewing:

| Choice | Why it could fit | Obligations / distinction |
|---|---|---|
| [MIT](https://choosealicense.com/licenses/mit/) | Short permissive license for a small library | Preserve copyright and license notice; no express contributor patent grant |
| [Apache-2.0](https://choosealicense.com/licenses/apache-2.0/) | Permissive adoption with an explicit contributor patent grant | Preserve relevant notices and state modifications; no trademark grant |

Apache-2.0 is a reasonable option if explicit patent terms matter to intended
integrators; MIT is simpler if the owner prioritizes a short license. The owner
must choose and confirm the right to license the included code before adding a
LICENSE file. No choice has been applied automatically.

## Community drafts — not published

These are reviewable drafts, not authorization to contact anyone. Recheck each
community's current rules and choose the channel before posting. Do not request
stars as a substitute for feedback. Use the repository's
[mail demonstration and results](mail-comparison.md) as the demo link.

**GitHub Discussions in a relevant agent integration project, if its rules allow
integration feedback:**

> I'm building TAHU, a small Python authorization gateway for agent actions.
> I added a reproducible mixed public/internal email experiment using real model
> drafts and a local SMTP receiver. Independent whitelist, model-review and
> TAHU runs expose an awkward result: conservative exposure checks still block
> harmless work. I'd like feedback on where a gateway would fit your integration,
> and which review interruptions would make it unusable. Code, exact tasks,
> captured synthetic mail and failed cases: https://github.com/ason5861/TAHU

**Show HN draft, subject to its submission rules:**

> Show HN: TAHU — a Python agent authorization gateway with a reproducible mail test
>
> The demo runs locally with Python's standard library. The live comparison uses
> separate model runs for a recipient whitelist, simulated approval and TAHU.
> It publishes utility costs alongside safety outcomes; the current small live
> run does not establish an added interception benefit. Looking for developers
> willing to try the local example and describe a concrete workflow it should
> handle better. https://github.com/ason5861/TAHU

**An agent/security developer forum's designated project-feedback thread:**

> Would persistent task exposure help your agent integration, or cause too many
> approval interruptions? TAHU has a six-task synthetic email comparison you can
> rerun, plus a no-model local demo. The aim is to measure added control versus
> simple recipient permissions and review, including normal-task failures.
> I'd value a reproducible counterexample or an integration pain point:
> https://github.com/ason5861/TAHU

Measure non-maintainer trials, reproducible feedback and repeat use. GitHub
traffic does not reliably identify individual viewers; do not claim all traffic
as organic users or infer adoption from stars. There is no measured “10x” growth
effect or seed-star threshold for this project.
