"""Transactional policy gateway. The caller supplies authenticated task identity.

This module is trusted server code, not an in-process sandbox for untrusted code.
"""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 64 and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


class Invalid(ValueError):
    pass


class Gateway:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, policy TEXT NOT NULL,
                    exposure TEXT NOT NULL DEFAULT '[]', used INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0, stopped INTEGER NOT NULL DEFAULT 0,
                    expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS artifacts (
                    task TEXT NOT NULL, id TEXT NOT NULL, text TEXT NOT NULL, labels TEXT NOT NULL,
                    PRIMARY KEY(task,id));
                CREATE TABLE IF NOT EXISTS grants (
                    task TEXT NOT NULL, artifact TEXT NOT NULL, destination TEXT NOT NULL,
                    content_hash TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(task,artifact,destination));
                CREATE TABLE IF NOT EXISTS receipts (
                    task TEXT NOT NULL, id TEXT NOT NULL, request_hash TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY(task,id));
                CREATE TABLE IF NOT EXISTS outbox (
                    id TEXT PRIMARY KEY, task TEXT NOT NULL, artifact TEXT NOT NULL,
                    destination TEXT NOT NULL, text TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
                    previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
            """)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def audit(db, event):
        event = dict(event, time=time.time())
        encoded = canonical(event)
        row = db.execute("SELECT hash FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        previous = row[0] if row else "0" * 64
        value = hashlib.sha256((previous + encoded).encode()).hexdigest()
        db.execute("INSERT INTO audit(event,previous_hash,hash) VALUES(?,?,?)", (encoded, previous, value))

    def create_task(self, data):
        if not isinstance(data, dict) or set(data) != {"id", "purpose", "budget", "attempt_limit", "ttl", "destinations", "artifacts"}:
            raise Invalid("invalid_task_fields")
        if not identifier(data["id"]) or not isinstance(data["purpose"], str) or not 1 <= len(data["purpose"]) <= 500:
            raise Invalid("invalid_task_identity")
        if not integer(data["budget"], 1, 1000) or not integer(data["attempt_limit"], data["budget"], 2000) or not integer(data["ttl"], 1, 86400):
            raise Invalid("invalid_task_limits")
        destinations = data["destinations"]
        if not isinstance(destinations, dict) or not 1 <= len(destinations) <= 10:
            raise Invalid("invalid_destinations")
        for name, labels in destinations.items():
            if not identifier(name) or not isinstance(labels, list) or any(x != "restricted" for x in labels):
                raise Invalid("invalid_clearance")
        if not isinstance(data["artifacts"], list) or len(data["artifacts"]) > 50:
            raise Invalid("invalid_artifacts")
        seen = set()
        for artifact in data["artifacts"]:
            if not isinstance(artifact, dict) or set(artifact) != {"id", "text", "labels"}:
                raise Invalid("invalid_artifact_fields")
            if not identifier(artifact["id"]) or artifact["id"] in seen:
                raise Invalid("duplicate_or_invalid_artifact_id")
            seen.add(artifact["id"])
            if not isinstance(artifact["text"], str) or len(artifact["text"]) > 8000:
                raise Invalid("invalid_text")
            if not isinstance(artifact["labels"], list) or any(x not in ("restricted", "unknown") for x in artifact["labels"]):
                raise Invalid("invalid_labels")
        token = secrets.token_urlsafe(32)
        policy = {k: data[k] for k in ("purpose", "budget", "attempt_limit", "destinations")}
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM tasks WHERE id=?", (data["id"],)).fetchone():
                raise Invalid("task_exists")
            db.execute("INSERT INTO tasks(id,token_hash,policy,expires) VALUES(?,?,?,?)", (data["id"], digest(token), canonical(policy), time.time() + data["ttl"]))
            for artifact in data["artifacts"]:
                db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (data["id"], artifact["id"], artifact["text"], canonical(sorted(set(artifact["labels"])))))
            self.audit(db, {"event": "task_created", "task": data["id"], "policy_hash": digest(policy)})
        return {"task": data["id"], "token": token}

    def authenticate(self, token):
        if not isinstance(token, str) or len(token) > 256:
            return None
        with self.transaction() as db:
            row = db.execute("SELECT id FROM tasks WHERE token_hash=?", (digest(token),)).fetchone()
        return row[0] if row else None

    def stop(self, task):
        with self.transaction() as db:
            if db.execute("UPDATE tasks SET stopped=1 WHERE id=?", (task,)).rowcount != 1:
                raise Invalid("unknown_task")
            db.execute("DELETE FROM grants WHERE task=?", (task,))
            self.audit(db, {"event": "task_stopped", "task": task})
        return {"stopped": True}

    def approve(self, data):
        if not isinstance(data, dict) or set(data) != {"task", "artifact", "destination", "ttl"} or not integer(data["ttl"], 1, 300):
            raise Invalid("invalid_approval")
        if not all(identifier(data[k]) for k in ("task", "artifact", "destination")):
            raise Invalid("invalid_approval_identity")
        with self.transaction() as db:
            task = db.execute("SELECT * FROM tasks WHERE id=?", (data["task"],)).fetchone()
            artifact = db.execute("SELECT * FROM artifacts WHERE task=? AND id=?", (data["task"], data["artifact"])).fetchone()
            if not task or not artifact or task["stopped"] or task["expires"] <= time.time():
                raise Invalid("inactive_task_or_unknown_artifact")
            if data["destination"] not in json.loads(task["policy"])["destinations"]:
                raise Invalid("unknown_destination")
            labels = set(json.loads(artifact["labels"])) | set(json.loads(task["exposure"]))
            if "unknown" in labels:
                raise Invalid("classification_required")
            content_hash = digest(artifact["text"])
            db.execute("INSERT OR REPLACE INTO grants VALUES(?,?,?,?,?,0)", (data["task"], data["artifact"], data["destination"], content_hash, time.time() + data["ttl"]))
            self.audit(db, {"event": "operator_approved", "task": data["task"], "artifact": data["artifact"], "destination": data["destination"], "content_hash": content_hash})
        return {"approved": True, "content_hash": content_hash}

    def step(self, task_id, request):
        # Snapshot before using any caller-owned collections; JSON only.
        try:
            request = json.loads(canonical(request))
        except (TypeError, ValueError, RecursionError):
            request = None
        fingerprint = digest(request)
        with self.transaction() as db:
            task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                raise Invalid("unknown_task")
            policy = json.loads(task["policy"])
            rid = request.get("request_id") if isinstance(request, dict) else None
            valid_rid = identifier(rid)

            def finish(allowed, reason, payload=None, cache=True):
                response = {"allowed": allowed, "reason": reason}
                if payload is not None:
                    response["result"] = payload
                self.audit(db, {"event": "step", "task": task_id, "request_hash": fingerprint, "allowed": allowed, "reason": reason})
                if valid_rid and cache:
                    db.execute("INSERT OR IGNORE INTO receipts VALUES(?,?,?,?)", (task_id, rid, fingerprint, canonical(response)))
                return response

            # Stop and expiry win even over cached successful reads.
            if task["stopped"]:
                return finish(False, "task_stopped", cache=False)
            if task["expires"] <= time.time():
                return finish(False, "task_expired", cache=False)
            if task["attempts"] >= policy["attempt_limit"]:
                return finish(False, "attempt_limit", cache=False)
            db.execute("UPDATE tasks SET attempts=attempts+1 WHERE id=?", (task_id,))
            if valid_rid:
                old = db.execute("SELECT * FROM receipts WHERE task=? AND id=?", (task_id, rid)).fetchone()
                if old:
                    if old["request_hash"] != fingerprint:
                        return finish(False, "request_id_conflict", cache=False)
                    self.audit(db, {"event": "replay", "task": task_id, "request_hash": fingerprint})
                    return json.loads(old["response"])
            if task["used"] >= policy["budget"]:
                return finish(False, "action_budget")
            if not valid_rid or not isinstance(request, dict):
                return finish(False, "invalid_request")
            op = request.get("op")
            fields = {"read": {"request_id", "op", "id"}, "derive": {"request_id", "op", "id", "sources", "text"}, "send": {"request_id", "op", "id", "destination"}}
            if not isinstance(op, str) or op not in fields:
                return finish(False, "unauthorized_operation")
            if set(request) != fields[op] or not identifier(request.get("id")):
                return finish(False, "invalid_request_fields")
            artifact = db.execute("SELECT * FROM artifacts WHERE task=? AND id=?", (task_id, request["id"])).fetchone()
            exposure = set(json.loads(task["exposure"]))
            result = None
            if op in ("read", "send") and not artifact:
                return finish(False, "unknown_artifact")
            if op == "read":
                exposure.update(json.loads(artifact["labels"]))
                result = {"text": artifact["text"], "labels": json.loads(artifact["labels"])}
            elif op == "derive":
                if artifact:
                    return finish(False, "immutable_artifact")
                sources = request["sources"]
                if not isinstance(sources, list) or len(sources) > 50 or not all(identifier(s) for s in sources) or not isinstance(request["text"], str) or len(request["text"]) > 8000:
                    return finish(False, "invalid_derivation")
                for source in sources:
                    item = db.execute("SELECT labels FROM artifacts WHERE task=? AND id=?", (task_id, source)).fetchone()
                    if not item:
                        return finish(False, "unknown_source")
                    exposure.update(json.loads(item[0]))
                db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (task_id, request["id"], request["text"], canonical(sorted(exposure))))
                result = {"id": request["id"], "labels": sorted(exposure)}
            else:
                destination = request["destination"]
                if not isinstance(destination, str) or destination not in policy["destinations"]:
                    return finish(False, "unknown_destination")
                labels = set(json.loads(artifact["labels"])) | exposure
                if "unknown" in labels:
                    return finish(False, "classification_required")
                grant = db.execute("SELECT * FROM grants WHERE task=? AND artifact=? AND destination=?", (task_id, request["id"], destination)).fetchone()
                approved = grant and not grant["used"] and grant["expires"] > time.time() and grant["content_hash"] == digest(artifact["text"])
                if not labels <= set(policy["destinations"][destination]) and not approved:
                    return finish(False, "information_flow_denied")
                delivery = secrets.token_hex(16)
                db.execute("INSERT INTO outbox VALUES(?,?,?,?,?,?)", (delivery, task_id, request["id"], destination, artifact["text"], time.time()))
                if grant:
                    db.execute("UPDATE grants SET used=1 WHERE task=? AND artifact=? AND destination=?", (task_id, request["id"], destination))
                result = {"delivery_id": delivery, "sink": "local_sqlite_outbox"}
            db.execute("UPDATE tasks SET used=used+1, exposure=? WHERE id=?", (canonical(sorted(exposure)), task_id))
            return finish(True, "allowed", result)

    def inspect(self, table):
        if table not in ("audit", "outbox"):
            raise Invalid("invalid_table")
        with self.transaction() as db:
            return [dict(row) for row in db.execute("SELECT * FROM " + table + " ORDER BY rowid")]

    def verify_audit(self):
        previous = "0" * 64
        rows = self.inspect("audit")
        for position, row in enumerate(rows, 1):
            expected = hashlib.sha256((previous + row["event"]).encode()).hexdigest()
            if row["sequence"] != position or row["previous_hash"] != previous or row["hash"] != expected:
                return {"valid": False, "failed_at": row["sequence"]}
            previous = row["hash"]
        return {"valid": True, "entries": len(rows), "head": previous}
