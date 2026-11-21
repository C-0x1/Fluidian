"""Shared helpers for the engine tests."""
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fluidian.capabilities import registry  # noqa: E402
from fluidian.config import Config  # noqa: E402
from fluidian.kernel import Kernel  # noqa: E402
from fluidian.testkit.mock_openai import KEY  # noqa: E402

CAPS = registry.load_all()

ACTIONS = [
    {"name": "create_invoice", "description": "Create a new invoice for a customer",
     "params": {"customer": "string customer name", "amount": "number amount in USD", "due": "date due date"}},
    {"name": "send_reminder", "description": "Send a payment reminder for an invoice", "params": {"invoice": "string invoice number such as INV-2041"}},
    {"name": "export_report", "description": "Export the current view as a file", "params": {"format": "string one of csv, xlsx, pdf"}},
]

INVOICES = [
    {"invoice": "INV-1", "customer": "Globex", "amount": 12400, "status": "Overdue"},
    {"invoice": "INV-2", "customer": "Halden", "amount": 3150, "status": "Paid"},
    {"invoice": "INV-3", "customer": "Tessellate", "amount": 7600, "status": "Overdue"},
    {"invoice": "INV-4", "customer": "Saffron", "amount": 1320, "status": "Overdue"},
    {"invoice": "INV-5", "customer": "Orbit", "amount": 18250, "status": "Pending"},
]


def base_config(**overrides):
    """A configuration that ignores the developer's environment and config files."""
    cfg = Config()
    cfg.data_dir = tempfile.mkdtemp(prefix="fluidian-test-")
    cfg.port = 0
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def offline_kernel(**overrides):
    return Kernel(base_config(offline=True, **overrides))


def live_kernel(mock, model="gpt-6-luna", **overrides):
    """A kernel wired to the mock provider, with every chat tier pinned to one model."""
    cfg = base_config(api_key=KEY, base_url=mock.base_url, **overrides)
    chain = model if isinstance(model, list) else [model]
    for tier in ("fast", "balanced", "deep"):
        cfg.models[tier] = list(chain)
    return Kernel(cfg)


def example_node(spec):
    """Build a scene node from a component's registry example."""
    props = dict(spec["example"].get("props") or {})
    for arg, value in zip(spec["args"], spec["example"].get("args") or []):
        props[arg["name"]] = value
    node = {"type": spec["type"], "props": props}
    if spec["container"]:
        node["children"] = [{"type": "Text", "props": {"content": "Inside %s" % spec["type"]}}]
    return node


def kind_of(cap):
    return "direct" if cap.direct else ("hybrid" if cap.facts else "model")


def http(method, url, body=None, headers=None, timeout=10):
    """Small HTTP helper returning (status, headers, bytes) without raising on 4xx/5xx."""
    data = json.dumps(body).encode("utf-8") if isinstance(body, (dict, list)) else body
    req = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}))
    if isinstance(body, (dict, list)):
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()
    except (urllib.error.URLError, ConnectionError):
        return 0, {}, b""  # the server closed the connection before the request was fully sent
