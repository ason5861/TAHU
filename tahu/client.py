"""Provider-neutral client; keep operator credentials out of the model process."""
import json
from urllib.request import Request, urlopen


class Client:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def call(self, path, payload):
        request = Request(self.base_url + path, data=json.dumps(payload).encode(), headers={
            "Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def step(self, request):
        return self.call("/v1/step", request)
