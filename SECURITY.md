# Security

TAHU 0.2 is research software using synthetic data. Do not expose its development HTTP server to the internet or use it as the sole boundary around sensitive production operations.

Use GitHub's private vulnerability reporting when enabled, or contact the repository owner privately. Do not post real credentials, private data or exploitable production details in public issues. Public issues are appropriate for ordinary bugs with fully synthetic reproduction data.

Review [the threat model](docs/threat-model.md) before integration. The service account, operator, filesystem and SQLite database are trusted. A separate process alone is not an OS security boundary. Windows deployments need appropriate ACLs and separate user identities.

No security certification, independent audit or general AI-control guarantee is claimed. The owner has not specified a response-time SLA.
