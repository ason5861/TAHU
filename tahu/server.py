"""Loopback-only development HTTP transport. Use a hardened TLS proxy for deployment."""
import argparse
import hmac
import json
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import Gateway, Invalid, identifier


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Invalid("duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise Invalid("non_finite_number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def make_server(gateway, operator_token, port=8765):
    if not isinstance(operator_token, str) or len(operator_token) < 32:
        raise Invalid("operator_token_must_have_at_least_32_characters")

    class Handler(BaseHTTPRequestHandler):
        server_version = "TAHU/0.3"

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            # Never print authorization headers or user-supplied paths/bodies.
            pass

        def reply(self, status, data):
            body = json.dumps(data, ensure_ascii=True, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, {"service": "TAHU", "version": "0.3.0", "sink": "local_sqlite_outbox"})
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self):
            try:
                self.handle_post()
            except (Invalid, ValueError, TypeError, UnicodeError, RecursionError):
                self.reply(400, {"error": "invalid_request"})
            except sqlite3.Error:
                self.reply(503, {"error": "storage_unavailable"})
            except (TimeoutError, ConnectionError):
                self.close_connection = True

        def handle_post(self):
            if self.headers.get("Origin") is not None:
                return self.reply(403, {"error": "browser_origin_not_allowed"})
            if self.headers.get("Transfer-Encoding") is not None or len(self.headers.get_all("Content-Length", [])) != 1:
                return self.reply(400, {"error": "content_length_required"})
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self.reply(415, {"error": "json_required"})
            length = int(self.headers["Content-Length"])
            if not 0 < length <= 65536:
                return self.reply(413, {"error": "body_size_limit"})
            headers = self.headers.get_all("Authorization", [])
            if len(headers) != 1 or not headers[0].startswith("Bearer "):
                return self.reply(401, {"error": "authentication_required"})
            token = headers[0][7:]
            if len(token) > 256 or not token.isascii():
                return self.reply(401, {"error": "invalid_credentials"})
            operator = hmac.compare_digest(token, operator_token)
            task = None if operator else gateway.authenticate(token)
            if not operator and not task:
                return self.reply(401, {"error": "invalid_credentials"})
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise Invalid("incomplete_body")
            body = strict_json(raw)
            if self.path == "/v1/step":
                if operator:
                    return self.reply(403, {"error": "task_token_required"})
                return self.reply(200, gateway.step(task, body))
            if not operator:
                return self.reply(403, {"error": "operator_required"})
            if self.path == "/v1/tasks":
                return self.reply(201, gateway.create_task(body))
            if self.path == "/v1/approve":
                return self.reply(200, gateway.approve(body))
            if self.path == "/v1/stop":
                if not isinstance(body, dict) or set(body) != {"task"} or not identifier(body["task"]):
                    raise Invalid("invalid_stop")
                return self.reply(200, gateway.stop(body["task"]))
            if self.path in ("/v1/audit", "/v1/outbox", "/v1/audit/verify"):
                if body != {}:
                    raise Invalid("empty_body_required")
                if self.path == "/v1/audit/verify":
                    return self.reply(200, gateway.verify_audit())
                return self.reply(200, {"items": gateway.inspect(self.path.rsplit("/", 1)[1])})
            return self.reply(404, {"error": "not_found"})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description="TAHU local authorization gateway")
    parser.add_argument("command", choices=("init", "serve"))
    parser.add_argument("--state", default=".tahu")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    state = Path(args.state).resolve()
    config = state / "operator.json"
    if args.command == "init":
        state.mkdir(parents=True, exist_ok=True)
        # Exclusive creation: never rotate or overwrite an existing credential.
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"token": secrets.token_urlsafe(48)}, handle)
        Gateway(state / "state.sqlite3")
        print("Initialized local state. Operator credential saved in operator.json; do not publish it.")
        return
    credential = json.loads(config.read_text(encoding="utf-8"))["token"]
    gateway = Gateway(state / "state.sqlite3")
    server = make_server(gateway, credential, args.port)
    print(f"TAHU listening on http://127.0.0.1:{server.server_port}; local outbox only", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
