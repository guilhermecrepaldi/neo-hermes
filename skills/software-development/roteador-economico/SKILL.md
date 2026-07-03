---
name: roteador-economico
description: "ROTEAMENTO AUTOMÁTICO S3/S2/S1. Integrado ao shellz.py + skill-router. NUNCA perguntar — SEMPRE classificar antes de agir. REGRA ABSOLUTA: verificar antes de afirmar."
category: software-development
tags: [economia, roteamento, automatico, s3, s2, s1, shellz, custo]
---

# Roteador Econômico — AUTOMÁTICO E INTEGRADO

## 🔴 ATIVADO AUTOMATICAMENTE — NÃO PERGUNTAR

Este roteador opera EM SILÊNCIO em TODA sessão.
NUNCA pergunte "quer que eu roteie para S1/S3?"
Simplesmente FAÇA.

## Arquitetura S3 → S2 → S1 (CORRETA)

```
USUÁRIO → AGENTE (classifica automaticamente)
  ├── S3 (DeepSeek V4 Flash — US$ 0.15/1M)
  │   └── Pesquisa web, análise complexa, arquitetura, decisões
  │
  ├── S2 (API Gateway — custo fixo)
  │   └── Requisições à LegiData API, cache, auth, webhooks
  │
  └── S1 (Ollama qwen2.5-coder:7b — US$ 0)
      └── Git, terminal, testes, formatação, compilação, LGPD
```

### Regras de classificação (automáticas, SEMPRE aplicar)

| Tarefa | Rota | Justificativa |
|:-------|:----:|:--------------|
| `git status`, `git add`, `git commit`, `git push` | S1 | Terminal, US$ 0 |
| `pip install`, `npm install` | S1 | Terminal, US$ 0 |
| `ls`, `cd`, `mkdir`, `rm`, `cp`, `mv` | S1 | Terminal, US$ 0 |
| Compilar, build, testar | S1 | Local, US$ 0 |
| Anonimizar texto (LGPD) | S1 | Ollama local, US$ 0 |
| **Qualquer pesquisa web** | **S3** | Requer browser/web tools |
| Análise arquitetural | S3 | Requer inteligência cloud |
| Decisão de design | S3 | Requer raciocínio complexo |
| RAG, resumo, perguntas | S3 | Requer LLM cloud |
| **Chamadas à LegiData API** | **S2** | API Gateway existente |
| Consultar cache | S2 | Redis, S2 |
| Verificar health | S2 | Endpoint S2 |

### Fluxo determinístico

```
1. Recebeu uma solicitação do usuário
2. Classifica ANTES de agir (sem perguntar)
3. Se S1: usa Ollama/terminal diretamente ($0)
4. Se S2: faz requisição à API LegiData (custo fixo)
5. Se S3: usa DeepSeek V4 Flash (US$ 0.15/1M)
6. Sempre inclui footer de custo no final
```

## Footer de custo OBRIGATÓRIO

TODA resposta DEVE terminar com:
```
⚡ [X]K tokens | Régua US$ 1/1M → US$ [Y] | DeepSeek → US$ [Z] | 🏆 Economia: US$ [E]
```

## Integração com shellz.py

O `shellz.py` no watchdog já faz o roteamento S3/S1 automaticamente.
Esta skill garante que o COMPORTAMENTO DA IA siga o mesmo padrão.
Ambos operam em conjunto — shellz roteia no backend, esta skill roteia no frontend.

## REGRA ABSOLUTA: VERIFICAR ANTES DE AFIRMAR

NUNCA afirme algo sem EVIDÊNCIA CONCRETA.
Se não testou com curl/browser, é ACHISMO.

```
✅ FATO: [verificado]
⚠️ INFERÊNCIA: [não testou]
❌ DESCONHECIDO: [não pesquisou]
```
