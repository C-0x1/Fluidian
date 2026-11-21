<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# The AI kernel

The kernel is the part of the engine that executes capabilities. It is one function, `Kernel.invoke(capability, input)`, reached three ways: from a component attachment in the browser, from `ctx.ai` in an app, and from `fluidian ai` on the command line. All three take the same path.

## The pipeline

| # | Stage | What happens | Can end the call |
| --- | --- | --- | --- |
| 1 | Policy | The capability id is checked against `policy_allow` and `policy_deny` | `policy_denied` |
| 2 | Consent | Capabilities that process behaviour or the microphone need a grant for the session | `consent_required` |
| 3 | Validate input | The payload is checked against the capability's input schema | `invalid_input` |
| 4 | Redact | Emails, phone numbers, card numbers and similar values are replaced with reversible placeholders such as `⟦EMAIL_1⟧` | — |
| 5 | Shield | Fields declared untrusted are scored for prompt injection and fenced | `blocked_injection` in block mode |
| 6 | Moderate | Optional content check, locally or through the moderation endpoint | `moderation_blocked` |
| 7 | Cache | Exact match on capability and input, then semantic similarity | returns the cached result |
| 8 | Coalesce | An identical call already in flight is awaited instead of repeated | returns the shared result |
| 9 | Budget | Session and global token ceilings | switches to Reflex |
| 10 | Route | Picks the tier's model and its fallback chain | — |
| 11 | Reason or Reflex | The model with a strict JSON schema, or the local implementation | — |
| 12 | Validate output | Schema check; one self-repair round with the validation errors | switches to Reflex |
| 13 | Ground | Scenes are normalised against the registry; unknown parts are removed | — |
| 14 | Restore | Placeholders are swapped back, so people see real values | — |
| 15 | Record | Provenance, telemetry, the ledger and optional audit and replay files | — |

A call never fails because the provider failed. Timeouts, rate limits, malformed output and exhausted budgets all end in a Reflex answer whose provenance says `degraded`.

## Three kinds of capability

| Kind | Count | How it is answered |
| --- | --- | --- |
| **model** | 122 | By the model when a key is set; by Reflex otherwise |
| **hybrid** | 19 | The engine computes the facts — totals, trends, outliers, contrast ratios — and the model only words them. Numbers in the output are never the model's. |
| **direct** | 44 | By the engine alone: parsing, colour maths, redaction, routing tables, telemetry. Identical online and offline. |

## Reflex: the offline engine

`engine/fluidian/reflex/` implements every model capability with deterministic code:

| Module | Examples |
| --- | --- |
| `text` | Extractive summaries, titles, tone rules, plain-language rewriting, question generation, decision extraction |
| `parse` | Natural dates and quantities, unit conversion, personal-data detection, address and signature parsing, format repair |
| `data` | Column typing, chart selection, robust anomaly detection on detrended residuals, linear forecasts, plain-language queries, formulas |
| `design` | Themes from prompts, palettes and harmonies in OKLCH, contrast repair, type pairing, procedural illustration |
| `scene` | Interface composition from archetypes, schema forms, wireframe and HTML import, empty states, skeletons |
| `review` | Usability heuristics, accessibility audit, scene linting, test synthesis |
| `behavior` | Intent routing with argument extraction, planning, frustration and expertise signals, focus prediction |

Reflex is narrower than a model — it follows rules — but it is instant, free, private and reproducible, which makes it the right tool for tests, demos, air-gapped installations and the degraded path.

### Choosing the provider per call

```python
ctx.ai("content.summarize", {"text": notes})                 # auto: model if available, Reflex otherwise
```
```bash
./fluidian ai content.summarize --mode reflex                # force the local implementation
./fluidian ai content.summarize --mode reason                # require the model; fail if unavailable
```

## Routing

Capabilities name a **tier**, not a model.

| Tier | Used for | Default preference |
| --- | --- | --- |
| `fast` | Field-level work: completion, parsing, labels, routing | the smallest current model |
| `balanced` | Composition, analysis, planning | the general model |
| `deep` | Reviews and multi-step reasoning | the strongest model |
| `embed`, `moderation`, `transcribe`, `speech`, `image` | The corresponding endpoints | — |

Each tier has an ordered list of model ids. At first use the kernel asks the provider which models the account can reach and takes the first match; if none matches, it classifies the available models by name. When a model returns "not found" mid-run, the next one in the chain is used and remembered. `./fluidian ai perf.router` prints the live table.

## Caching and coalescing

Results are cached per capability and normalised input for `cache_ttl` seconds (default 900). A second, semantic layer returns a cached result when a new input embeds within `semantic_cache_threshold` (default 0.93) of a previous one. Identical requests that arrive while the first is still running share its answer. Cached results are marked in provenance and cost no tokens.

## Budgets

Two ceilings are enforced in tokens: per session (`session_token_budget`, default 400,000) and for the process (`global_token_budget`, default 20,000,000). When a ceiling is reached, calls are answered by Reflex and marked `degraded`. `trust.budget` reports the current state.

## Provenance

Every result has the same envelope:

```json
{
  "ok": true,
  "capability": "data.insights",
  "data": { "title": "Revenue is rising", "body": "…", "bullets": ["…"], "confidence": 0.71, "tone": "success" },
  "provenance": {
    "traceId": "4709768c9d834cb1", "provider": "reflex", "model": "", "tier": "fast",
    "cached": false, "latencyMs": 3.5, "tokens": { "in": 0, "out": 0 },
    "redactions": 0, "repairs": 0, "groundingFixes": 0, "degraded": false, "shield": "safe",
    "confidence": 0.71, "at": "2026-11-19T16:47:47Z"
  }
}
```

The runtime turns provenance into the chip shown beside generated content, and the developer tools list it per call. Failures have `"ok": false` and an `error` with a stable `code` and a readable `message`.

## Consent, policy, audit and replay

| Feature | Configuration | Effect |
| --- | --- | --- |
| Consent | `consent_required` (default: `microphone`, `personalization`) | Capabilities declaring a scope fail with `consent_required` until `trust.consent` grants it for the session |
| Policy | `FLUIDIAN_POLICY_ALLOW`, `FLUIDIAN_POLICY_DENY` | Allow or deny capability ids and families such as `modal.*` |
| Audit | `FLUIDIAN_AUDIT_PATH` | Appends one JSON line per call: capability, provider, model, tokens, redaction count, shield verdict, trace id and a hash of the input. Inputs and outputs themselves are not written. |
| Replay | `FLUIDIAN_REPLAY=record` or `replay`, `FLUIDIAN_REPLAY_PATH` | Records model answers and plays them back, for deterministic demos and regression tests |

## Adding a capability

```python
cap("content.haiku", "Haiku Writer",
    "Turns a status message into a haiku.",
    why="Because even a build failure deserves a moment of calm.",
    do="Write a three-line haiku (5-7-5 syllables) that conveys the message. No title.",
    inp={"text": "str"}, out={"lines": ["str"]},
    ex={"text": "The build failed on the linting step."},
    present="annotate", tier="fast",
    reflex=lambda i, c: {"lines": [T.clip(i["text"], 30), "a quiet red light glows", "fix, commit, breathe out"]})
```

That declaration is the whole feature: the schema sent to the model, the validation of what comes back, the offline behaviour, the documentation page and the contract tests are derived from it. Run `./fluidian codegen && ./fluidian docs`, then `./fluidian ai content.haiku`.
