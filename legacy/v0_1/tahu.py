"""TAHU 0.1: deterministic, in-memory research demonstrator; not a security sandbox."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Artifact:
    text: str
    labels: frozenset[str]


class Monitor:
    """Trusted harness owns registry/policy. Agent submits step dictionaries only.

    Modes: tools = tool allowlist; lineage = artifact labels;
    tahu = artifact labels plus conservative session exposure tracking.
    """

    def __init__(self, mode="tahu", budget=10):
        if mode not in {"tools", "lineage", "tahu"}:
            raise ValueError("unknown mode")
        self.mode, self.budget = mode, budget
        self.used, self.stopped = 0, False
        self.exposure = frozenset()
        self.registry = {
            "public": Artifact("Public course information", frozenset()),
            "private": Artifact("SYNTHETIC confidential note", frozenset({"restricted"})),
            "unknown": Artifact("Unclassified synthetic note", frozenset({"unknown"})),
        }
        # Installed by the trusted harness, never by a submitted step.
        self.clearances = {"public": frozenset(), "internal": frozenset({"restricted"})}
        self.grants = set()
        self.log, self.deliveries = [], []

    def approve(self, artifact, destination):
        """Trusted operator hook: one-use grant for immutable artifact and destination."""
        if artifact not in self.registry or destination not in self.clearances:
            raise ValueError("invalid grant")
        if "unknown" in self.registry[artifact].labels:
            raise ValueError("classify unknown source before approving")
        self.grants.add((artifact, destination))

    def stop(self):
        self.stopped = True
        self.log.append({"event": "operator_stop"})

    def step(self, request):
        """Deny before side effects. No network/file execution exists in this demo."""
        def done(allowed, reason):
            self.log.append({"sequence": len(self.log) + 1,
                             "request": dict(request), "allowed": allowed,
                             "reason": reason, "used": self.used,
                             "exposure": sorted(self.exposure)})
            return allowed

        if self.stopped:
            return done(False, "operator_stopped")
        if self.used >= self.budget:
            return done(False, "action_budget_exhausted")
        op = request.get("op")
        fields = {"read": {"op", "id"}, "derive": {"op", "id", "sources", "text"},
                  "send": {"op", "id", "destination"}}
        if op not in fields:
            return done(False, "unauthorized_tool")
        if set(request) != fields[op]:
            return done(False, "invalid_request_fields")
        key = request["id"]
        if not isinstance(key, str):
            return done(False, "invalid_id")
        if op in {"read", "send"} and key not in self.registry:
            return done(False, "unknown_artifact")
        if op == "read":
            self.exposure |= self.registry[key].labels
        elif op == "derive":
            sources = request["sources"]
            if key in self.registry:
                return done(False, "immutable_artifact")
            if (not isinstance(sources, list) or
                    any(not isinstance(s, str) or s not in self.registry for s in sources) or
                    not isinstance(request["text"], str)):
                return done(False, "invalid_sources_or_text")
            labels = frozenset().union(*(self.registry[s].labels for s in sources))
            # Transform invocation also exposes its inputs to the simulated agent.
            self.exposure |= labels
            if self.mode == "tahu":
                labels |= self.exposure
            self.registry[key] = Artifact(request["text"], labels)
        else:
            dest = request["destination"]
            if not isinstance(dest, str) or dest not in self.clearances:
                return done(False, "unknown_destination")
            artifact = self.registry[key]
            grant = (key, dest)
            if self.mode != "tools":
                if "unknown" in artifact.labels:
                    return done(False, "classification_required")
                if not artifact.labels <= self.clearances[dest] and grant not in self.grants:
                    return done(False, "information_flow_denied")
            self.grants.discard(grant)
            self.deliveries.append({"id": key, "destination": dest, "text": artifact.text})
        self.used += 1
        return done(True, "allowed")
