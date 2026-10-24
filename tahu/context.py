"""Host-owned input minimization, not declassification or draft approval.

Configure a fresh public job BEFORE giving any materials to the model. Never
feed a previous model's memory, request, draft or tool results into this helper.
The host owns record classification, request, hash pins and context isolation.
"""
import hashlib
import re
from dataclasses import dataclass

from .core import Invalid, identifier


@dataclass(frozen=True)
class PublicContextPlan:
    request: str
    records: tuple

    def __post_init__(self):
        if (not isinstance(self.request, str) or not 0 < len(self.request) <= 8000
                or not isinstance(self.records, tuple) or not 0 < len(self.records) <= 50
                or any(not isinstance(pin, tuple) or len(pin) != 2
                       or not identifier(pin[0]) or not isinstance(pin[1], str)
                       or not re.fullmatch(r"[0-9a-f]{64}", pin[1]) for pin in self.records)
                or len({pin[0] for pin in self.records}) != len(self.records)):
            raise Invalid("invalid_public_context_plan")

    def job(self, records):
        """Copy only pinned, classified-public records into a new empty history."""
        if (not isinstance(records, list) or any(not isinstance(record, dict)
                                                or not identifier(record.get("id")) for record in records)
                or len({record["id"] for record in records}) != len(records)):
            raise Invalid("ambiguous_public_records")
        registry = {record["id"]: record for record in records}
        selected = []
        for name, expected_hash in self.records:
            record = registry.get(name)
            if (not record or record.get("labels") != [] or not isinstance(record.get("text"), str)
                    or hashlib.sha256(record["text"].encode()).hexdigest() != expected_hash):
                raise Invalid("public_record_changed_or_not_public")
            selected.append({"id": name, "text": record["text"], "labels": []})
        return {"request": self.request, "documents": selected, "history": [],
                "operator_review_required": False}
