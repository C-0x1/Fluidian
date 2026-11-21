"""OpenAI API client (standard library only).

Covers the endpoints the kernel needs — chat completions with Structured
Outputs and streaming, embeddings, moderation, transcription, speech and
image generation — plus the resilience a UI framework requires:

* **Adaptive parameter negotiation.**  Model families disagree on request
  parameters (``max_tokens`` vs ``max_completion_tokens``, ``system`` vs
  ``developer`` instructions, ``reasoning_effort``, ``response_format``).  When
  the API rejects a parameter the client rewrites the request, retries, and
  remembers the adjustment per model.
* **Bounded retries** with exponential backoff and ``Retry-After`` support.
* Works with any OpenAI-compatible endpoint through ``OPENAI_BASE_URL``.
"""
from __future__ import annotations

import json
import random
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

from . import __version__
from .config import Config


class ProviderError(Exception):
    def __init__(self, message: str, status: int = 0, code: str = "", param: str = "", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code or ""
        self.param = param or ""
        self.retryable = retryable

    def __str__(self) -> str:
        bits = [self.message]
        if self.status:
            bits.append("(HTTP %d%s)" % (self.status, ", " + self.code if self.code else ""))
        return " ".join(bits)


def _usage(raw: Optional[Dict[str, Any]]) -> Dict[str, int]:
    raw = raw or {}
    details = raw.get("completion_tokens_details") or {}
    cached = (raw.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return {"in": int(raw.get("prompt_tokens") or raw.get("input_tokens") or 0),
            "out": int(raw.get("completion_tokens") or raw.get("output_tokens") or 0),
            "reasoning": int(details.get("reasoning_tokens") or 0), "cached": int(cached or 0)}


class OpenAIClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.quirks: Dict[str, set] = {}
        self._lock = threading.Lock()
        host = urlparse(cfg.base_url).hostname or ""
        self.first_party = host.endswith("openai.com")

    # ------------------------------------------------------------------ http
    def _headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        headers = {"Authorization": "Bearer " + self.cfg.api_key, "User-Agent": "fluidian/" + __version__,
                   "Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if self.cfg.organization:
            headers["OpenAI-Organization"] = self.cfg.organization
        if self.cfg.project:
            headers["OpenAI-Project"] = self.cfg.project
        return headers

    def _open(self, method: str, path: str, body: Optional[bytes], headers: Dict[str, str], timeout: float):
        request = urllib.request.Request(self.cfg.base_url + path, data=body, headers=headers, method=method)
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            message, code, param = raw[:300] or exc.reason, "", ""
            try:
                err = json.loads(raw).get("error") or {}
                if isinstance(err, dict):
                    message = str(err.get("message") or message)
                    code = str(err.get("code") or err.get("type") or "")
                    param = str(err.get("param") or "")
                elif isinstance(err, str):
                    message = err
            except ValueError:
                pass
            retryable = exc.code in (408, 409, 425, 429, 500, 502, 503, 504) and code != "insufficient_quota"
            error = ProviderError(message, exc.code, code, param, retryable)
            error.retry_after = exc.headers.get("Retry-After") if exc.headers else None  # type: ignore[attr-defined]
            raise error
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ProviderError("network error: %s" % reason, 0, "network", "", True)

    def _request(self, method: str, path: str, payload: Any = None, *, raw_body: Optional[bytes] = None,
                 content_type: Optional[str] = "application/json", timeout: Optional[float] = None,
                 stream: bool = False):
        body = raw_body if raw_body is not None else (json.dumps(payload).encode("utf-8") if payload is not None else None)
        attempts = max(0, self.cfg.max_retries) + 1
        deadline = time.time() + (timeout or self.cfg.request_timeout) * 1.5
        last: Optional[ProviderError] = None
        for attempt in range(attempts):
            try:
                return self._open(method, path, body, self._headers(content_type), timeout or self.cfg.request_timeout)
            except ProviderError as exc:
                last = exc
                if not exc.retryable or attempt == attempts - 1:
                    raise
                delay = min(8.0, 0.4 * (2 ** attempt)) + random.uniform(0, 0.25)
                retry_after = getattr(exc, "retry_after", None)
                if retry_after:
                    try:
                        delay = min(10.0, max(delay, float(retry_after)))
                    except ValueError:
                        pass
                if time.time() + delay > deadline:
                    raise
                time.sleep(delay)
        raise last or ProviderError("request failed")

    def _json(self, method: str, path: str, payload: Any = None, **kw: Any) -> Dict[str, Any]:
        with self._request(method, path, payload, **kw) as response:
            raw = response.read().decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except ValueError:
            raise ProviderError("provider returned a non-JSON response: %s" % raw[:120])

    # ---------------------------------------------------------------- models
    def list_models(self) -> List[str]:
        data = self._json("GET", "/models", timeout=min(15.0, self.cfg.request_timeout))
        return sorted(str(m.get("id")) for m in data.get("data", []) if isinstance(m, dict) and m.get("id"))

    # ------------------------------------------------------------------ chat
    def _role(self, model: str) -> str:
        q = self.quirks.get(model, set())
        if "role:system" in q:
            return "system"
        if "role:developer" in q:
            return "developer"
        if self.cfg.instruction_role in ("system", "developer"):
            return self.cfg.instruction_role
        return "developer" if self.first_party else "system"

    def _reasoning_capable(self, model: str) -> bool:
        m = model.lower()
        return self.first_party and (m.startswith(("gpt-5", "gpt-6", "gpt-7", "o1", "o3", "o4")) and "chat" not in m)

    def _chat_body(self, model: str, messages: List[Dict[str, Any]], schema: Optional[Dict[str, Any]],
                   schema_name: str, max_tokens: int, stream: bool) -> Dict[str, Any]:
        q = self.quirks.setdefault(model, set())
        role = self._role(model)
        msgs = []
        for m in messages:
            entry = dict(m)
            if entry.get("role") == "system":
                entry["role"] = role
            msgs.append(entry)
        body: Dict[str, Any] = {"model": model, "messages": msgs}
        reasoning = bool(self.cfg.reasoning_effort) and "no_reasoning" not in q and self._reasoning_capable(model)
        if reasoning:
            body["reasoning_effort"] = self.cfg.reasoning_effort
        if max_tokens and "no_max" not in q:
            budget = max_tokens + (2400 if reasoning else 0) + (max_tokens if "grow" in q else 0)
            body["max_tokens" if "max_tokens" in q else "max_completion_tokens"] = budget
        if schema is not None:
            if "json_object" in q:
                body["response_format"] = {"type": "json_object"}
                hint = "Respond with a single JSON object that validates against this JSON Schema:\n" + json.dumps(schema)
                body["messages"] = msgs + [{"role": role, "content": hint}]
            else:
                body["response_format"] = {"type": "json_schema",
                                           "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
        if stream:
            body["stream"] = True
            if "no_stream_options" not in q:
                body["stream_options"] = {"include_usage": True}
        return body

    def _heal(self, model: str, body: Dict[str, Any], err: ProviderError) -> bool:
        """Adjust per-model quirks after a 400; returns True when a retry is worthwhile."""
        if err.status not in (400, 404, 422):
            return False
        q = self.quirks.setdefault(model, set())
        text = (err.param + " " + err.message).lower()
        param = err.param.lower()

        def learn(flag: str) -> bool:
            if flag in q:
                return False
            q.add(flag)
            return True

        if "max_completion_tokens" in text and "max_completion_tokens" in body:
            return learn("no_max") if "legacy_rejected" in q else learn("max_tokens")
        if "max_tokens" in text and "max_tokens" in body:
            q.discard("max_tokens")
            q.add("legacy_rejected")
            return learn("no_max")
        if "reasoning_effort" in text or "reasoning.effort" in text:
            return learn("no_reasoning")
        if "stream_options" in text:
            return learn("no_stream_options")
        if "response_format" in text or "json_schema" in text or "structured output" in text:
            return learn("json_object")
        if "developer" in text and self._role(model) == "developer":
            q.discard("role:developer")
            return learn("role:system")
        if ("'system'" in text or "system message" in text or "role" in param) and self._role(model) == "system":
            q.discard("role:system")
            return learn("role:developer")
        return False

    def chat(self, model: str, messages: List[Dict[str, Any]], *, schema: Optional[Dict[str, Any]] = None,
             schema_name: str = "result", max_tokens: int = 900, timeout: Optional[float] = None,
             on_delta: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Run a chat completion.  With ``on_delta`` the response is streamed.

        Returns ``{"text", "usage", "model", "finish", "refusal"}``.
        """
        last: Optional[ProviderError] = None
        for _ in range(6):
            body = self._chat_body(model, messages, schema, schema_name, max_tokens, on_delta is not None)
            try:
                if on_delta is not None:
                    result = self._chat_stream(body, on_delta, timeout)
                else:
                    data = self._json("POST", "/chat/completions", body, timeout=timeout)
                    choice = (data.get("choices") or [{}])[0]
                    message = choice.get("message") or {}
                    content = message.get("content")
                    if isinstance(content, list):
                        content = "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
                    result = {"text": content or "", "usage": _usage(data.get("usage")), "model": data.get("model") or model,
                              "finish": choice.get("finish_reason") or "", "refusal": message.get("refusal") or ""}
            except ProviderError as exc:
                last = exc
                if self._heal(model, body, exc):
                    continue
                raise
            if result["finish"] == "length" and not result["text"].strip() and "grow" not in self.quirks.setdefault(model, set()):
                # reasoning consumed the whole budget: grow it once and retry
                self.quirks[model].add("grow")
                continue
            return result
        raise last or ProviderError("could not negotiate request parameters for %s" % model)

    def _chat_stream(self, body: Dict[str, Any], on_delta: Callable[[str], None], timeout: Optional[float]) -> Dict[str, Any]:
        text: List[str] = []
        usage: Dict[str, int] = _usage(None)
        finish, refusal, model = "", "", body["model"]
        with self._request("POST", "/chat/completions", body, timeout=timeout, stream=True) as response:
            for raw in response:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if chunk.get("error"):
                    err = chunk["error"]
                    raise ProviderError(str(err.get("message", "stream error")), 0, str(err.get("code", "")))
                model = chunk.get("model") or model
                if chunk.get("usage"):
                    usage = _usage(chunk["usage"])
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        text.append(piece)
                        on_delta(piece)
                    if delta.get("refusal"):
                        refusal += str(delta["refusal"])
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
        return {"text": "".join(text), "usage": usage, "model": model, "finish": finish, "refusal": refusal}

    # ------------------------------------------------------------ embeddings
    def embeddings(self, model: str, texts: List[str]) -> Tuple[List[List[float]], Dict[str, int]]:
        data = self._json("POST", "/embeddings", {"model": model, "input": texts})
        rows = sorted(data.get("data") or [], key=lambda r: r.get("index", 0))
        return [r.get("embedding") or [] for r in rows], _usage(data.get("usage"))

    # ------------------------------------------------------------ moderation
    def moderate(self, model: str, text: str) -> Dict[str, Any]:
        data = self._json("POST", "/moderations", {"model": model, "input": text})
        result = (data.get("results") or [{}])[0]
        categories = [k for k, v in (result.get("categories") or {}).items() if v]
        return {"flagged": bool(result.get("flagged")), "categories": categories}

    # ----------------------------------------------------------------- audio
    def transcribe(self, model: str, audio: bytes, filename: str = "audio.webm", mime: str = "audio/webm",
                   language: str = "") -> str:
        boundary = "fluidian-" + uuid.uuid4().hex
        parts: List[bytes] = []

        def field(name: str, value: str) -> None:
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode("utf-8"))

        field("model", model)
        if language:
            field("language", language)
        safe_name = "".join(ch for ch in filename if ch.isalnum() or ch in "._-") or "audio.webm"
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                      % (boundary, safe_name, mime)).encode("utf-8"))
        parts.append(audio)
        parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
        data = self._json("POST", "/audio/transcriptions", raw_body=b"".join(parts),
                          content_type="multipart/form-data; boundary=" + boundary)
        return str(data.get("text") or "")

    def speech(self, model: str, text: str, voice: str = "alloy", fmt: str = "mp3") -> bytes:
        payload = {"model": model, "input": text[:4000], "voice": voice, "response_format": fmt}
        with self._request("POST", "/audio/speech", payload) as response:
            return response.read()

    # ---------------------------------------------------------------- images
    def image(self, model: str, prompt: str, size: str = "1024x1024") -> Dict[str, str]:
        data = self._json("POST", "/images/generations", {"model": model, "prompt": prompt[:3000], "size": size},
                          timeout=max(90.0, self.cfg.request_timeout))
        item = (data.get("data") or [{}])[0]
        if item.get("b64_json"):
            return {"url": "data:image/png;base64," + item["b64_json"]}
        return {"url": str(item.get("url") or "")}


def iter_sse(lines: Iterator[bytes]) -> Iterator[Dict[str, Any]]:
    """Parse a server-sent event stream into JSON payloads (used by tests and tools)."""
    for raw in lines:
        line = raw.decode("utf-8", "replace").strip()
        if line.startswith("data:") and line[5:].strip() != "[DONE]":
            try:
                yield json.loads(line[5:].strip())
            except ValueError:
                continue
