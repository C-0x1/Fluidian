<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# OpenAI integration

With `OPENAI_API_KEY` set, model and hybrid capabilities are answered by OpenAI models. This page describes exactly what is sent, how models are chosen, and what happens when something goes wrong.

## Enabling it

```bash
export OPENAI_API_KEY=sk-...
./fluidian doctor --live
```

`doctor --live` lists the models the key can reach, prints the model each tier will use, and makes one structured-output request so you can see a real round trip, its latency and any parameters that had to be negotiated.

Other variables:

| Variable | Purpose |
| --- | --- |
| `OPENAI_BASE_URL` | Use an OpenAI-compatible endpoint (a gateway, a proxy, a regional deployment) |
| `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID` | Sent as organisation and project headers |
| `FLUIDIAN_MODEL` | One model for every chat tier |
| `FLUIDIAN_MODEL_FAST`, `_BALANCED`, `_DEEP`, `_EMBED`, `_MODERATION`, `_TRANSCRIBE`, `_SPEECH`, `_IMAGE` | A model, or a comma-separated preference list, for one tier |
| `FLUIDIAN_REASONING_EFFORT` | Effort hint for reasoning models (default `low`) |
| `FLUIDIAN_TIMEOUT`, `FLUIDIAN_MAX_RETRIES` | Request timeout in seconds (45) and retry count (2) |
| `FLUIDIAN_DISCOVER_MODELS` | Set to `0` to skip the model-list request and trust the configured ids |

The key is read from the engine's environment only. It is never sent to the browser or to the app process.

## What a request looks like

Capabilities use the Chat Completions endpoint with **Structured Outputs**:

```json
{
  "model": "<the tier's model>",
  "messages": [
    { "role": "developer", "content": "<the capability's instruction, the component catalogue if it composes UI>" },
    { "role": "user", "content": "<the redacted input as JSON, untrusted fields fenced>" }
  ],
  "response_format": { "type": "json_schema", "json_schema": { "name": "data_insights", "strict": true, "schema": { "…": "…" } } },
  "max_completion_tokens": 900
}
```

- The schema is compiled from the capability's declared output and is always strict: every property required, optional values expressed as nullable, no additional properties. The test suite checks all 141 model-facing schemas against these rules.
- Sampling parameters (`temperature`, `top_p`, `n`, `seed`) are never sent; several current models reject them.
- The instruction role is `developer` on `api.openai.com` and `system` on other endpoints (override with `FLUIDIAN_INSTRUCTION_ROLE`).
- `reasoning_effort` is sent only to models that accept it.
- Capabilities that compose interfaces stream, so a scene appears as it is written.

Other endpoints are used by the capabilities that need them: moderations, audio transcription, speech and images, each with a local fallback. Embeddings for the semantic cache and search are computed locally by default; set `FLUIDIAN_EMBEDDINGS=openai` to use the embeddings endpoint instead.

## Model selection

Model ids are data. `engine/fluidian/config.py` holds a preference list per tier, newest first, ending in widely available models. The engine does not assume any of them exists:

1. On first use it requests the account's model list.
2. For each tier it picks the first preferred id that is present.
3. If none is present it classifies what is available by name (for example ids containing `mini` or `nano` for the fast tier).
4. If a chosen model later returns "model not found", the next candidate is tried and the choice is remembered.

Because of this, an outdated default list costs nothing more than a fallback. To pin exact models, set the tier variables above or a `models` object in `fluidian.config.json`:

```json
{ "models": { "fast": ["your-small-model"], "balanced": ["your-general-model"], "deep": ["your-strongest-model"] } }
```

## Adaptive parameter negotiation

Model generations disagree about request parameters. Rather than hard-code a table that goes stale, the client reads the provider's error, adjusts the request, retries, and remembers what it learned for that model:

| The provider says | The client does |
| --- | --- |
| `max_tokens` is not supported, use `max_completion_tokens` (or the reverse) | Switches the parameter |
| The `developer` role is not supported (or `system` is not) | Switches the role |
| `reasoning_effort` is not supported | Stops sending it |
| `response_format` of type `json_schema` is not supported | Falls back to JSON mode and validates locally |
| `stream_options` is not supported | Stops sending it |
| The output was cut off by the token limit | Raises the limit and retries once |

The negotiated set is visible in `doctor --live` and in the developer tools.

## Failure handling

| Failure | Response |
| --- | --- |
| HTTP 429 or 5xx, connection errors | Retry with exponential backoff, honouring `Retry-After` |
| Model not found | Next model in the tier's chain |
| Output violates the schema | One repair round that shows the model its validation errors |
| Output truncated | JSON is completed where possible, otherwise retried with a higher limit |
| Still failing, key invalid, or budget exhausted | The Reflex engine answers; provenance records `degraded` and the provider's message |

## What leaves your machine

Only the capability's input, after redaction. Personal data detected in it is replaced by placeholders before the request and restored in the response, so the provider does not receive it and the person still sees it. Fields that a capability declares as untrusted — message threads, pasted text, imported documents — are fenced and labelled so that instructions inside them are treated as content. See [Security](security.md).

## Verifying without a key

The whole model path is tested against `engine/fluidian/testkit/mock_openai.py`, a local server that enforces authentication, strict-schema rules and several parameter dialects, and can be told to fail, rate-limit, truncate or return invalid output. `./fluidian test --quick` runs those tests. They prove the client's behaviour against the protocol; `doctor --live` is how you confirm it against your own account and models.
