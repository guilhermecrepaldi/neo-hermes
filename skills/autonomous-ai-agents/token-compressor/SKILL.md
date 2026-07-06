---
name: token-compressor
description: Compressão obrigatória de contexto via Ollama local para reduzir billing da API. Aplicado em toda sessão, global, eterno.
pinned: true
load_order: 1
---

# Token Compressor — Obrigatório em TODAS as sessões

## ⚠️ REGRA DE FERRO

**TODO contexto grande (acima de ~500 tokens) DEVE ser comprimido via Ollama local ANTES de qualquer chamada de API paga (DeepSeek, etc.).**

Isso é OBRIGATÓRIO. Sempre. Em toda sessão. Para sempre.

## Como usar

O compressor está em `/d/projetos/hermes-watchdog/compressor_local.py`

### Via terminal (pipe):

```bash
echo "texto longo aqui..." | python3 /d/projetos/hermes-watchdog/compressor_local.py
```

### Via Python (import):

```python
import sys
sys.path.insert(0, '/d/projetos/hermes-watchdog')
from compressor_local import comprimir_contexto

resultado = comprimir_contexto(texto_grande)
texto_comprimido = resultado["comprimido"]
# resultado["economia_pct"] mostra economia
# resultado["engine"] mostra "ollama", "cache" ou "passthrough"
```

### Para comprimir mensagens de conversa:

```python
from compressor_local import comprimir_mensagens
mensagens_comprimidas = comprimir_mensagens(mensagens_originais)
```

### Status:

```bash
python3 /d/projetos/hermes-watchdog/compressor_local.py --status
```

## Comportamento

| Cenário | Ação |
|---------|------|
| Texto < 500 tokens | Passa direto (sem custo, sem latência) |
| Texto >= 500 tokens | Comprime via Ollama qwen2.5-coder:7b (~73% economia) |
| Cache hit | Usa cache (~7 dias) — zero latência |
| Ollama offline | Passa direto com motivo "erro: ..." |
| Modo force (`force=True`) | Ignora threshold, comprime sempre |

## Exemplo de uso na sessão

Antes de enviar um bloco grande de contexto para o DeepSeek:

1. Capture o texto do contexto
2. Passe pelo `comprimir_contexto()`
3. Use o resultado `["comprimido"]` no lugar do original
4. Reporte a economia no footer de custo

## Verificação

Sempre que possível, inclua no final da resposta:
`⚡ [X]k tokens | Régua US$ 1/1M → US$ [Y] | DeepSeek → US$ [Z] | Cache → US$ [W] | 🏆 Economia: US$ [E]`

E também:
`⚡ Compressor: [X] → [Y] tok ([Z]% economia) | Engine: [ollama|cache]`

Isso permite auditoria de economia de tokens e custo total da sessão.

## Referências

- `references/verify.md` — Comandos de verificação, teste de performance, configuração pinned
- `/d/projetos/hermes-watchdog/compressor_local.py` — Script do compressor (Python)
