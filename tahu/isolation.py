"""Trusted, offline, one-shot worker broker; never execute this inside an agent.

Only reviewed, secret-free Linux images by immutable image ID are accepted.
Workers receive data on stdin and return one text proposal, never capabilities.
Docker and its host/kernel are trusted. This is not a kernel-escape defense.
"""
import json
import re
import shutil
import subprocess
import threading
import time
import uuid

from .core import Invalid, canonical, identifier
from .server import strict_json


class IsolationError(RuntimeError):
    pass


def _bounded_process(command, payload, timeout, active=lambda: True, limit=65536):
    """Bound both pipes and wall time, including a worker that never reads stdin."""
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=False)
    overflow = threading.Event()
    output = bytearray()

    def read(stream, keep):
        count = 0
        while True:
            block = stream.read(1024)
            if not block:
                break
            count += len(block)
            if count > limit:
                overflow.set()
                process.kill()
                break
            if keep:
                output.extend(block)

    def write():
        try:
            process.stdin.write(payload)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    readers = [threading.Thread(target=read, args=(process.stdout, True), daemon=True),
               threading.Thread(target=read, args=(process.stderr, False), daemon=True)]
    writer = threading.Thread(target=write, daemon=True)
    for thread in readers + [writer]:
        thread.start()
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            if overflow.is_set():
                raise IsolationError("worker_output_limit")
            if not active():
                raise IsolationError("task_inactive")
            if time.monotonic() >= deadline:
                raise IsolationError("worker_timeout")
            time.sleep(0.05)
        for thread in readers + [writer]:
            thread.join(timeout=1)
        if any(thread.is_alive() for thread in readers + [writer]):
            raise IsolationError("worker_pipe_not_closed")
        if overflow.is_set():
            raise IsolationError("worker_output_limit")
        if process.returncode != 0:
            # Worker stderr may contain secrets. Do not surface it in host logs.
            raise IsolationError("worker_failed")
        if not active():
            raise IsolationError("task_inactive")
        return bytes(output)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        for thread in readers + [writer]:
            thread.join(timeout=1)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


class DockerWorker:
    def __init__(self, image, timeout=20):
        if not isinstance(image, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise Invalid("immutable_local_image_id_required")
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise Invalid("invalid_worker_timeout")
        self.image = image
        self.timeout = timeout
        self.docker = shutil.which("docker")
        if not self.docker:
            raise IsolationError("docker_required_no_host_fallback")

    def _metadata(self, args):
        try:
            return strict_json(_bounded_process([self.docker] + args, b"", 10))
        except (ValueError, OSError) as exc:
            raise IsolationError("docker_metadata_unavailable") from exc

    def preflight(self):
        info = self._metadata(["info", "--format", "{{json .}}"])
        if info.get("OSType") != "linux" or not any("seccomp" in option for option in info.get("SecurityOptions", [])):
            raise IsolationError("linux_engine_with_seccomp_required")
        image = self._metadata(["image", "inspect", self.image])[0]
        if image.get("Os") != "linux" or image.get("Config", {}).get("Volumes"):
            raise IsolationError("linux_image_without_declared_volumes_required")

    def command(self, name):
        return [self.docker, "run", "--rm", "--interactive", "--pull=never", "--name", name,
                "--network=none", "--ipc=none", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true", "--user=65534:65534",
                "--pids-limit=32", "--memory=128m", "--memory-swap=128m", "--cpus=0.5",
                "--ulimit=nofile=64:64", "--ulimit=core=0:0", "--log-driver=none",
                "--no-healthcheck", "--workdir=/tmp",
                "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777", self.image]

    def run(self, job, active=lambda: True):
        raw = canonical(job).encode()
        if len(raw) > 65536:
            raise Invalid("worker_input_limit")
        self.preflight()
        if not active():
            raise IsolationError("task_inactive")
        name = "tahu-" + uuid.uuid4().hex
        try:
            response = _bounded_process(self.command(name), raw, self.timeout, active)
            try:
                proposal = strict_json(response)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise IsolationError("invalid_worker_json") from exc
            if (not isinstance(proposal, dict) or set(proposal) != {"text"}
                    or not isinstance(proposal["text"], str) or len(proposal["text"]) > 8000):
                raise IsolationError("text_proposal_required")
            return proposal["text"]
        finally:
            # Killing the docker client does not necessarily stop the container.
            # Explicit removal is mandatory; failure is surfaced, never ignored.
            cleanup = subprocess.run([self.docker, "rm", "--force", name],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if cleanup.returncode:
                check = subprocess.run([self.docker, "ps", "-aq", "--filter", "name=^/" + name + "$"],
                                       capture_output=True, timeout=10)
                if check.returncode or check.stdout.strip():
                    raise IsolationError("worker_cleanup_unconfirmed")


def execute_isolated(gateway, task, sources, output_id, destination, worker):
    """Operator-only Python API. Worker never chooses a task, tool or destination.

    Reads account for exposure before data leaves the gateway. Text stays in the
    artifact registry; callers receive only policy decisions and delivery IDs.
    Each call supplies only this task's selected inputs, with no shared history.
    """
    if (not identifier(task) or not identifier(output_id) or not identifier(destination)
            or not isinstance(sources, list) or len(sources) > 50
            or not all(identifier(item) for item in sources) or len(set(sources)) != len(sources)):
        raise Invalid("invalid_execution")

    def active():
        with gateway.transaction() as db:
            state = db.execute("SELECT stopped,expires FROM tasks WHERE id=?", (task,)).fetchone()
            return bool(state and not state["stopped"] and state["expires"] > time.time())

    with gateway.transaction() as db:
        row = db.execute("SELECT policy FROM tasks WHERE id=?", (task,)).fetchone()
        if not row:
            raise Invalid("unknown_task")
        policy = json.loads(row[0])
        if destination not in policy["destinations"]:
            raise Invalid("unknown_destination")
    run_id = uuid.uuid4().hex
    documents = []
    for index, source in enumerate(sources):
        response = gateway.step(task, {"request_id": run_id + "r" + str(index), "op": "read", "id": source})
        if not response["allowed"]:
            return response
        documents.append(dict(id=source, **response["result"]))
    if not active():
        raise IsolationError("task_inactive")
    job = {"purpose": policy["purpose"], "documents": documents}
    text = worker.run(job, active=active)
    derived = gateway.step(task, {"request_id": run_id + "d", "op": "derive", "id": output_id,
                                  "sources": sources, "text": text})
    if not derived["allowed"]:
        return derived
    return gateway.step(task, {"request_id": run_id + "s", "op": "send", "id": output_id,
                               "destination": destination})
