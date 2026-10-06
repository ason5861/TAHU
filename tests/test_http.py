import http.client
import json
import secrets
import tempfile
import threading
import unittest
from pathlib import Path

from tahu.core import Gateway
from tahu.server import make_server
from tests.test_gateway import policy


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.g = Gateway(Path(self.temp.name) / "state.sqlite3")
        self.operator = secrets.token_urlsafe(48)
        self.task = self.g.create_task(policy())["token"]
        self.server = make_server(self.g, self.operator, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, path, body, token=None, raw=False, extra=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        headers.update(extra or {})
        connection.request("POST", path, body=body if raw else json.dumps(body), headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_requires_authentication(self):
        self.assertEqual(self.post("/v1/step", {})[0], 401)
        self.assertEqual(self.post("/v1/step", {}, "invalid")[0], 401)

    def test_task_cannot_administer(self):
        for path in ("/v1/tasks", "/v1/approve", "/v1/stop", "/v1/audit", "/v1/outbox"):
            self.assertEqual(self.post(path, {}, self.task)[0], 403)

    def test_operator_cannot_accidentally_act_as_agent(self):
        self.assertEqual(self.post("/v1/step", {}, self.operator)[0], 403)

    def test_scope_cannot_be_supplied_by_agent(self):
        _, result = self.post("/v1/step", {"request_id": "a", "op": "read", "id": "public", "task": "other"}, self.task)
        self.assertFalse(result["allowed"])

    def test_browser_origin_rejected(self):
        self.assertEqual(self.post("/v1/tasks", {}, self.operator, extra={"Origin": "https://untrusted.example"})[0], 403)

    def test_strict_json(self):
        for body in ('{"op":"read","op":"send"}', '{"number":NaN}', '{'):
            self.assertEqual(self.post("/v1/step", body, self.task, raw=True)[0], 400)

    def test_oversized_body(self):
        # Reject the declared size before reading a body. Sending an unread
        # oversized body can correctly produce a TCP reset on Windows.
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.putrequest("POST", "/v1/step")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "65537")
        connection.putheader("Authorization", "Bearer " + self.task)
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        connection.close()

    def test_end_to_end_approval_and_stop(self):
        data = {"request_id": "1", "op": "send", "id": "private", "destination": "public"}
        self.assertFalse(self.post("/v1/step", data, self.task)[1]["allowed"])
        status, _ = self.post("/v1/approve", {"task": "research", "artifact": "private", "destination": "public", "ttl": 60}, self.operator)
        self.assertEqual(status, 200)
        data["request_id"] = "2"
        self.assertTrue(self.post("/v1/step", data, self.task)[1]["allowed"])
        self.assertEqual(self.post("/v1/stop", {"task": "research"}, self.operator)[0], 200)
        data["request_id"] = "3"
        self.assertEqual(self.post("/v1/step", data, self.task)[1]["reason"], "task_stopped")
        self.assertTrue(self.post("/v1/audit/verify", {}, self.operator)[1]["valid"])
