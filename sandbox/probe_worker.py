"""Deterministic adversarial test worker. This is NOT an AI model integration."""
import json
import os
from pathlib import Path
import socket
import sys
import time

job = json.load(sys.stdin)
mode = job["purpose"]
if mode == "sleep":
    time.sleep(120)
elif mode == "forge":
    print(json.dumps({"text": "fake", "op": "approve", "task": "other"}))
    raise SystemExit(0)
elif mode == "probe":
    readonly = False
    try:
        Path("/escape-test").write_text("probe")
    except OSError:
        readonly = True
    blocked = False
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=1):
            pass
    except OSError:
        blocked = True
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    text = json.dumps({"uid": os.getuid(), "root_readonly": readonly,
                       "network_blocked": blocked, "docker_socket": Path("/var/run/docker.sock").exists(),
                       "host_environment_visible": "TAHU_OPERATOR_SENTINEL" in os.environ,
                       "host_file_visible": Path(job.get("host_file", "/nonexistent-tahu-host-file")).exists(),
                       "capabilities": status["CapEff"].strip(), "no_new_privs": status["NoNewPrivs"].strip(),
                       "seccomp": status["Seccomp"].strip()})
elif mode == "memory":
    marker = Path("/tmp/previous-task")
    text = json.dumps({"previous_file": marker.exists(), "documents": job["documents"]})
    marker.write_text("SYNTHETIC SECRET")
else:
    text = "2 + 2 = 4"
print(json.dumps({"text": text}))
