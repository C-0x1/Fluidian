"""Engine configuration.

Configuration is resolved in three layers, later layers winning:

1. built-in defaults (this file)
2. ``fluidian.config.json`` in the working directory (optional)
3. environment variables (``OPENAI_API_KEY``, ``FLUIDIAN_*``)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Ordered preference chains.  The router intersects each chain with the models
# the account can actually reach (``GET /v1/models``) and falls back down the
# chain when a model is retired or unavailable.  Override any tier with
# ``FLUIDIAN_MODEL_<TIER>`` (comma separated for a custom chain).
DEFAULT_MODELS: Dict[str, List[str]] = {
    "fast": ["gpt-6-luna", "gpt-5.6-luna", "gpt-5.4-mini", "gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"],
    "balanced": ["gpt-6.2-sol", "gpt-6.1-sol", "gpt-6-sol", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4", "gpt-5", "gpt-4.1", "gpt-4o"],
    "deep": ["gpt-6.2-astra", "gpt-6-astra", "gpt-6.2-sol", "gpt-5.5-pro", "gpt-5.5", "gpt-5", "gpt-4.1"],
    "embed": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
    "moderation": ["omni-moderation-latest"],
    "transcribe": ["gpt-transcribe", "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"],
    "speech": ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"],
    "image": ["gpt-image-2.6-flare", "gpt-image-2.5-flare", "gpt-image-2", "gpt-image-1.5", "gpt-image-1"],
}

# Substrings used to classify unknown model ids into tiers when none of the
# preferred ids are available on the account.
TIER_HINTS: Dict[str, List[str]] = {
    "fast": ["luna", "nano", "mini", "flash", "small", "haiku", "lite"],
    "balanced": ["sol", "terra", "gpt-5", "gpt-4", "medium"],
    "deep": ["astra", "pro", "opus", "large"],
    "embed": ["embedding", "embed"],
    "moderation": ["moderation"],
    "transcribe": ["transcribe", "whisper"],
    "speech": ["tts"],
    "image": ["image"],
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


@dataclass
class Config:
    # --- provider -----------------------------------------------------
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    organization: str = ""
    project: str = ""
    models: Dict[str, List[str]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_MODELS.items()})
    offline: bool = False            # force the Reflex provider even when a key exists
    instruction_role: str = "auto"   # auto | system | developer
    reasoning_effort: str = "low"    # sent to reasoning models; dropped automatically when rejected
    request_timeout: float = 45.0
    max_retries: int = 2
    discover_models: bool = True
    # --- server -------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8787
    allowed_hosts: List[str] = field(default_factory=list)
    embed_origins: List[str] = field(default_factory=list)   # origins allowed to frame the app with <fluidian-app>; "*" allows any
    max_body_bytes: int = 2_000_000
    max_media_bytes: int = 12_000_000
    session_ttl: float = 1800.0
    dev: bool = True
    # --- kernel -------------------------------------------------------
    cache_enabled: bool = True
    cache_ttl: float = 900.0
    cache_max_entries: int = 2000
    semantic_cache_threshold: float = 0.93
    session_token_budget: int = 400_000
    global_token_budget: int = 20_000_000
    redaction: bool = True
    shield_mode: str = "flag"        # off | flag | block
    moderation: str = "reflex"       # off | reflex | openai
    replay_mode: str = "off"         # off | record | replay
    replay_path: str = ""
    audit_path: str = ""             # JSONL ledger; empty disables persistence
    policy_allow: List[str] = field(default_factory=list)   # capability ids / "category.*"
    policy_deny: List[str] = field(default_factory=list)
    consent_required: List[str] = field(default_factory=lambda: ["microphone", "personalization"])
    pricing: Dict[str, Dict[str, float]] = field(default_factory=dict)  # model -> {"in": usd/1M, "out": usd/1M}
    locale: str = "en-US"
    data_dir: str = ""

    # ------------------------------------------------------------------
    @property
    def live(self) -> bool:
        """True when requests should be sent to the model provider."""
        return bool(self.api_key) and not self.offline

    def redacted(self) -> Dict[str, Any]:
        out = dict(self.__dict__)
        if out.get("api_key"):
            key = out["api_key"]
            out["api_key"] = (key[:3] + "…" + key[-4:]) if len(key) > 10 else "…"
        return out


def load_config(cwd: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Config:
    cfg = Config()
    cwd = cwd or os.getcwd()

    path = os.path.join(cwd, "fluidian.config.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise SystemExit("fluidian.config.json is not valid JSON: %s" % exc)
        for key, value in data.items():
            if key == "models" and isinstance(value, dict):
                for tier, chain in value.items():
                    cfg.models[tier] = [chain] if isinstance(chain, str) else list(chain)
            elif hasattr(cfg, key):
                setattr(cfg, key, value)

    env = os.environ
    cfg.api_key = env.get("FLUIDIAN_OPENAI_API_KEY") or env.get("OPENAI_API_KEY") or cfg.api_key
    cfg.base_url = (env.get("FLUIDIAN_OPENAI_BASE_URL") or env.get("OPENAI_BASE_URL") or cfg.base_url).rstrip("/")
    cfg.organization = env.get("OPENAI_ORG_ID") or env.get("OPENAI_ORGANIZATION") or cfg.organization
    cfg.project = env.get("OPENAI_PROJECT_ID") or env.get("OPENAI_PROJECT") or cfg.project
    for tier in list(cfg.models):
        raw = env.get("FLUIDIAN_MODEL_" + tier.upper())
        if raw:
            cfg.models[tier] = [m.strip() for m in raw.split(",") if m.strip()]
    if env.get("FLUIDIAN_MODEL"):
        for tier in ("fast", "balanced", "deep"):
            cfg.models[tier] = [env["FLUIDIAN_MODEL"].strip()]
    cfg.offline = _env_bool("FLUIDIAN_OFFLINE", cfg.offline)
    cfg.instruction_role = env.get("FLUIDIAN_INSTRUCTION_ROLE", cfg.instruction_role)
    cfg.reasoning_effort = env.get("FLUIDIAN_REASONING_EFFORT", cfg.reasoning_effort)
    cfg.request_timeout = _env_float("FLUIDIAN_TIMEOUT", cfg.request_timeout)
    cfg.max_retries = _env_int("FLUIDIAN_MAX_RETRIES", cfg.max_retries)
    cfg.discover_models = _env_bool("FLUIDIAN_DISCOVER_MODELS", cfg.discover_models)
    cfg.host = env.get("FLUIDIAN_HOST", cfg.host)
    cfg.port = _env_int("FLUIDIAN_PORT", cfg.port)
    if env.get("FLUIDIAN_ALLOWED_HOSTS"):
        cfg.allowed_hosts = [h.strip() for h in env["FLUIDIAN_ALLOWED_HOSTS"].split(",") if h.strip()]
    if env.get("FLUIDIAN_EMBED_ORIGINS"):
        cfg.embed_origins = [o.strip().rstrip("/") for o in env["FLUIDIAN_EMBED_ORIGINS"].split(",") if o.strip()]
    cfg.dev = _env_bool("FLUIDIAN_DEV", cfg.dev)
    cfg.cache_enabled = _env_bool("FLUIDIAN_CACHE", cfg.cache_enabled)
    cfg.cache_ttl = _env_float("FLUIDIAN_CACHE_TTL", cfg.cache_ttl)
    cfg.session_token_budget = _env_int("FLUIDIAN_SESSION_TOKEN_BUDGET", cfg.session_token_budget)
    cfg.global_token_budget = _env_int("FLUIDIAN_GLOBAL_TOKEN_BUDGET", cfg.global_token_budget)
    cfg.redaction = _env_bool("FLUIDIAN_REDACTION", cfg.redaction)
    cfg.shield_mode = env.get("FLUIDIAN_SHIELD", cfg.shield_mode)
    cfg.moderation = env.get("FLUIDIAN_MODERATION", cfg.moderation)
    cfg.replay_mode = env.get("FLUIDIAN_REPLAY", cfg.replay_mode)
    cfg.replay_path = env.get("FLUIDIAN_REPLAY_PATH", cfg.replay_path)
    cfg.audit_path = env.get("FLUIDIAN_AUDIT_PATH", cfg.audit_path)
    cfg.locale = env.get("FLUIDIAN_LOCALE", cfg.locale)
    cfg.data_dir = env.get("FLUIDIAN_DATA_DIR", cfg.data_dir) or os.path.join(cwd, ".fluidian")
    if env.get("FLUIDIAN_POLICY_DENY"):
        cfg.policy_deny = [p.strip() for p in env["FLUIDIAN_POLICY_DENY"].split(",") if p.strip()]
    if env.get("FLUIDIAN_POLICY_ALLOW"):
        cfg.policy_allow = [p.strip() for p in env["FLUIDIAN_POLICY_ALLOW"].split(",") if p.strip()]

    for key, value in (overrides or {}).items():
        if value is not None and hasattr(cfg, key):
            setattr(cfg, key, value)
    if not cfg.replay_path:
        cfg.replay_path = os.path.join(cfg.data_dir, "replay.jsonl")
    return cfg
