"""Minimal Chrome DevTools Protocol driver (standard library only).

Used by the browser tests and the screenshot tool.  It launches a headless
Chrome/Chromium, speaks CDP over a hand-rolled WebSocket client, and offers
just what the suite needs: navigate, evaluate, wait and capture.
"""
from __future__ import annotations

import atexit
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from typing import Any, Dict, Optional

from ..procs import LaunchRecord, browser_endpoint, stop_process

BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "microsoft-edge")


def find_browser() -> Optional[str]:
    override = os.environ.get("FLUIDIAN_BROWSER")
    if override and (os.path.isfile(override) or shutil.which(override)):
        return override
    for name in BROWSERS:
        hit = shutil.which(name)
        if hit:
            return hit
    return None


class _WebSocket:
    def __init__(self, host: str, port: int, path: str):
        self.sock = socket.create_connection((host, port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        self.sock.sendall(("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key)).encode("ascii"))
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("websocket upgrade refused: %r" % head[:80])
        self.buffer = head.split(b"\r\n\r\n", 1)[1]

    def send(self, text: str) -> None:
        data = text.encode("utf-8")
        mask = os.urandom(4)
        head = bytearray([0x81])
        if len(data) < 126:
            head.append(0x80 | len(data))
        elif len(data) < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", len(data))
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", len(data))
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(head) + mask + masked)

    def _read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:n], self.buffer[n:]
        return out

    def recv(self) -> str:
        message = b""
        while True:
            b1, b2 = self._read(2)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(length)
            opcode = b1 & 0x0F
            if opcode == 0x8:
                raise ConnectionError("websocket closed by peer")
            if opcode in (0x9, 0xA):
                continue
            message += payload
            if b1 & 0x80:
                return message.decode("utf-8", "replace")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def quit_browser_on_port(port: int, timeout: float = 3.0) -> None:
    """Ask the browser whose DevTools endpoint listens on ``port`` to exit. Raises when nothing answers there."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:%d/json/version" % port, timeout=timeout) as res:
        url = json.loads(res.read())["webSocketDebuggerUrl"]
    ws = _WebSocket("127.0.0.1", port, "/" + url.split("/", 3)[3])
    try:
        ws.send(json.dumps({"id": 1, "method": "Browser.close", "params": {}}))
        time.sleep(0.2)   # let the message leave before the socket closes
    finally:
        ws.close()


class Browser:
    def __init__(self, width: int = 1440, height: int = 900, scale: float = 1.0):
        binary = find_browser()
        if not binary:
            raise RuntimeError("no Chrome or Chromium binary found (set FLUIDIAN_BROWSER)")
        self.ws: Optional[_WebSocket] = None
        self._id = 0
        self._closed = False
        self.profile = tempfile.mkdtemp(prefix="fluidian-chrome-")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        args = [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking", "--force-color-profile=srgb", "--remote-debugging-port=%d" % self.port,
                "--user-data-dir=" + self.profile, "--window-size=%d,%d" % (width, height), "--no-proxy-server", "about:blank"]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            args.insert(1, "--no-sandbox")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(self.close)   # an interrupted run must not leave a browser behind
        # ...and if this process is killed outright, the record lets the next run find the browser and close it
        self.record = LaunchRecord(self.proc.pid, self.port, self.profile)
        deadline = time.time() + 20
        target = None
        while time.time() < deadline and target is None:
            try:
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:%d/json" % self.port, timeout=2) as res:
                    pages = [t for t in json.loads(res.read()) if t.get("type") == "page"]
                    target = pages[0] if pages else None
            except (OSError, ValueError):
                time.sleep(0.15)
        if target is None:
            self.close()
            raise RuntimeError("Chrome did not expose a debugging target")
        self.record.update(endpoint=browser_endpoint(self.port, timeout=3.0) or "")
        url = target["webSocketDebuggerUrl"]
        self.ws = _WebSocket("127.0.0.1", self.port, "/" + url.split("/", 3)[3])
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.viewport(width, height, scale)

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert self.ws is not None
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError("%s failed: %s" % (method, msg["error"].get("message")))
                return msg.get("result", {})

    def viewport(self, width: int, height: int, scale: float = 1.0) -> None:
        self.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": False})

    def navigate(self, url: str) -> None:
        self.call("Page.navigate", {"url": url})

    def eval(self, expression: str) -> Any:
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        if result.get("exceptionDetails"):
            raise RuntimeError("script error: %s" % result["exceptionDetails"].get("text"))
        return result.get("result", {}).get("value")

    def wait_for(self, expression: str, timeout: float = 15.0, poll: float = 0.1) -> Any:
        deadline = time.time() + timeout
        last: Any = None
        while time.time() < deadline:
            try:
                last = self.eval(expression)
            except RuntimeError:
                last = None
            if last:
                return last
            time.sleep(poll)
        raise TimeoutError("condition not met within %.0fs: %s" % (timeout, expression[:90]))

    def screenshot(self, path: str, full_page: bool = False) -> None:
        params: Dict[str, Any] = {"format": "png", "captureBeyondViewport": bool(full_page)}
        if full_page:
            size = self.eval("JSON.stringify([document.documentElement.scrollWidth, document.documentElement.scrollHeight])")
            width, height = json.loads(size)
            params["clip"] = {"x": 0, "y": 0, "width": width, "height": min(height, 6000), "scale": 1}
        data = self.call("Page.captureScreenshot", params)["data"]
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(data))

    def _quit_from_page(self) -> None:
        """Ask the browser to exit through the page connection that is already open."""
        if self.ws is None:
            raise ConnectionError("no page connection")
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": "Browser.close", "params": {}}))

    def _quit_from_browser(self) -> None:
        """Ask the browser to exit through its own endpoint, for when the page connection is missing or stuck."""
        quit_browser_on_port(self.port)

    def close(self) -> None:
        """Shut the browser down. Safe to call more than once, and it never raises.

        The browser is first asked to exit over the DevTools protocol, which
        works even where the system refuses to deliver a signal to it (a
        sandboxed build such as the snap-packaged Chromium may not accept
        signals from the shell that launched it). Signals are the fallback.
        """
        if getattr(self, "_closed", True):
            return
        self._closed = True
        try:
            atexit.unregister(self.close)
        except Exception:
            pass
        proc = getattr(self, "proc", None)
        self.exit_status = stop_process(proc, timeout=6.0, polite=[self._quit_from_page, self._quit_from_browser])
        if self.ws:
            self.ws.close()
            self.ws = None
        shutil.rmtree(self.profile, ignore_errors=True)
        record = getattr(self, "record", None)
        if record is not None:
            known = record.data.get("endpoint")
            if self.exit_status is None and known and browser_endpoint(self.port) == known:
                record.release()   # it could not be stopped: leave the note so that the next run closes it
            else:
                record.remove()

    def __enter__(self) -> "Browser":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
