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
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


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
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    response = json.loads(raw)
                except json.JSONDecodeError:
                    response = {}
                error = response.get("error") if isinstance(response, dict) else None
                error = error if isinstance(error, dict) else {}
                details = {
                    "http_status": exc.code,
                    "endpoint": url,
                    "method": "POST",
                    "payload": {key: value for key, value in fields.items()
                                if key != "access_token"},
                    "message": str(error.get("message") or "Meta returned no JSON error message"),
                    "type": error.get("type"),
                    "code": error.get("code"),
                    "subcode": error.get("error_subcode"),
                    "fbtrace_id": error.get("fbtrace_id"),
                }
                if exc.code in {401, 403}:
                    raise PostingError("INVALID_TOKEN", f"Meta authentication failed with HTTP {exc.code}",
                                       details) from exc
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < self.retries:
                        time.sleep(.25 * (attempt + 1))
                        continue
                    raise PostingError("NETWORK_TIMEOUT", f"Temporary Meta HTTP failure: {exc.code}",
                                       details) from exc
                summary = (f"Meta HTTP {exc.code}: {details['message']} "
                           f"(type={details['type']}, code={details['code']}, "
                           f"subcode={details['subcode']})")
                raise PostingError("META_API_ERROR", summary, details) from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt < self.retries:
                    time.sleep(.25 * (attempt + 1))
                    continue
                raise PostingError("NETWORK_TIMEOUT", "Meta network request failed or timed out") from exc
            except json.JSONDecodeError as exc:
                raise PostingError("MALFORMED_API_RESPONSE", "Meta response was not valid JSON") from exc
        raise PostingError("NETWORK_TIMEOUT", "Meta request retry limit reached")

    def get(self, url: str, fields: dict) -> dict:
        safe_fields = {key: value for key, value in fields.items() if key != "access_token"}
        request_url = f"{url}?{urllib.parse.urlencode(fields, doseq=True)}"
        try:
            request = urllib.request.Request(request_url, method="GET")
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error = json.loads(raw).get("error", {})
            except json.JSONDecodeError:
                error = {}
            details = {"http_status": exc.code, "endpoint": url, "method": "GET",
                       "payload": safe_fields,
                       "message": error.get("message") or "Meta returned no JSON error message",
                       "type": error.get("type"), "code": error.get("code"),
                       "subcode": error.get("error_subcode"),
                       "fbtrace_id": error.get("fbtrace_id")}
            raise PostingError("CONTAINER_STATUS_FAILURE",
                               f"Meta container status HTTP {exc.code}: {details['message']}",
                               details) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise PostingError("NETWORK_TIMEOUT", "Meta container status request failed") from exc
        except json.JSONDecodeError as exc:
            raise PostingError("MALFORMED_API_RESPONSE",
                               "Meta container status response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise PostingError("MALFORMED_API_RESPONSE",
                               "Meta container status response must be a JSON object")
        return payload


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
            raise PostingError(failure_code, str(exc), exc.details) from exc
        except Exception as exc:
            raise PostingError(failure_code, "Meta transport failed") from exc
        remote_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(remote_id, str) or not remote_id:
            raise PostingError("MALFORMED_API_RESPONSE", "Meta response did not contain an id")
        return remote_id

    def create_text_container(self, text: str) -> str:
        fields = {"media_type": "TEXT", "text": text}
        return self._post("me/threads", fields, "CONTAINER_CREATION_FAILURE")

    def create_text_reply(self, text: str, reply_to_id: str) -> str:
        """Create a reply media container and return its creation ID."""
        if not reply_to_id:
            raise PostingError("THREADS_REPLY_FAILURE", "reply_to_id is required")
        return self._post("me/threads", {
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": reply_to_id,
        }, "THREADS_REPLY_FAILURE")

    def create_image_container(self, text: str, image_url: str,
                               reply_to_id: str | None = None) -> str:
        fields = {"media_type": "IMAGE", "text": text, "image_url": image_url}
        if reply_to_id:
            fields["reply_to_id"] = reply_to_id
        return self._post("me/threads", fields,
                          "CONTAINER_CREATION_FAILURE")

    def publish(self, creation_id: str) -> str:
        self.wait_until_ready(creation_id)
        return self._post("me/threads_publish", {"creation_id": creation_id},
                          "PUBLISH_FAILURE")

    def container_status(self, creation_id: str) -> str:
        getter = getattr(self.transport, "get", None)
        if getter is None:
            return "FINISHED"
        payload = getter(f"{self.base_url}/{creation_id}", {
            "fields": "id,status", "access_token": self.secrets.access_token,
        })
        if payload.get("id") != creation_id:
            raise PostingError("MALFORMED_API_RESPONSE",
                               "Container status response ID did not match creation_id")
        status = payload.get("status")
        if status not in {"IN_PROGRESS", "FINISHED", "PUBLISHED", "ERROR", "EXPIRED"}:
            raise PostingError("MALFORMED_API_RESPONSE",
                               f"Unknown Meta container status: {status}")
        return status

    def wait_until_ready(self, creation_id: str, attempts: int = 30,
                         interval: float = 1.0) -> str:
        """Wait for Meta to expose a container as publishable before publishing."""
        for attempt in range(attempts):
            status = self.container_status(creation_id)
            if status in {"FINISHED", "PUBLISHED"}:
                return status
            if status in {"ERROR", "EXPIRED"}:
                raise PostingError("CONTAINER_STATUS_FAILURE",
                                   f"Meta container is not publishable: {status}")
            if status != "IN_PROGRESS":
                raise PostingError("MALFORMED_API_RESPONSE",
                                   f"Unknown Meta container status: {status}")
            if attempt + 1 < attempts:
                time.sleep(interval)
        raise PostingError("CONTAINER_STATUS_FAILURE",
                           "Meta container did not become FINISHED before timeout")
