<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Configuration

Settings are resolved in this order, later sources winning: built-in defaults, `fluidian.config.json` in the working directory, environment variables, command-line flags.

## Provider

| Variable | Config key | Default | Meaning |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` (or `FLUIDIAN_OPENAI_API_KEY`) | `api_key` | unset | Enables model-backed answers. Unset means the offline Reflex engine. |
| `OPENAI_BASE_URL` (or `FLUIDIAN_OPENAI_BASE_URL`) | `base_url` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID` | `organization`, `project` | unset | Sent as organisation and project headers |
| `FLUIDIAN_OFFLINE` | `offline` | `false` | Use Reflex even when a key is set |
| `FLUIDIAN_MODEL` | — | unset | One model for the `fast`, `balanced` and `deep` tiers |
| `FLUIDIAN_MODEL_<TIER>` | `models.<tier>` | preference lists | A model or comma-separated chain for `FAST`, `BALANCED`, `DEEP`, `EMBED`, `MODERATION`, `TRANSCRIBE`, `SPEECH` or `IMAGE` |
| `FLUIDIAN_DISCOVER_MODELS` | `discover_models` | `true` | Ask the provider which models are available before choosing |
| `FLUIDIAN_INSTRUCTION_ROLE` | `instruction_role` | `auto` | `auto`, `system` or `developer` |
| `FLUIDIAN_REASONING_EFFORT` | `reasoning_effort` | `low` | Sent to models that accept it |
| `FLUIDIAN_TIMEOUT` | `request_timeout` | `45` | Seconds per provider request |
| `FLUIDIAN_MAX_RETRIES` | `max_retries` | `2` | Retries for transient provider errors |

## Server

| Variable | Config key | Default | Meaning |
| --- | --- | --- | --- |
| `FLUIDIAN_HOST` | `host` | `127.0.0.1` | Interface to bind |
| `FLUIDIAN_PORT` | `port` | `8787` | Port to bind |
| `FLUIDIAN_ALLOWED_HOSTS` | `allowed_hosts` | empty | Extra `Host` names to accept, comma-separated |
| `FLUIDIAN_EMBED_ORIGINS` | `embed_origins` | none | Comma-separated origins allowed to frame the app with `<fluidian-app>`, for example `https://www.example.com`. `*` allows any. Without it the engine sends `frame-ancestors 'none'` |
| `FLUIDIAN_DEV` | `dev` | `true` | Developer tools and detailed errors. `--production` sets it to false. |
| — | `max_body_bytes` | `2000000` | Limit for JSON request bodies |
| — | `max_media_bytes` | `12000000` | Limit for audio and image uploads |
| — | `session_ttl` | `1800` | Seconds before an idle session is discarded |
| `FLUIDIAN_LOCALE` | `locale` | `en-US` | Locale used when the browser sends none |
| `FLUIDIAN_DATA_DIR` | `data_dir` | `./.fluidian` | Where build output, replay files and caches are written |

## Kernel

| Variable | Config key | Default | Meaning |
| --- | --- | --- | --- |
| `FLUIDIAN_CACHE` | `cache_enabled` | `true` | Result cache |
| `FLUIDIAN_CACHE_TTL` | `cache_ttl` | `900` | Seconds a result stays cached |
| `FLUIDIAN_EMBEDDINGS` | — | `local` | `local` computes embeddings in the engine; `openai` uses the embeddings endpoint |
| — | `cache_max_entries` | `2000` | Cache size |
| — | `semantic_cache_threshold` | `0.93` | Similarity needed for a semantic cache hit |
| `FLUIDIAN_SESSION_TOKEN_BUDGET` | `session_token_budget` | `400000` | Tokens per session before degrading to Reflex |
| `FLUIDIAN_GLOBAL_TOKEN_BUDGET` | `global_token_budget` | `20000000` | Tokens per engine process |
| `FLUIDIAN_REDACTION` | `redaction` | `true` | Replace personal data before provider requests |
| `FLUIDIAN_SHIELD` | `shield_mode` | `flag` | Injection shield: `off`, `flag` (fence and record) or `block` (refuse) |
| `FLUIDIAN_MODERATION` | `moderation` | `reflex` | `off`, `reflex` (local) or `openai` (moderation endpoint) |
| `FLUIDIAN_POLICY_ALLOW` | `policy_allow` | empty: everything | Capability ids or families (`data.*`) that may run |
| `FLUIDIAN_POLICY_DENY` | `policy_deny` | empty | Capability ids or families that may not run |
| — | `consent_required` | `["microphone", "personalization"]` | Consent scopes that must be granted per session |
| `FLUIDIAN_AUDIT_PATH` | `audit_path` | unset | Append-only JSON Lines file of call metadata |
| `FLUIDIAN_REPLAY` | `replay_mode` | `off` | `record` or `replay` model answers |
| `FLUIDIAN_REPLAY_PATH` | `replay_path` | in the data directory | Where recordings are stored |
| — | `pricing` | empty | Per-model prices, `{"model": {"in": usd_per_million, "out": usd_per_million}}`, used to show cost in telemetry |

## Tooling

| Variable | Meaning |
| --- | --- |
| `FLUIDIAN_BROWSER` | Chrome or Chromium binary for browser tests and screenshots |
| `FLUIDIAN_TEST_PORT` | First of three consecutive ports for the browser tests; by default three free ports are chosen at run time |
| `FLUIDIAN_SHOT_PORT` | First of two ports for the screenshot tool (default `8793`) |
| `FLUIDIAN_LIFELINE` | Set to `stdin` to make `run`, `serve`, `gallery` and `showcase` exit when their standard input closes. A program that starts the engine as a child holds the other end of the pipe, and the engine can then never outlive it |
| `FLUIDIAN_INSTANCE` | A token of your choice that `/healthz` echoes back as `instance`, so a program can tell the engine it started from any other answering on the same port |
| `FLUIDIAN_STATE_DIR` | Where the test and screenshot tools keep the record of each browser they start, so that a later run can close one that an interrupted run left behind. Default: a private folder named `fluidian-run-<uid>` in the temporary directory |
| `NO_COLOR` | Disable coloured terminal output |

## A complete config file

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "allowed_hosts": ["app.example.com"],
  "models": {
    "fast": ["your-small-model"],
    "balanced": ["your-general-model", "your-fallback-model"],
    "deep": "your-strongest-model"
  },
  "session_token_budget": 200000,
  "shield_mode": "block",
  "moderation": "openai",
  "policy_deny": ["modal.*"],
  "audit_path": "/var/log/fluidian/audit.jsonl"
}
```

Do not put the API key in this file if the file is committed; use the environment.

## Inspecting the result

```bash
./fluidian doctor              # shows the mode and what was detected
./fluidian ai perf.router      # the tier-to-model table in effect
./fluidian ai trust.budget     # budgets and usage
```
