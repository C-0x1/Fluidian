"""Stopping child processes: clean-up must never fail a run, even when a signal is refused."""
import io
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import support
from fluidian import procs
from fluidian.procs import free_ports, leftovers, remove_leftover, start_server, stop_process, stop_server
from fluidian.testkit import cdp

FLUIDIAN = os.path.join(support.ROOT, "fluidian")

SLEEPER = "import time; time.sleep(120)"
LISTENER = "import sys; sys.stdin.readline(); sys.exit(7)"
STUBBORN = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(120)"


class FakeProcess:
    """A process the system will not let us signal, as happens with a sandboxed browser."""

    def __init__(self, exits_when_asked=False):
        self.calls = []
        self.returncode = None
        self.exits_when_asked = exits_when_asked
        self.asked = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.calls.append("wait")
        if self.asked and self.exits_when_asked:
            self.returncode = 0
            return 0
        raise subprocess.TimeoutExpired("fake", timeout)

    def terminate(self):
        self.calls.append("terminate")
        raise PermissionError(13, "Permission denied")

    def kill(self):
        self.calls.append("kill")
        raise PermissionError(13, "Permission denied")


class StopProcessTest(unittest.TestCase):
    def spawn(self, code, **kwargs):
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        self.addCleanup(lambda: (proc.poll() is None and proc.kill(), proc.wait(), [s.close() for s in (proc.stdin, proc.stdout) if s]))
        return proc

    def test_a_running_process_is_stopped(self):
        proc = self.spawn(SLEEPER)
        code = stop_process(proc, timeout=5.0)
        self.assertIsNotNone(code)
        self.assertIsNotNone(proc.poll())

    def test_an_exited_process_reports_its_status(self):
        proc = self.spawn("raise SystemExit(3)")
        proc.wait(timeout=10)
        self.assertEqual(stop_process(proc), 3)
        self.assertIsNone(stop_process(None))

    def test_the_polite_request_is_tried_before_any_signal(self):
        proc = self.spawn(LISTENER, stdin=subprocess.PIPE)
        signals = []
        real_terminate, real_kill = proc.terminate, proc.kill
        proc.terminate = lambda: (signals.append("terminate"), real_terminate())
        proc.kill = lambda: (signals.append("kill"), real_kill())
        code = stop_process(proc, timeout=10.0, polite=lambda: (proc.stdin.write(b"quit\n"), proc.stdin.flush()))
        self.assertEqual((code, signals), (7, []), "the process left by itself, with its own exit status")

    def test_a_refused_signal_is_not_an_error(self):
        proc = FakeProcess()
        self.assertIsNone(stop_process(proc, timeout=0.01))
        self.assertEqual(proc.calls, ["terminate", "kill"], "both signals were tried, both were refused, nothing was raised")

    def test_a_process_that_cannot_be_signalled_can_still_be_asked(self):
        proc = FakeProcess(exits_when_asked=True)
        asks = []

        def first():
            asks.append("first")
            raise ConnectionError("that channel is closed")

        def second():
            asks.append("second")
            proc.asked = True

        self.assertEqual(stop_process(proc, timeout=0.01, polite=[first, second]), 0)
        self.assertEqual(asks, ["first", "second"], "a request that fails moves on to the next one")
        self.assertNotIn("terminate", proc.calls)
        self.assertNotIn("kill", proc.calls)

    def test_a_process_that_ignores_sigterm_is_killed(self):
        proc = self.spawn(STUBBORN.replace("print('ready', flush=True); ", ""))
        time.sleep(0.5)   # let it install its handler
        code = stop_process(proc, timeout=1.0)
        self.assertIsNotNone(code)
        self.assertIsNotNone(proc.poll())

    def test_a_process_that_vanished_is_not_an_error(self):
        proc = FakeProcess()
        proc.terminate = lambda: (_ for _ in ()).throw(ProcessLookupError(3, "No such process"))
        proc.kill = lambda: (_ for _ in ()).throw(ProcessLookupError(3, "No such process"))
        self.assertIsNone(stop_process(proc, timeout=0.01))


class RecordingSocket:
    def __init__(self, fail=False):
        self.sent, self.closed, self.fail = [], False, fail

    def send(self, text):
        if self.fail:
            raise ConnectionError("websocket closed")
        self.sent.append(text)

    def close(self):
        self.closed = True


class BrowserCloseTest(unittest.TestCase):
    """`Browser.close` without launching a browser: the object is assembled by hand around a process that refuses signals."""

    def browser(self, proc, ws):
        browser = cdp.Browser.__new__(cdp.Browser)
        browser.proc, browser.ws, browser._id, browser._closed, browser.port = proc, ws, 41, False, 9
        browser.profile = tempfile.mkdtemp(prefix="fluidian-chrome-test-")
        return browser

    def test_close_asks_the_browser_to_quit_and_never_raises(self):
        proc, ws = FakeProcess(exits_when_asked=True), RecordingSocket()
        original_send = ws.send
        ws.send = lambda text: (original_send(text), setattr(proc, "asked", True))
        browser = self.browser(proc, ws)
        profile = browser.profile
        browser.close()
        self.assertEqual(len(ws.sent), 1)
        self.assertIn('"method": "Browser.close"', ws.sent[0])
        self.assertEqual(browser.exit_status, 0)
        self.assertNotIn("terminate", proc.calls, "no signal is sent to a browser that quits when asked")
        self.assertTrue(ws.closed)
        self.assertFalse(os.path.exists(profile))
        browser.close()
        self.assertEqual(len(ws.sent), 1, "closing twice does nothing the second time")

    def test_close_survives_a_browser_that_can_neither_be_asked_nor_signalled(self):
        proc = FakeProcess()
        browser = self.browser(proc, RecordingSocket(fail=True))
        real_wait = proc.wait
        proc.wait = lambda timeout=None: real_wait(0.01)
        started = time.time()
        browser.close()   # the page channel is dead, nothing listens on the port, and both signals are refused
        self.assertIsNone(browser.exit_status)
        self.assertEqual([c for c in proc.calls if c != "wait"], ["terminate", "kill"])
        self.assertLess(time.time() - started, 15)
        self.assertFalse(os.path.exists(browser.profile))

    def test_a_half_built_browser_can_be_closed(self):
        browser = cdp.Browser.__new__(cdp.Browser)
        browser.close()   # nothing was started, so there is nothing to do and nothing to fail


def alive(pid):
    try:
        with open("/proc/%d/stat" % pid, "rb") as fh:
            return fh.read().rsplit(b")", 1)[1].split()[0] != b"Z"
    except (OSError, IndexError):
        return False


def wait_until(condition, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return condition()


class ServerLifelineTest(unittest.TestCase):
    """A server started by a harness never outlives it, and a stale server is never mistaken for a fresh one."""

    def gallery(self, port):
        return [sys.executable, FLUIDIAN, "gallery", "--port", str(port), "--offline"]

    def test_free_ports_are_distinct_and_usable(self):
        ports = free_ports(3)
        self.assertEqual(len(set(ports)), 3)
        self.assertTrue(all(1024 < p < 65536 for p in ports))

    def test_a_server_stops_when_its_lifeline_closes(self):
        port = free_ports(1)[0]
        proc = start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"))
        try:
            self.assertEqual(support.http("GET", "http://127.0.0.1:%d/healthz" % port)[0], 200)
            proc.stdin.close()
            self.assertEqual(proc.wait(timeout=15), 0, "it shuts down cleanly, without being signalled")
        finally:
            stop_server(proc)
        again = start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"))   # the port is free again
        self.assertIsNotNone(stop_server(again))
        self.assertIsNotNone(again.poll())

    def test_a_server_started_normally_does_not_watch_its_input(self):
        port = free_ports(1)[0]
        env = {k: v for k, v in os.environ.items() if k != "FLUIDIAN_LIFELINE"}
        proc = subprocess.Popen(self.gallery(port), env=dict(env, FLUIDIAN_OFFLINE="1"), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            self.assertTrue(wait_until(lambda: self.answers(port)))
            time.sleep(1.0)
            self.assertIsNone(proc.poll(), "`./fluidian gallery &` keeps running although nothing is connected to its input")
        finally:
            self.assertIsNotNone(stop_process(proc, timeout=10.0))

    def answers(self, port):
        try:
            return support.http("GET", "http://127.0.0.1:%d/healthz" % port)[0] == 200
        except OSError:
            return False

    def test_a_busy_port_is_an_error_not_a_silent_reuse(self):
        port = free_ports(1)[0]
        first = start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"))
        try:
            with self.assertRaises(RuntimeError) as caught:
                start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"), timeout=20.0)
            self.assertIn("port %d is already in use" % port, str(caught.exception))
            self.assertIsNone(first.poll(), "the server that owns the port is untouched")
        finally:
            stop_server(first)

    def test_an_answer_from_another_server_is_not_accepted(self):
        """The port is free when checked but taken a moment later: the health check must not be fooled by whoever answers."""
        port, other = free_ports(2)
        owner = start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"))
        real_socket = procs.socket.socket

        class Unbound(real_socket):   # make the up-front check pass, as if the port had been free an instant ago
            def bind(self, address):
                return super().bind(("127.0.0.1", other) if address == ("127.0.0.1", port) else address)

        procs.socket.socket = Unbound
        try:
            with self.assertRaises(RuntimeError) as caught:
                start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"), timeout=20.0)
        finally:
            procs.socket.socket = real_socket
            healthy = self.answers(port)
            stop_server(owner)
        message = str(caught.exception)
        self.assertIn("exited during start-up", message)
        self.assertIn("Could not listen", message)
        self.assertNotIn("\x1b", message)
        self.assertTrue(healthy, "the server that owns the port kept running")

    def test_health_reports_the_instance_only_when_one_was_given(self):
        port = free_ports(1)[0]
        proc = start_server(self.gallery(port), port, dict(os.environ, FLUIDIAN_OFFLINE="1"))
        try:
            import json as _json
            health = _json.loads(support.http("GET", "http://127.0.0.1:%d/healthz" % port)[2])
            self.assertRegex(health["instance"], r"^[0-9a-f]{16}$")
        finally:
            stop_server(proc)
        from fluidian.server import Engine
        engine = Engine(support.base_config(offline=True), scenes={"/": {"type": "Page", "props": {"title": "x"}}})
        engine.serve(block=False)
        try:
            import json as _json
            health = _json.loads(support.http("GET", "http://127.0.0.1:%d/healthz" % engine.cfg.port)[2])
            self.assertNotIn("instance", health)
        finally:
            engine.stop()

    @unittest.skipUnless(os.path.isdir("/proc"), "needs /proc")
    def test_a_killed_harness_takes_its_servers_with_it(self):
        port = free_ports(1)[0]
        helper = ("import sys, time; sys.path.insert(0, %r); from fluidian.procs import start_server; "
                  "p = start_server(%r, %d); print(p.pid, flush=True); time.sleep(120)" % (os.path.join(support.ROOT, "engine"), self.gallery(port), port))
        harness = subprocess.Popen([sys.executable, "-c", helper], stdout=subprocess.PIPE, env=dict(os.environ, FLUIDIAN_OFFLINE="1"))
        try:
            server = int(harness.stdout.readline())
            self.assertTrue(alive(server))
            harness.kill()   # no clean-up code runs: this is a crash, a Ctrl+C at the wrong moment, a closed terminal
            harness.wait(timeout=10)
            self.assertTrue(wait_until(lambda: not alive(server)), "the server noticed and exited by itself")
            self.assertFalse(self.answers(port))
        finally:
            harness.stdout.close()
            if harness.poll() is None:
                harness.kill()
                harness.wait()


@unittest.skipUnless(os.path.isdir("/proc"), "needs /proc")
class LeftoverTest(unittest.TestCase):
    """Recognising what an interrupted run left behind, and nothing else. Only this test's own processes are ever stopped."""

    SLEEP = "import time; time.sleep(120)"

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fluidian-leftover-test-")
        self.script = os.path.join(self.folder, "fluidian")
        with open(self.script, "w", encoding="utf-8") as fh:
            fh.write(self.SLEEP + "\n")
        self.pids = []

    def tearDown(self):
        for pid in self.pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        import shutil
        shutil.rmtree(self.folder, ignore_errors=True)

    def orphan(self, argv):
        """Start ``argv`` through a shell that exits at once, so that no Python process is its ancestor any more."""
        out = subprocess.run(["sh", "-c", "%s >/dev/null 2>&1 & echo $!" % " ".join(shlex.quote(a) for a in argv)], stdout=subprocess.PIPE, check=True).stdout
        pid = int(out)
        self.pids.append(pid)
        self.assertTrue(wait_until(lambda: len(procs._cmdline(pid)) >= len(argv), 5.0))
        return pid

    def child(self, argv):
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        self.assertTrue(wait_until(lambda: len(procs._cmdline(proc.pid)) >= len(argv), 5.0))
        return proc.pid

    def mine(self):
        return {e["pid"]: e for e in leftovers() if e["pid"] in self.pids or e["pid"] in getattr(self, "children", [])}

    def test_only_abandoned_harness_processes_are_recognised(self):
        browser = [sys.executable, "-c", self.SLEEP, "--headless=new", "--remote-debugging-port=9", "--user-data-dir=/tmp/fluidian-chrome-abc123"]
        legacy = [sys.executable, self.script, "gallery", "--port", "8795", "--offline"]
        stale_browser = self.orphan(browser)
        stale_gallery = self.orphan(legacy)
        stale_showcase = self.orphan([sys.executable, self.script, "showcase", "--port", "8796", "--offline"])
        not_ours = [
            self.orphan([sys.executable, self.script, "gallery", "--port", "8787", "--offline"]),          # someone's own server on the default port
            self.orphan([sys.executable, self.script, "gallery", "--port", "8795"]),                       # not the harness's command line
            self.orphan([sys.executable, self.script, "run", "--port", "8795", "--offline"]),              # nor this
            self.orphan([sys.executable, "-c", self.SLEEP, "--user-data-dir=/tmp/my-own-profile", "--remote-debugging-port=9"]),   # someone's own browser
            self.orphan(browser + ["--type=renderer"]),                                                     # a helper process of a browser, not the browser
        ]
        self.children = [self.child(browser), self.child(legacy)]   # launched by a live Python process: a run in progress
        found = self.mine()
        self.assertEqual(sorted(found), sorted([stale_browser, stale_gallery, stale_showcase]))
        self.assertEqual(found[stale_browser], {"pid": stale_browser, "kind": "browser", "port": 9, "profile": "/tmp/fluidian-chrome-abc123"})
        self.assertEqual(found[stale_gallery], {"pid": stale_gallery, "kind": "server", "port": 8795})
        for pid in not_ours + self.children:
            self.assertTrue(alive(pid))

    def test_leftovers_are_removed_and_nothing_else_is_touched(self):
        stale = [self.orphan([sys.executable, "-c", self.SLEEP, "--remote-debugging-port=9", "--user-data-dir=/tmp/fluidian-chrome-zzz"]),
                 self.orphan([sys.executable, self.script, "showcase", "--port", "8796", "--offline"])]
        bystander = self.orphan([sys.executable, self.script, "gallery", "--port", "8787", "--offline"])
        for entry in self.mine().values():
            self.assertTrue(remove_leftover(entry, timeout=5.0))
        self.assertTrue(wait_until(lambda: not any(alive(pid) for pid in stale), 5.0))
        self.assertTrue(alive(bystander))
        self.assertEqual(self.mine(), {})

    def test_a_leftover_that_refuses_signals_is_reported_as_still_there(self):
        pid = self.orphan([sys.executable, self.script, "gallery", "--port", "8795", "--offline"])
        entry = self.mine()[pid]
        real_kill = procs.os.kill
        refused = []

        def kill(target, sig):
            if target == pid:
                refused.append(sig)
                raise PermissionError(13, "Permission denied")
            return real_kill(target, sig)

        procs.os.kill = kill
        try:
            self.assertFalse(remove_leftover(entry, timeout=0.3), "it could not be stopped, and saying so is not an error")
        finally:
            procs.os.kill = real_kill
        self.assertEqual(refused, [signal.SIGTERM, signal.SIGKILL])
        self.assertTrue(alive(pid))

    def test_sweep_says_what_it_removed(self):
        real = procs.leftovers
        pid = self.orphan([sys.executable, self.script, "gallery", "--port", "8795", "--offline"])
        procs.leftovers = lambda: [e for e in real() if e["pid"] == pid]   # confine the sweep to this test's own process
        try:
            out = io.StringIO()
            self.assertEqual(procs.sweep(out), 1)
            self.assertEqual(out.getvalue(), "Removed 1 process left behind by an earlier, interrupted run.\n")
            quiet = io.StringIO()
            self.assertEqual(procs.sweep(quiet), 0)
            self.assertEqual(quiet.getvalue(), "", "nothing to remove, nothing to say")
        finally:
            procs.leftovers = real


class FakeBrowser:
    """Something that answers on a DevTools port the way a browser does, and stops listening when told ``Browser.close``."""

    def __init__(self, ident="abc"):
        import socket
        import threading
        self.ident = "/devtools/browser/" + ident
        self.closed = threading.Event()
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        import json
        while not self.closed.is_set():
            try:
                conn, _ = self.sock.accept()
            except OSError:
                continue
            with conn:
                conn.settimeout(2)
                try:
                    head = conn.recv(4096)
                    if b"Upgrade: websocket" in head:
                        conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
                        if b"Browser.close" in self.unmask(conn.recv(4096)):
                            self.closed.set()
                    else:
                        body = json.dumps({"Browser": "Fake/1.0", "webSocketDebuggerUrl": "ws://127.0.0.1:%d%s" % (self.port, self.ident)}).encode()
                        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
                except OSError:
                    pass
        self.sock.close()

    @staticmethod
    def unmask(frame):
        if len(frame) < 6:
            return b""
        length = frame[1] & 0x7F
        start = 2 + (2 if length == 126 else 8 if length == 127 else 0)
        mask, data = frame[start:start + 4], frame[start + 4:]
        return bytes(b ^ mask[i % 4] for i, b in enumerate(data))

    def stop(self):
        self.closed.set()
        self.thread.join(timeout=3)


class LaunchRecordTest(unittest.TestCase):
    """Finding an abandoned browser from the record its launcher left, without looking at the process table.

    This is the path that has to work on every system: a packaged browser may be started through
    wrappers, see a private /tmp, be adopted by an unexpected parent, or refuse signals.
    """

    DEAD_LAUNCHER = ("import sys; sys.path.insert(0, %r); from fluidian.procs import LaunchRecord; "
                     "r = LaunchRecord(%%d, %%d, %%r); r.update(endpoint=%%r); print(r.path, flush=True)" % os.path.join(support.ROOT, "engine"))

    def setUp(self):
        import shutil
        self.state = tempfile.mkdtemp(prefix="fluidian-state-test-")
        self.addCleanup(shutil.rmtree, self.state, True)
        self.previous = os.environ.get("FLUIDIAN_STATE_DIR")
        os.environ["FLUIDIAN_STATE_DIR"] = self.state
        self.addCleanup(lambda: os.environ.pop("FLUIDIAN_STATE_DIR", None) if self.previous is None else os.environ.__setitem__("FLUIDIAN_STATE_DIR", self.previous))
        real = procs.os.listdir   # keep the process table out of it: these tests are about records alone
        procs.os.listdir = lambda path=".": [] if path == "/proc" else real(path)
        self.addCleanup(setattr, procs.os, "listdir", real)

    def fake(self, ident="abc"):
        browser = FakeBrowser(ident)
        self.addCleanup(browser.stop)
        return browser

    def abandoned_record(self, port, endpoint, pid=999999, profile=""):
        """A record written by a launcher that has since exited, exactly as an interrupted run leaves it."""
        code = self.DEAD_LAUNCHER % (pid, port, profile, endpoint)
        out = subprocess.run([sys.executable, "-c", code], stdout=subprocess.PIPE, check=True, env=dict(os.environ)).stdout
        path = out.decode().strip()
        self.assertTrue(os.path.isfile(path))
        return path

    def test_a_record_is_written_locked_and_removed(self):
        record = procs.LaunchRecord(4242, 5555, "/tmp/fluidian-chrome-x")
        self.assertTrue(os.path.isfile(record.path))
        with open(record.path, encoding="utf-8") as fh:
            import json
            self.assertEqual(json.load(fh)["port"], 5555)
        with open(record.path, "r+", encoding="utf-8") as fh:
            self.assertFalse(procs._try_lock(fh), "the launcher holds the record for as long as it lives")
        path = record.path
        record.remove()
        self.assertFalse(os.path.exists(path))
        record.remove()   # twice is harmless

    def test_a_browser_whose_launcher_is_alive_is_in_use(self):
        browser = self.fake()
        record = procs.LaunchRecord(4242, browser.port, "")
        record.update(endpoint=browser.ident)
        self.addCleanup(record.remove)
        self.assertEqual(leftovers(), [])
        self.assertTrue(os.path.isfile(record.path), "and its record is left alone")

    def test_a_browser_whose_launcher_died_is_found_whatever_its_process_looks_like(self):
        browser = self.fake()
        path = self.abandoned_record(browser.port, browser.ident, pid=999999)   # a process id that tells us nothing, as with a wrapper
        found = leftovers()
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["kind"], found[0]["port"], found[0]["record"], found[0]["endpoint"]), ("browser", browser.port, path, browser.ident))

    def test_it_is_asked_to_quit_over_its_port_and_no_signal_is_needed(self):
        browser = self.fake()
        profile = tempfile.mkdtemp(prefix="fluidian-chrome-")
        path = self.abandoned_record(browser.port, browser.ident, profile=profile)
        real_kill, signals = procs.os.kill, []
        procs.os.kill = lambda pid, sig: signals.append((pid, sig))
        try:
            self.assertTrue(remove_leftover(leftovers()[0], timeout=5.0))
        finally:
            procs.os.kill = real_kill
        self.assertTrue(browser.closed.is_set(), "the browser received Browser.close")
        self.assertEqual(signals, [])
        self.assertFalse(os.path.exists(path), "the record goes with it")
        self.assertFalse(os.path.exists(profile), "and so does the temporary profile")
        self.assertEqual(leftovers(), [])

    def test_one_that_will_not_quit_and_refuses_signals_is_reported_and_kept_on_record(self):
        browser = self.fake()
        browser.unmask = lambda frame: b""   # it ignores the request to close
        path = self.abandoned_record(browser.port, browser.ident, pid=os.getpid())
        real_kill = procs.os.kill

        def refuse(pid, sig):
            raise PermissionError(13, "Permission denied")

        procs.os.kill = refuse
        try:
            self.assertFalse(remove_leftover(leftovers()[0], timeout=0.4))
        finally:
            procs.os.kill = real_kill
        self.assertTrue(os.path.isfile(path), "so that the next run tries again")

    def test_a_record_for_a_browser_that_has_gone_is_tidied_away(self):
        port = free_ports(1)[0]
        profile = tempfile.mkdtemp(prefix="fluidian-chrome-")
        path = self.abandoned_record(port, "/devtools/browser/gone", profile=profile)
        self.assertEqual(leftovers(), [])
        self.assertFalse(os.path.exists(path))
        self.assertFalse(os.path.exists(profile))

    def test_another_browser_that_now_has_the_port_is_not_touched(self):
        other = self.fake("someone-elses")
        path = self.abandoned_record(other.port, "/devtools/browser/ours")
        self.assertEqual(leftovers(), [], "the id on the port is not the one written down")
        self.assertFalse(os.path.exists(path))
        self.assertFalse(other.closed.is_set())

    def test_only_a_profile_folder_the_harness_made_is_ever_deleted(self):
        port = free_ports(1)[0]
        precious = tempfile.mkdtemp(prefix="not-ours-")
        self.addCleanup(os.rmdir, precious)
        self.abandoned_record(port, "/devtools/browser/gone", profile=precious)
        self.assertEqual(leftovers(), [])
        self.assertTrue(os.path.isdir(precious))

    def test_damaged_records_and_an_unusable_folder_are_not_errors(self):
        with open(os.path.join(self.state, "browser-1-bad.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(leftovers(), [])
        self.assertEqual(os.listdir(self.state), [], "a record nobody holds and nobody can read is removed")
        blocker = os.path.join(self.state, "a-file")
        open(blocker, "w").close()
        os.environ["FLUIDIAN_STATE_DIR"] = os.path.join(blocker, "inside")   # a folder cannot be made inside a file
        self.assertIsNone(procs.state_dir())
        record = procs.LaunchRecord(1, 2, "")   # nowhere to write: no record, and no error
        self.assertIsNone(record.path)
        record.update(endpoint="x")
        record.remove()
        self.assertEqual(leftovers(), [])

    def test_sweep_closes_recorded_browsers_and_says_so(self):
        browser = self.fake()
        self.abandoned_record(browser.port, browser.ident)
        out = io.StringIO()
        self.assertEqual(procs.sweep(out), 1)
        self.assertTrue(browser.closed.is_set())
        self.assertEqual(out.getvalue(), "Removed 1 process left behind by an earlier, interrupted run.\n")

    def test_describe_reports_what_the_clean_up_can_see(self):
        browser = self.fake()
        self.abandoned_record(browser.port, browser.ident)
        text = procs.describe(os.getpid(), browser.port)
        self.assertIn("launcher gone", text)
        self.assertIn("port %d answers as: %s" % (browser.port, browser.ident), text)


if __name__ == "__main__":
    unittest.main()
