from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


class PostingError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ThreadsSecrets:
    access_token: str
    user_id: str

    @classmethod
    def from_env(cls) -> "ThreadsSecrets":
        names = ("THREADS_ACCESS_TOKEN", "THREADS_USER_ID")
        values = {name: os.environ.get(name, "").strip() for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise PostingError("MISSING_SECRET", f"Missing environment variables: {', '.join(missing)}")
        return cls(values[names[0]], values[names[1]])


class HttpTransport:
    def __init__(self, timeout: float = 20, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    def __call__(self, url: str, fields: dict) -> dict:
        body = urllib.parse.urlencode(fields, doseq=True).encode()
        for attempt in range(self.retries + 1):
            try:
                request = urllib.request.Request(url, data=body, method="POST")
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise PostingError("MALFORMED_API_RESPONSE", "Meta response must be a JSON object")
                return payload
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403}:
                    raise PostingError("INVALID_TOKEN", f"Meta authentication failed with HTTP {exc.code}") from exc
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < self.retries:
                        time.sleep(.25 * (attempt + 1))
                        continue
                    raise PostingError("NETWORK_TIMEOUT", f"Temporary Meta HTTP failure: {exc.code}") from exc
                raise PostingError("META_API_ERROR", f"Meta HTTP failure: {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt < self.retries:
                    time.sleep(.25 * (attempt + 1))
                    continue
                raise PostingError("NETWORK_TIMEOUT", "Meta network request failed or timed out") from exc
            except json.JSONDecodeError as exc:
                raise PostingError("MALFORMED_API_RESPONSE", "Meta response was not valid JSON") from exc
        raise PostingError("NETWORK_TIMEOUT", "Meta request retry limit reached")


class ThreadsMetaClient:
    def __init__(self, secrets: ThreadsSecrets, transport=None):
        self.secrets = secrets
        self.transport = transport or HttpTransport()
        self.base_url = "https://graph.threads.net"

    def _post(self, path: str, fields: dict, failure_code: str) -> str:
        try:
            payload = self.transport(f"{self.base_url}/{path.lstrip('/')}",
                                     dict(fields, access_token=self.secrets.access_token))
        except PostingError as exc:
            if exc.code in {"MISSING_SECRET", "INVALID_TOKEN", "NETWORK_TIMEOUT", "MALFORMED_API_RESPONSE"}:
                raise
            raise PostingError(failure_code, str(exc)) from exc
        except Exception as exc:
            raise PostingError(failure_code, "Meta transport failed") from exc
        remote_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(remote_id, str) or not remote_id:
            raise PostingError("MALFORMED_API_RESPONSE", "Meta response did not contain an id")
        return remote_id

    def create_text_container(self, text: str, reply_to_id: str | None = None) -> str:
        fields = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            fields["reply_to_id"] = reply_to_id
        return self._post(f"{self.secrets.user_id}/threads", fields, "CONTAINER_CREATION_FAILURE")

    def create_image_container(self, text: str, image_url: str,
                               reply_to_id: str | None = None) -> str:
        fields = {"media_type": "IMAGE", "text": text, "image_url": image_url}
        if reply_to_id:
            fields["reply_to_id"] = reply_to_id
        return self._post(f"{self.secrets.user_id}/threads", fields,
                          "CONTAINER_CREATION_FAILURE")

    def publish(self, creation_id: str) -> str:
        return self._post(f"{self.secrets.user_id}/threads_publish", {"creation_id": creation_id},
                          "PUBLISH_FAILURE")
