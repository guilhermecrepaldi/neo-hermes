# Delegator — Delegacao Inteligente com Telemetria

## Arquivo: watchdog/delegator.py

### Decisao por Complexidade

Complexity 1-5:  S1_local  (Ollama qwen2.5-coder:7b, $0)
Complexity 6-8:  S2_cheap  (DeepSeek v4-flash, ~$0.30/M)
Complexity 9-10: S3_premium (Claude Sonnet 4, ~$12/M)

### Uso no Hermes Loop

from delegator import delegator
dec = delegator.delegar(user_input, funcao=shell_name)
telemetry.record(
    user_input=user_input,
    shell_used=dec.shell,
    model_used=dec.model,
    provider=dec.provider,
    complexity=dec.complexity,
)

### Tabela de Precos

ollama:    $0.00 (local)
deepseek:  $0.14/M input, $0.42/M output
openrouter:$0.15/M input, $0.60/M output

### SHELL_TIERS

S1_local, S1  -> local (gratis)
S2_cheap, S2  -> cloud (pago)
S3_premium, S3, S1_nuvem -> cloud (pago)
