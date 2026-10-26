# Contributing

Start with the architecture and threat model. Use synthetic data only. Keep secrets and generated service state out of commits. A public repository is not permission to test third-party systems.

Run `python -m unittest discover -s tests -v` and `python scripts/evaluate.py`. For changes to approval, information flow or persistence, include a regression test demonstrating the previously failing behavior. Do not remove the known-overblocking test to inflate reported utility.

Distinguish implemented controls, measured results, assumptions and future plans in every change. Report the actual model and environment when introducing live-model experiments. TAHU uses Apache-2.0; submit only contributions you have the right to provide under those terms, and preserve applicable third-party notices.
