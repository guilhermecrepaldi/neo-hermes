# free-claude-code Provider Patterns (36.4k stars)

Repo: Alishahryar1/free-claude-code | MIT | 712 commits

## Architecture

A proxy that routes Anthropic/OpenAI API calls to 17 providers.
Key difference from Hermes: it's a proxy, not an agent harness.

## Patterns We Absorbed

| Pattern | Our Implementation |
|---------|-------------------|
| Provider Registry | `providers.py` — CATALOG dict with ProviderInfo dataclass |
| Rate Limiter | `providers.py` — RateLimiter (token bucket per provider) |
| Admin UI | `admin_ui.py` — FastAPI + html template at /admin |
| Error Mapping | `error_mapping.py` — 13 error types with recoverable flag + suggestion |
| Model Catalog | `model_catalog.py` — get_models_json() for /v1/models endpoint |
| Launchers | `cli/hermes-launcher.py` — claude/codex wrappers |

## Key Design Decisions

1. **CATALOG dict** over class hierarchy — simpler, easier to extend
2. **Token bucket** rate limiting — per-provider, not global
3. **Error categorization** by keyword matching — no regex over-engineering
4. **Flat model list** — each provider lists its models explicitly
5. **Local > cheap > premium** tier ordering for select_best_provider()
