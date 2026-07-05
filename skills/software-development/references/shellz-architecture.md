# Shellz Architecture Reference

## Estrutura Eterna (v3.0)

```
shellz.rotear(user_input)
  ├── S1_TASKS match? (compilar, loc, git, pytest, ls, install)
  │     ├── SIM → S1 (Ollama, $0.00)
  │     └── NAO → S3 (DeepSeek, $0.30/M)
  └── Telemetry records everything
```

## Files

| File | Purpose |
|------|---------|
| `watchdog/shellz.py` | Core module. Singleton. Auto-init on import. |
| `watchdog/telemetry.py` | Telemetry. Records every interaction. |
| `hermes_loop.py` | Imports shellz. Calls `rotear()` every iteration. |

## Key Decisions (Jun/2026)

1. S3 (DeepSeek) is the MAIN brain. NOT S1.
2. S1 (Ollama) is the WORKER for: compilation, LOC, git, pytest, ls, pip
3. Everything else goes to S3.
4. Model default in config.yaml: deepseek-v4-flash (NOT ollama)
5. telemetry.mini_report() shows per-shell breakdown with real costs
6. NEVER bypass shellz.rotear(). It's eternal.

## Cost Table

| Shell | Provider | Input/M | Output/M |
|-------|----------|:-------:|:--------:|
| S1 | Ollama qwen2.5-coder:7b | $0.00 | $0.00 |
| S3 | DeepSeek V4 Flash | $0.14 | $0.42 |
| S3 (future) | Claude Sonnet 4 | $3.00 | $15.00 |

## Removed

- `watchdog/delegator.py` — replaced by `shellz.py` (2026-06-23)
- Old complexity-based routing — replaced by task-type routing
