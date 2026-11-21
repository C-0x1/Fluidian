"""A local stand-in for the OpenAI API used by the automated tests.

It validates requests the way the real service does where it matters to the
kernel (authentication, strict Structured Output schemas, parameter dialects)
and returns schema-conforming responses.  Model names select behaviours:

``legacy-*``   only understands ``max_tokens`` and the ``system`` role
``modern-*``   rejects ``max_tokens``; accepts ``developer`` and ``reasoning_effort``
``plain-*``    rejects ``reasoning_effort`` and ``stream_options``
``nojson-*``   rejects ``json_schema`` response formats (JSON mode only)
``flaky-*``    answers 500, then 429, then succeeds
``gone-*``     404 model_not_found
``garbage-*``  first reply violates the schema; the corrected retry is valid
``cut-*``      reply is truncated mid-JSON
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from .. import schema as SCH
from ..reflex import data as D

KEY = "sk-test-fluidian"
_ALLOWED = {"type", "properties", "required", "additionalProperties", "items", "enum", "anyOf", "$ref", "$defs", "description"}


def strict_problems(schema: Any, path: str = "$") -> List[str]:
    """Problems that would make the real API reject a ``strict: true`` schema."""
    out: List[str] = []
    if isinstance(schema, list):
        for i, item in enumerate(schema):
            out += strict_problems(item, "%s[%d]" % (path, i))
        return out
    if not isinstance(schema, dict):
        return out
    for key in schema:
        if key not in _ALLOWED and path.split(".")[-1] not in ("properties", "$defs"):
            out.append("%s: unsupported keyword %r" % (path, key))
    types = schema.get("type")
    if types == "object" or (isinstance(types, list) and "object" in types):
        props = schema.get("properties")
        if not isinstance(props, dict):
            out.append("%s: object without properties" % path)
            props = {}
        if schema.get("additionalProperties") is not False:
            out.append("%s: additionalProperties must be false" % path)
        if sorted(schema.get("required") or []) != sorted(props):
            out.append("%s: every property must be listed in required" % path)
        for name, sub in props.items():
            out += strict_problems(sub, "%s.properties.%s" % (path, name))
    if "items" in schema:
        out += strict_problems(schema["items"], path + ".items")
    for option in schema.get("anyOf") or []:
        out += strict_problems(option, path + ".anyOf")
    for name, sub in (schema.get("$defs") or {}).items():
        out += strict_problems(sub, "%s.$defs.%s" % (path, name))
    return out


class MockOpenAI:
    def __init__(self, models: Optional[List[str]] = None):
        self.models = models or ["gpt-6-luna", "gpt-6.2-sol", "gpt-6.2-astra", "text-embedding-3-small", "omni-moderation-latest",
                                 "gpt-transcribe", "gpt-4o-mini-tts", "gpt-image-2.6-flare"]
        self.requests: List[Dict[str, Any]] = []
        self.counts: Dict[str, int] = {}
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:
                pass

            def _send(self, status: int, payload: Any, headers: Optional[Dict[str, str]] = None, raw: Optional[bytes] = None) -> None:
                body = raw if raw is not None else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json" if raw is None else "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _err(self, status: int, message: str, code: str = "invalid_request_error", param: str = "", headers: Optional[Dict[str, str]] = None) -> None:
                self._send(status, {"error": {"message": message, "type": "invalid_request_error", "param": param or None, "code": code}}, headers)

            def _auth(self) -> bool:
                if self.headers.get("Authorization") != "Bearer " + KEY:
                    self._err(401, "Incorrect API key provided.", "invalid_api_key")
                    return False
                return True

            def do_GET(self) -> None:  # noqa: N802
                if not self._auth():
                    return
                if self.path == "/v1/models":
                    self._send(200, {"object": "list", "data": [{"id": m, "object": "model"} for m in outer.models]})
                else:
                    self._err(404, "Not found", "not_found")

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                if not self._auth():
                    return
                ctype = self.headers.get("Content-Type", "")
                body: Dict[str, Any] = {}
                if ctype.startswith("application/json"):
                    try:
                        body = json.loads(raw.decode("utf-8"))
                    except ValueError:
                        return self._err(400, "Could not parse JSON body.")
                with outer.lock:
                    outer.requests.append({"path": self.path, "body": body, "contentType": ctype, "size": len(raw)})
                if self.path == "/v1/chat/completions":
                    return self._chat(body)
                if self.path == "/v1/embeddings":
                    texts = body.get("input") if isinstance(body.get("input"), list) else [body.get("input")]
                    return self._send(200, {"data": [{"index": i, "embedding": D.embed(str(t), 64)} for i, t in enumerate(texts)],
                                            "usage": {"prompt_tokens": sum(len(str(t)) // 4 for t in texts), "total_tokens": 0}})
                if self.path == "/v1/moderations":
                    flagged = "attack" in str(body.get("input")).lower()
                    return self._send(200, {"results": [{"flagged": flagged, "categories": {"violence": flagged, "hate": False}}]})
                if self.path == "/v1/audio/transcriptions":
                    if not ctype.startswith("multipart/form-data") or b'name="file"' not in raw or b'name="model"' not in raw:
                        return self._err(400, "Expected multipart form with model and file.")
                    return self._send(200, {"text": "um so the invoice is late again"})
                if self.path == "/v1/audio/speech":
                    if not body.get("input") or not body.get("voice"):
                        return self._err(400, "input and voice are required.")
                    return self._send(200, None, raw=b"ID3mock-audio")
                if self.path == "/v1/images/generations":
                    if "n" in body:
                        return self._err(400, "Unsupported parameter: 'n'.", param="n")
                    return self._send(200, {"data": [{"b64_json": base64.b64encode(b"\x89PNG-mock").decode("ascii")}]})
                self._err(404, "Unknown endpoint %s" % self.path, "not_found")

            def _chat(self, body: Dict[str, Any]) -> None:
                model = str(body.get("model") or "")
                with outer.lock:
                    outer.counts[model] = n = outer.counts.get(model, 0) + 1
                messages = body.get("messages")
                if not model or not isinstance(messages, list) or not messages:
                    return self._err(400, "model and messages are required.")
                if model not in outer.models and not model.split("-")[0] in ("legacy", "modern", "plain", "nojson", "flaky", "garbage", "cut"):
                    return self._err(404, "The model `%s` does not exist or you do not have access to it." % model, "model_not_found")
                if model.startswith("gone-"):
                    return self._err(404, "The model `%s` does not exist." % model, "model_not_found")
                for banned in ("n", "seed", "temperature", "functions"):
                    if banned in body:
                        return self._err(400, "Unsupported parameter: '%s'." % banned, param=banned)
                roles = {m.get("role") for m in messages}
                if model.startswith("legacy-"):
                    if "max_completion_tokens" in body:
                        return self._err(400, "Unrecognized request argument supplied: max_completion_tokens", param="max_completion_tokens")
                    if "developer" in roles:
                        return self._err(400, "Invalid value: 'developer'. Supported values are: 'system', 'assistant', 'user'.", param="messages[0].role")
                if model.startswith("modern-") and "max_tokens" in body:
                    return self._err(400, "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.", param="max_tokens")
                if model.startswith(("plain-", "legacy-")):
                    if "reasoning_effort" in body:
                        return self._err(400, "Unrecognized request argument supplied: reasoning_effort", param="reasoning_effort")
                if model.startswith("plain-") and "stream_options" in body:
                    return self._err(400, "Unrecognized request argument supplied: stream_options", param="stream_options")
                if model.startswith("flaky-") and n <= 2:
                    return self._err(500, "The server had an error.", "server_error") if n == 1 else \
                        self._err(429, "Rate limit reached.", "rate_limit_exceeded", headers={"Retry-After": "0"})
                fmt = body.get("response_format") or {}
                schema = None
                if fmt.get("type") == "json_schema":
                    if model.startswith("nojson-"):
                        return self._err(400, "Invalid parameter: 'response_format' of type 'json_schema' is not supported with this model.", param="response_format")
                    spec = fmt.get("json_schema") or {}
                    if not isinstance(spec.get("name"), str) or not spec.get("strict") or not isinstance(spec.get("schema"), dict):
                        return self._err(400, "json_schema requires name, strict and schema.", param="response_format")
                    problems = strict_problems(spec["schema"])
                    if problems:
                        return self._err(400, "Invalid schema for response_format: " + problems[0], param="response_format")
                    schema = spec["schema"]
                elif fmt.get("type") == "json_object":
                    hint = next((m["content"] for m in reversed(messages) if isinstance(m.get("content"), str) and "JSON Schema" in m["content"]), "")
                    try:
                        schema = json.loads(hint[hint.index("{"):])
                    except ValueError:
                        schema = None
                user = next((m for m in messages if m.get("role") == "user"), {})
                content = user.get("content")
                text = content if isinstance(content, str) else next((p.get("text", "") for p in content or [] if p.get("type") == "text"), "")
                try:
                    request = json.loads(text)
                except ValueError:
                    request = {}
                hint = next((str(v) for v in (request.get("input") or {}).values() if isinstance(v, str)), "")
                hint = hint.replace("<<<UNTRUSTED\n", "").replace("\nUNTRUSTED>>>", "")
                if schema is not None:
                    answer = json.dumps(SCH.synthesize(schema, seed=model + hint, hint=hint), ensure_ascii=False)
                else:
                    answer = "Mock reply to: %s" % hint[:80]
                finish = "stop"
                corrected = any("did not match the schema" in str(m.get("content")) for m in messages)
                if model.startswith("garbage-") and not corrected:
                    answer = json.dumps({"unexpected": True})
                if model.startswith("cut-"):
                    answer, finish = answer[: max(2, len(answer) * 2 // 3)], "length"
                usage = {"prompt_tokens": max(1, len(json.dumps(messages)) // 4), "completion_tokens": max(1, len(answer) // 4),
                         "total_tokens": 0, "completion_tokens_details": {"reasoning_tokens": 0}}
                if body.get("stream"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    step = max(8, len(answer) // 6)
                    for start in range(0, len(answer), step):
                        chunk = {"object": "chat.completion.chunk", "model": model, "choices": [{"index": 0, "delta": {"content": answer[start:start + step]}, "finish_reason": None}]}
                        self.wfile.write(("data: %s\n\n" % json.dumps(chunk)).encode("utf-8"))
                        self.wfile.flush()
                    self.wfile.write(("data: %s\n\n" % json.dumps({"model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})).encode())
                    if "stream_options" in body:
                        self.wfile.write(("data: %s\n\n" % json.dumps({"model": model, "choices": [], "usage": usage})).encode())
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self._send(200, {"id": "chatcmpl-mock", "object": "chat.completion", "model": model,
                                 "choices": [{"index": 0, "message": {"role": "assistant", "content": answer, "refusal": None}, "finish_reason": finish}],
                                 "usage": usage})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.base_url = "http://127.0.0.1:%d/v1" % self.port
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="mock-openai", daemon=True)

    def start(self) -> "MockOpenAI":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def chat_requests(self, model: Optional[str] = None) -> List[Dict[str, Any]]:
        return [r["body"] for r in self.requests if r["path"] == "/v1/chat/completions" and (model is None or r["body"].get("model") == model)]
