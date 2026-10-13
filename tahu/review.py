"""Trusted exact-template approval, never a model-driven declassifier.

Configure rules from independently trusted records before invoking the agent.
Do not construct rules from a draft, untrusted document, or grading oracle.
"""
import threading
from dataclasses import dataclass
from urllib.error import HTTPError

from .agent import validate_proposal
from .core import Invalid, digest, identifier


@dataclass(frozen=True)
class ReleaseRule:
    task: str
    destination: str
    text: str
    sources: frozenset

    def __post_init__(self):
        if (not identifier(self.task) or not identifier(self.destination)
                or not isinstance(self.text, str) or not 0 < len(self.text) <= 8000
                or not isinstance(self.sources, frozenset) or not self.sources
                or not all(identifier(source) for source in self.sources)):
            raise Invalid("invalid_exact_release_rule")

    def matches(self, task, proposal):
        validate_proposal(proposal)
        return (task == self.task and proposal["action"] == "send"
                and proposal["destination"] == self.destination
                and proposal["text"] == self.text
                and bool(proposal["sources"])
                and set(proposal["sources"]) <= self.sources)


class TemplateReviewer:
    """One grant per artifact per reviewer; gateway still checks expiry/stop/use.

    Operator-token HTTP requests remain in the trusted host. A rule is an
    explicit prior authorization for one exact text, not automatic semantic
    approval of arbitrary text or detection of all possible secrets.
    """
    def __init__(self, rules):
        self.rules = tuple(rules)
        if not all(isinstance(rule, ReleaseRule) for rule in self.rules):
            raise Invalid("release_rules_required")
        self._used = set()
        self._lock = threading.Lock()

    def approve(self, operator, task, artifact, proposal):
        if not identifier(artifact):
            raise Invalid("invalid_review_artifact")
        if not any(rule.matches(task, proposal) for rule in self.rules):
            return False
        key = (task, artifact, proposal["destination"])
        with self._lock:
            if key in self._used:
                return False
            # Fail closed even when the HTTP response is lost; never reissue a
            # consumed grant simply because this host can call /v1/approve.
            self._used.add(key)
            try:
                result = operator.call("/v1/approve", {"task": task, "artifact": artifact,
                                       "destination": proposal["destination"], "ttl": 60,
                                       "expected_content_hash": digest(proposal["text"])})
            except HTTPError as exc:
                exc.close()
                if exc.code == 400:  # e.g. task stopped/expired or unknown labels
                    return False
                raise
            return result.get("approved") is True
