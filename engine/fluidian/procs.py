"""Stopping child processes without letting clean-up fail.

Ending a process is usually a matter of sending it a signal, but a signal can
be refused. A browser installed as a sandboxed package (the snap-packaged
Chromium on Ubuntu, for one) runs under a security profile that may not accept
signals from the shell that started it, and ``kill`` then fails with
"Permission denied". A process can also exit between the check and the signal.

Neither is a reason for a test run, a screenshot run or an engine shutdown to
fail, so everything in Fluidian that stops a child goes through
:func:`stop_process`: ask politely first when the child has a way to be asked,
fall back to signals, and never raise.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

Polite = Union[Callable[[], Any], Iterable[Callable[[], Any]], None]


def _wait(proc: Any, timeout: float) -> Optional[int]:
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    except (OSError, ValueError):   # already reaped, or its handles are gone
        return proc.poll()


def stop_process(proc: Any, timeout: float = 5.0, polite: Polite = None) -> Optional[int]:
    """Stop a child process; return its exit status, or ``None`` if it is still running.

    ``polite`` is one callable, or several, that ask the process to exit by
    itself, for example by sending a shutdown message over its own protocol.
    Each is tried in order and given ``timeout`` seconds. If the process is
    still alive it is sent SIGTERM and then SIGKILL. A request that fails and a
    signal that is refused are skipped, so this function does not raise.
    """
    if proc is None:
        return None
    try:
        if proc.poll() is not None:
            return proc.returncode
    except (OSError, ValueError):
        return None
    asks = [polite] if callable(polite) else list(polite or [])
    for ask in asks:
        try:
            ask()
        except Exception:  # a process that cannot be asked is simply signalled instead
            continue
        code = _wait(proc, timeout)
        if code is not None:
            return code
    for send in (proc.terminate, proc.kill):
        try:
            send()
        except OSError:   # PermissionError: the signal was refused; ProcessLookupError: the process has just gone
            continue
        code = _wait(proc, timeout)
        if code is not None:
            return code
    try:
        return proc.poll()
    except (OSError, ValueError):
        return None


def free_ports(count: int = 1) -> List[int]:
    """``count`` TCP ports on 127.0.0.1 that nothing is listening on right now."""
    sockets = []
    try:
        for _ in range(count):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def start_server(argv: List[str], port: int, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None, timeout: float = 30.0) -> subprocess.Popen:
    """Start a Fluidian server for a test or tool and wait until it answers on ``port``.

    The server is tied to this process by a lifeline (``FLUIDIAN_LIFELINE=stdin``):
    it exits by itself when this process ends for any reason, so nothing is left
    listening after an interrupted run. Raises ``RuntimeError`` when the port is
    taken, when the server exits during start-up, or when it does not answer in
    time. An answer from some other process on the same port is never accepted:
    the server must return the token it was started with.
    """
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError("port %d is already in use (%s); is another server still running there?" % (port, exc.strerror or exc))
    token = secrets.token_hex(8)
    merged = dict(os.environ if env is None else env, FLUIDIAN_LIFELINE="stdin", FLUIDIAN_INSTANCE=token)
    log = tempfile.TemporaryFile()   # a file, not a pipe: a server that prints a lot must never block on us
    proc = subprocess.Popen(argv, cwd=cwd, env=merged, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
    proc.fluidian_log = log   # type: ignore[attr-defined]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            log.seek(0)
            said = [line.strip() for line in log.read().decode("utf-8", "replace").splitlines() if line.strip()]
            reason = next((line for line in said if "Could not listen" in line or "Error" in line or "error" in line), said[-1] if said else "")
            _close_pipes(proc)
            raise RuntimeError("the server on port %d exited during start-up (status %s)%s" % (
                port, proc.returncode, ": " + _plain(reason) if reason else "; is the port already in use?"))
        try:
            with opener.open("http://127.0.0.1:%d/healthz" % port, timeout=1) as res:
                if res.status == 200 and json.loads(res.read()).get("instance") == token:
                    return proc   # the answer came from the process started here, not from some other server
        except (OSError, ValueError, AttributeError):
            pass
        time.sleep(0.15)
    stop_server(proc)
    raise RuntimeError("the server on port %d did not answer within %.0f seconds" % (port, timeout))


def _plain(text: str) -> str:
    """``text`` without terminal colour codes."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _close_pipes(proc: Any) -> None:
    for stream in (getattr(proc, "stdin", None), getattr(proc, "stdout", None), getattr(proc, "stderr", None), getattr(proc, "fluidian_log", None)):
        try:
            if stream:
                stream.close()
        except OSError:
            pass


def stop_server(proc: Any, timeout: float = 8.0) -> Optional[int]:
    """Stop a server started with :func:`start_server`: drop its lifeline, then fall back to signals."""
    def drop_lifeline() -> None:
        if proc.stdin is None or proc.stdin.closed:
            raise OSError("no lifeline")
        proc.stdin.close()

    code = stop_process(proc, timeout=timeout, polite=drop_lifeline)
    _close_pipes(proc)
    return code


# --- a written record of every browser the harness starts ---------------------------
# Recognising an abandoned browser by looking at the process table is not dependable:
# a packaged browser may be started through wrappers (so the process id handed back is
# not the browser's), may run with a private /tmp (so its profile path is not the one
# asked for), and what its command line and ancestry look like differs between systems.
# So the harness writes down what it starts. Each record is a small file that the
# launching process keeps locked for as long as it lives; the lock is released by the
# operating system when that process ends, however it ends. A record whose lock can be
# taken therefore belongs to a launcher that is gone, and if the browser it names still
# answers on its debugging port with the same endpoint id, that browser was abandoned.
PROFILE_PREFIX = "fluidian-chrome-"
RECORD_PREFIX = "browser-"


def state_dir() -> Optional[str]:
    """The folder that holds launch records, created on first use; ``None`` when there is nowhere safe to keep them."""
    base = os.environ.get("FLUIDIAN_STATE_DIR")
    if not base:
        owner = str(os.getuid()) if hasattr(os, "getuid") else re.sub(r"\W+", "_", os.environ.get("USERNAME", "user"))
        base = os.path.join(tempfile.gettempdir(), "fluidian-run-" + owner)
    try:
        os.makedirs(base, mode=0o700, exist_ok=True)
        info = os.lstat(base)
        if not os.path.isdir(base) or os.path.islink(base) or (hasattr(os, "getuid") and info.st_uid != os.getuid()):
            return None   # someone else's folder: do not trust what is in it, and do not write there
    except OSError:
        return None
    return base


def _try_lock(fh: Any) -> bool:
    """Take the exclusive lock on an open record without waiting. False when another holder has it."""
    try:
        import fcntl
    except ImportError:
        try:
            import msvcrt
            fh.seek(1 << 30)   # a byte far past the content, so the content itself stays readable
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)   # type: ignore[attr-defined]
            return True
        except (ImportError, OSError):
            return False
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


class LaunchRecord:
    """The note a launcher keeps about one browser it started. Creating, updating and removing it never raise."""

    def __init__(self, pid: int, port: int, profile: str):
        self.path: Optional[str] = None
        self._fh: Any = None
        self.data: Dict[str, Any] = {"kind": "browser", "pid": int(pid), "port": int(port), "profile": profile,
                                     "endpoint": "", "launcher": os.getpid(), "started": int(time.time())}
        folder = state_dir()
        if not folder:
            return
        try:
            path = os.path.join(folder, "%s%d-%s.json" % (RECORD_PREFIX, port, secrets.token_hex(4)))
            fh = open(path, "w+", encoding="utf-8")
            if not _try_lock(fh):
                fh.close()
                os.unlink(path)
                return
            self.path, self._fh = path, fh
            self._write()
        except OSError:
            self.path = self._fh = None

    def _write(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(json.dumps(self.data))
            self._fh.flush()
        except (OSError, ValueError):
            pass

    def update(self, **fields: Any) -> None:
        self.data.update(fields)
        self._write()

    def release(self) -> None:
        """Stop holding the record but leave it in place, for a browser that could not be stopped: the next run will try."""
        fh, self._fh = self._fh, None
        try:
            if fh is not None:
                fh.close()
        except OSError:
            pass

    def remove(self) -> None:
        fh, path, self._fh, self.path = self._fh, self.path, None, None
        try:
            if fh is not None:
                fh.close()
        except OSError:
            pass
        try:
            if path:
                os.unlink(path)
        except OSError:
            pass


def browser_endpoint(port: int, timeout: float = 1.0) -> Optional[str]:
    """The id of the browser answering on a DevTools port (the path of its endpoint), or ``None`` when no browser answers."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:%d/json/version" % int(port), timeout=timeout) as res:
            url = json.loads(res.read()).get("webSocketDebuggerUrl") or ""
        return "/" + url.split("/", 3)[3] if url.count("/") >= 3 else None
    except Exception:
        return None


def _forget(path: Optional[str], profile: Optional[str]) -> None:
    """Delete a record and the temporary profile it names. Only a folder this harness created is ever removed."""
    try:
        if path:
            os.unlink(path)
    except OSError:
        pass
    if profile and os.path.basename(profile.rstrip("/\\")).startswith(PROFILE_PREFIX) and os.path.isdir(profile) and not os.path.islink(profile):
        import shutil
        shutil.rmtree(profile, ignore_errors=True)


def _recorded() -> "tuple[List[Dict[str, Any]], set]":
    """Read the launch records: (browsers whose launcher is gone but which still answer, ports whose launcher is alive).

    Records that no longer describe anything running are deleted on the way.
    """
    abandoned: List[Dict[str, Any]] = []
    live: set = set()
    folder = state_dir()
    if not folder:
        return abandoned, live
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return abandoned, live
    for name in names:
        if not (name.startswith(RECORD_PREFIX) and name.endswith(".json")):
            continue
        path = os.path.join(folder, name)
        try:
            fh = open(path, "r+", encoding="utf-8")
        except OSError:
            continue
        with fh:
            try:
                fh.seek(0)
                data = json.loads(fh.read() or "{}")
                port = int(data.get("port") or 0)
            except (OSError, ValueError, TypeError, AttributeError):
                data, port = {}, 0
            if not _try_lock(fh):   # its launcher is running: this browser is in use
                if port:
                    live.add(port)
                continue
            answering = browser_endpoint(port) if port else None
            known = data.get("endpoint") or ""
            if answering is None or (known and answering != known):
                _forget(path, data.get("profile"))   # the browser has gone; so does the note about it
                continue
            if not known and not _profile_in_process_table(data.get("profile")):
                continue   # the launcher died before it learnt the browser's id, and nothing else confirms it
            abandoned.append({"pid": int(data.get("pid") or 0), "kind": "browser", "port": port, "profile": data.get("profile") or "",
                              "endpoint": known or answering, "record": path})
    return abandoned, live


def _profile_in_process_table(profile: Optional[str]) -> bool:
    if not profile or not os.path.isdir("/proc"):
        return False
    wanted = "--user-data-dir=" + profile
    for name in os.listdir("/proc"):
        if name.isdigit() and wanted in _cmdline(int(name)):
            return True
    return False


# --- processes left behind by an earlier run --------------------------------------
# Only Linux exposes what is needed (/proc); elsewhere nothing is reported and nothing is touched.
LEGACY_PORTS = {"8793", "8794", "8795", "8796", "8797"}   # fixed ports used by the harness up to 1.1.0


def _cmdline(pid: int) -> List[str]:
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as fh:
            return [part.decode("utf-8", "replace") for part in fh.read().split(b"\0") if part]
    except OSError:
        return []


def _parent(pid: int) -> int:
    try:
        with open("/proc/%d/stat" % pid, "rb") as fh:
            return int(fh.read().rsplit(b")", 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        return 0


def _launcher_alive(pid: int) -> bool:
    """True when some ancestor of ``pid`` is a running Python process, which is what every harness is."""
    seen = set()
    pid = _parent(pid)
    while pid > 1 and pid not in seen:
        seen.add(pid)
        argv = _cmdline(pid)
        if argv and "python" in os.path.basename(argv[0]).lower():
            return True
        pid = _parent(pid)
    return False


def leftovers() -> List[Dict[str, Any]]:
    """Processes that an earlier, interrupted test or screenshot run left behind.

    Three things are recognised, and only when the process that launched them is gone:

    * a headless browser the harness wrote a launch record for (see :class:`LaunchRecord`): its
      launcher no longer holds the record, and the browser still answers on its debugging port
      with the id that was written down. This does not depend on what the process table shows;
    * a headless browser started by the harness of version 1.1.1 or earlier, which kept no
      records, known by the ``fluidian-chrome-`` profile folder on its command line (Linux only);
    * a gallery or showcase server started by the harness of version 1.1.0 or earlier, known by
      its exact command line (the fixed test ports and ``--offline``). Later versions tie their
      servers to the harness with a lifeline, so those cannot be left behind.

    A browser or server that someone started on purpose never matches.
    """
    found, live = _recorded()
    taken = {entry["port"] for entry in found} | live
    if not os.path.isdir("/proc"):
        return found
    me = os.getpid()
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == me:
            continue
        pid = int(name)
        argv = _cmdline(pid)
        if len(argv) < 2:
            continue
        profile = next((a for a in argv if a.startswith("--user-data-dir=") and os.path.basename(a.split("=", 1)[1].rstrip("/")).startswith(PROFILE_PREFIX)), None)
        if profile and not any(a.startswith("--type=") for a in argv):
            port = next((a.split("=", 1)[1] for a in argv if a.startswith("--remote-debugging-port=")), "")
            number = int(port) if port.isdigit() else 0
            if number in taken:   # already accounted for by a launch record, as abandoned or as in use
                continue
            if not _launcher_alive(pid):
                found.append({"pid": pid, "kind": "browser", "port": number, "profile": profile.split("=", 1)[1]})
            continue
        if ("python" in os.path.basename(argv[0]).lower() and len(argv) == 6 and os.path.basename(argv[1]) == "fluidian"
                and argv[2] in ("gallery", "showcase") and argv[3] == "--port" and argv[4] in LEGACY_PORTS and argv[5] == "--offline"
                and not _launcher_alive(pid)):
            found.append({"pid": pid, "kind": "server", "port": int(argv[4])})
    return found


def _gone(pid: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while True:
        try:
            with open("/proc/%d/stat" % pid, "rb") as fh:
                if fh.read().rsplit(b")", 1)[1].split()[0] == b"Z":   # finished, waiting to be reaped
                    return True
        except (OSError, IndexError):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.1)


def _entry_gone(entry: Dict[str, Any], timeout: float) -> bool:
    """Whether a leftover has stopped. A recorded browser is judged by its debugging port, which is certain;
    anything else by its process id."""
    endpoint, port = entry.get("endpoint"), entry.get("port")
    if not (endpoint and port):
        return _gone(int(entry["pid"]), timeout)
    deadline = time.time() + timeout
    while True:
        if browser_endpoint(int(port), timeout=0.5) != endpoint:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.1)


def remove_leftover(entry: Dict[str, Any], timeout: float = 6.0) -> bool:
    """Stop one process reported by :func:`leftovers`. Returns whether it is gone. Never raises."""
    import signal
    pid = int(entry.get("pid") or 0)

    def done() -> bool:
        if entry.get("record") or entry.get("endpoint"):
            _forget(entry.get("record"), entry.get("profile"))
        return True

    if entry.get("endpoint") and _entry_gone(entry, 0):
        return done()   # it went by itself between being found and now
    if entry.get("kind") == "browser" and entry.get("port"):
        try:   # a sandboxed browser may refuse signals, but it can always be asked over its own port
            from .testkit.cdp import quit_browser_on_port
            quit_browser_on_port(int(entry["port"]))
            if _entry_gone(entry, timeout):
                return done()
        except Exception:
            if entry.get("endpoint") and _entry_gone(entry, 0.5):
                return done()   # nothing answers there any more: that is why it could not be asked
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if pid <= 1:
            break
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            if _entry_gone(entry, 0.5):
                return done()
            break
        except OSError:
            continue
        if _entry_gone(entry, timeout):
            return done()
    return done() if _entry_gone(entry, 0.2) else False


def describe(pid: int = 0, port: int = 0) -> str:
    """What the clean-up code can see about one browser, as text for a failure message or a bug report."""
    lines = ["platform: %s, python %s" % (sys.platform, sys.version.split()[0])]
    folder = state_dir()
    lines.append("record folder: %s" % (folder or "(none usable)"))
    try:
        for name in sorted(os.listdir(folder)) if folder else []:
            with open(os.path.join(folder, name), "r+", encoding="utf-8") as fh:
                text = fh.read()
                lines.append("  %s  launcher %s  %s" % (name, "gone" if _try_lock(fh) else "alive", text))
    except OSError as exc:
        lines.append("  (could not read: %s)" % exc)
    if port:
        lines.append("port %d answers as: %s" % (port, browser_endpoint(port)))
    seen = set()
    while pid > 1 and pid not in seen and os.path.isdir("/proc"):
        seen.add(pid)
        lines.append("process %d: %s" % (pid, " ".join(_cmdline(pid))[:400] or "(no command line readable)"))
        pid = _parent(pid)
    return "\n".join(lines)


def sweep(report: Any = None) -> int:
    """Remove everything :func:`leftovers` finds; returns how many processes were stopped.

    ``report`` is a stream (``sys.stderr`` by default) that gets one line when something was removed.
    """
    removed = sum(1 for entry in leftovers() if remove_leftover(entry))
    if removed:
        stream = sys.stderr if report is None else report
        try:
            stream.write("Removed %d process%s left behind by an earlier, interrupted run.\n" % (removed, "" if removed == 1 else "es"))
            stream.flush()
        except (OSError, ValueError, AttributeError):
            pass
    return removed
