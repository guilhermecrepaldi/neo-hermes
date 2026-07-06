# Verificação do Token Compressor

## Status do compressor

```bash
# Verificar status (cache, modelo, threshold)
python3 /d/projetos/hermes-watchdog/compressor_local.py --status

# Teste rápido com texto pequeno (deve passar direto <500 tok)
echo "texto curto" | python3 /d/projetos/hermes-watchdog/compressor_local.py

# Teste com force (ignora threshold, comprime sempre)
python3 -c "
import sys; sys.path.insert(0, '/d/projetos/hermes-watchdog')
from compressor_local import comprimir_contexto
r = comprimir_contexto('texto grande... ' * 100, force=True)
print(f'{r[\"tokens_antes\"]} → {r[\"tokens_depois\"]} tok | {r[\"economia_pct\"]}% | engine: {r[\"engine\"]}')
"
```

## Verificar que está pinned

```bash
grep "pinned" /c/Users/Home/AppData/Local/hermes/config.yaml
# Deve mostrar: pinned: '["token-compressor"]'
```

## Verificar que Ollama está rodando

```bash
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['name']) for m in d['models']]"
```

## Economia esperada

| Métrica | Valor |
|---------|-------|
| Threshold mínimo | 500 tokens |
| Economia típica (texto grande) | ~73% |
| Cache TTL | 7 dias |
| Latência com cache | 0ms |
| Latência sem cache (5K chars) | ~8s |
| Engine | Ollama qwen2.5-coder:7b ($0) |
| Fallback (Ollama offline) | Passthrough (sem compressão) |
