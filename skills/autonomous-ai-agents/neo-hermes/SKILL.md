---
name: neo-hermes
description: "NEO HERMES — entry point do ecossistema completo. Consolida todas as skills em um pipeline unificado: Auto-Assembly monta workflow, DAG executa paralelo, Conselho de IAs delibera, Hooks envolvem tool calls, Token Budget controla gastos, Auto-Executor valida, Auto-Healing recupera, Taste-Skill garante qualidade, OSS-Absorb gerencia terceiros. Tudo integrado e carregado automaticamente."
category: autonomous-ai-agents
tags: [neo-hermes, entry-point, ecossistema, pipeline, integrado, super-agente]
---

# 🚀 NEO HERMES — Super Agente Autônomo

## Pipeline Unificado

```
                ┌──────────────────────────────────┐
                │         NEO HERMES               │
                │  "O Agente que Evolui com Você"   │
                └──────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ AUTO-ASSEMBLY WORKFLOW  │ ← EvoAgentX (🇨🇳)
              │ "Analisa e monta tudo"  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │    SPEC-AGENT (Spec Kit)│ ← github/spec-kit (114K⭐)
              │ "Constitution → Specify │
              │  → Plan → Tasks → Impl" │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     CONSELHO DE IAS     │ ← Shannon (🇯🇵) + OWL (🇨🇳)
              │ "Delibera antes de agir"│
              │  Arquiteto → Revisor →  │
              │  Executor → Auditor     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      DAG WORKFLOW       │ ← OxiFY (🇯🇵) + DeerFlow (🇨🇳)
              │ "Passos em paralelo"    │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │    HERMES HOOKS         │ ← Claude Code Hooks
              │ "pre/post tool call     │
              │  on-error/on-success"   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     AUTO-EXECUTOR       │ ← Claude Code + Grok Build
              │ "Plan → Execute → Verify│
              │  3 tentativas + loop"   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     AUTO-HEALING        │ ← DeepSeek resiliência
              │ "Fallbacks automáticos" │
              │ "+ on-error hooks"      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   TOKEN BUDGET CONTROL  │ ← Shannon (🇯🇵)
              │ "Orçamento por agente"  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      OUTPUT COESO       │ ← Claude Code + Codex
              │ "Diagnóstico → Ação →   │
              │  Resultado"             │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      TASTE-SKILL        │ ← Auditoria real do Hermes
              │ "Quality Gate: 10 regras│
              │  pre-commit obrigatórias"│
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      OSS-ABSORB         │ ← Pipeline A0→A6
              │ "Absorve OSS com gate de│
              │  licença + attribution" │
              └────────────┬────────────┘
                           │
                           ▼
                  ✅ RESULTADO FINAL
```

## Arquitetura Agentica (Fable 5 Inspired)

A arquitetura do Hermes 2.0 foi reestruturada para seguir o padrao Fable 5 (Claude Code):
**loop simples + harness complexo.**

### Agent Loop (hermes_loop.py) — ~15 linhas de orquestracao

```python
while True:
    user_input = get_input()                    # 1. Entrada
    harness.update_context(user_input)           # 2. Contexto
    action = harness.choose_action(user_input)   # 3. Decisao
    result = harness.execute_action(action)      # 4. Execucao (com validacao)
    harness.update_progress(result)              # 5. Progresso
```

### Harness (watchdog/core.py) — complexidade aqui

| Componente | Responsabilidade |
|-----------|----------------|
| `HermesHarness` | Permissoes, contexto, memoria, tools, roteamento |
| `Action` | Acao com nome, descricao, permissoes requeridas |
| `Context` | Estado da sessao (progress, skills, budget) |
| `HarnessResult` | Resultado com sucesso, summary, actions_taken |
| `SkillLoader` | Carregamento de skills |

### Roteamento Economico

```
TAREFA → Ollama rodando? → classificar_tarefa_local() [$0]
  ├── "codigo/shell/leitura" → S1 (qwen2.5-coder:7b, $0)
  ├── "arquitetura" → S2 (DeepSeek Flash, ~$0.00002)
  └── "pesado" → S3 (DeepSeek Pro, ~$0.00008)
```

95% das tarefas sao classificadas e executadas por IA local antes de tocar em API paga.

### Engine (watchdog/engine.py) — Servicos do Hermes

O engine contem toda a logica auxiliar que nao e loop puro nem harness:

| Componente | Responsabilidade | Metodos |
|-----------|----------------|---------|
| `carregar_progresso()` | Le estado da sessao do hermes-progress.md | retorna dict com feito/pendente/artefatos |
| `salvar_progresso(acao, resultado)` | Registra progresso | escreve no hermes-progress.md |
| `criar_worktree(nome)` | Cria subagent via git worktree | subagents/{nome}/ + branch agent/{nome} |
| `remover_worktree(nome)` | Remove worktree e branch | git worktree remove + branch -D |
| `InitializerAgent.setup()` | Planning e setup | retorna contexto com regras |
| `CodingAgent.plan_and_execute()` | Execucao incremental | gera plan a partir do setup |
| `CheckpointManager.save()` | Salva checkpoint | .hermes/checkpoints/{nome}_{ts}.json |
| `CheckpointManager.list()` | Lista checkpoints | sorted descending |
| `CheckpointManager.auto_compact()` | Remove antigos, mantem 10 | auto a cada 5 acoes |
| `HookManager.register()` | Registra hook pre/post | pre/patch, post/terminal, etc |
| `HookManager.execute()` | Executa hooks | verifica arquivo existe, exit code |
| `HookManager.setup_default()` | Hooks padrao | pre-patch + post-terminal |
| `KVCache.get()` | Le do cache compartilhado | com TTL e expiracao |
| `KVCache.set()` | Escreve no cache | auto-compact quando > 100 entradas |

### Finalizer (watchdog/finalizer.py + finalizer-loop.sh)

Watchdog que verifica e corrige pendencias a cada 2 minutos:

```python
check_pending() → [
  {"type": "test", "fix": "pytest"},        # testes falhando
  {"type": "git", "fix": "commit"},          # arquivos nao commitados
  {"type": "git", "fix": "push"},            # push pendente
  {"type": "code", "fix": "resolve"},        # TODOs reais
  {"type": "ci", "fix": "fix_ci"},           # CI falhou
  {"type": "doc", "fix": "update_spec"},     # SPEC desatualizada
]
```

Uso: `bash finalizer-loop.sh` — loop 2min ate clean.
NUNCA termine task com pendencia sem criar watchdog.

## Skills do Ecossistema

### Autoload (carregadas automaticamente em toda sessão)

| Skill | Função | Inspiração | Criada |
|-------|--------|-----------|--------|
| `token-compressor` | Compressão OBRIGATÓRIA de contexto via Ollama local | billing reduction | Jul/2026 |
| `neo-hermes` | Entry point — este documento | Consolidação total | Jun/2026 |
| `auto-executor` | Loop Plan→Execute→Verify | Claude Code + Grok Build | Jun/2026 |
| `auto-healing` | Fallbacks automáticos | DeepSeek resiliência | Jun/2026 |
| `output-coeso` | Template de resposta | Claude Code + Codex | Jun/2026 |
| `roteador-economico` | DeepSeek 95% das tarefas | Claude Code (Haiku) | Jun/2026 |
| `spec-agent` | Spec-Driven Development | github/spec-kit (114K⭐) | Jun/2026 |
| `taste-skill` | Quality Gate: 10 regras | Auditoria real Hermes 2.0 | Jun/2026 |
- `hermes-hooks` | Hooks pre/post tool call | Claude Code (Anthropic) | Jun/2026 |
- `threejs-benchmark` | Benchmark Three.js (WebGL) — abrir em Chrome, Hermes nao suporta | Teste de renderizacao | Jun/2026 |

### Sob demanda (carregar quando necessário)

| Skill | Função | Inspiração | Criada |
|-------|--------|-----------|--------|
| `auto-assembly-workflow` | Monta workflow automaticamente | EvoAgentX (🇨🇳) | Jun/2026 |
| `conselho-ias` | Deliberação multi-agente | Shannon (🇯🇵) + OWL (🇨🇳) | Jun/2026 |
| `dag-workflow` | Execução paralela em grafo | OxiFY (🇯🇵) + DeerFlow (🇨🇳) | Jun/2026 |
| `token-budget-control` | Orçamento de tokens | Shannon (🇯🇵) | Jun/2026 |
| `oss-absorb` | Pipeline A0→A6 absorção OSS | GitHub Spec-compliant | Jun/2026 |
| `benchmark-neo-hermes` | Benchmark econômico + assertividade | Próprio | Jun/2026 |
| `arquitetura-code-review-loops` | Code review + QA | Google + Nubank | Jun/2026 |
| **`python-reviewer`** 🆕 | Revisão Python (tipos, segurança, perf) | **ECC Python Reviewer** | Jul/2026 |
| **`security-reviewer`** 🆕 | Auditoria segurança (credenciais, LGPD, CVEs) | **ECC AgentShield** | Jul/2026 |
| **`architecture-reviewer`** 🆕 | Análise arquitetural (acoplamento, padrões) | **ECC Arch Agent** | Jul/2026 |
| **`continuous-learning`** 🆕 | Extrai padrões de sessões → skills/memory | **ECC Continuous Learning** | Jul/2026 |

### Estudos e fontes

| Skill | Conteúdo |
|-------|---------|
| `repos-chineses-japoneses-2026` | DeerFlow, OWL, LightAgent, EvoAgentX, Shannon, OxiFY |
| `estudo-concorrentes-hermes` | Claude Code, Antigravity, Grok Build, OpenAI GPT-5 |
| `hermes-arquitetura-melhorias` | Melhorias ARQUITETURA/ECONOMIA/OUTPUT + lições de leaks |
| `fontes-frontend` | Font Awesome, Google Fonts, CodePen, Unsplash |
| `fontes-educacao-tech` | Coddy.Tech + 11 plataformas de educação |
| `fontes-referencia-tech` | W3Schools + MDN + TutorialsPoint + GeeksforGeeks |
| `fontes-auditoria-software` | Eramba, Lynis, Wazuh, OpenVAS + papers |
| `estudo-automacao-instagram` | Postsfy, Buffer, Later, InstaGem vs IG Auto Post |

## Como Usar

**Skills de pipeline já estão em autoload.** Toda sessão nova já nasce com elas.

```bash
# ✅ NADA A FAZER — já carregado:
# neo-hermes, auto-executor, auto-healing, output-coeso,
# roteador-economico, spec-agent, taste-skill, hermes-hooks

# Descreva a tarefa diretamente:
# "Cria uma API de usuários com FastAPI, testa e faz deploy"
```

### Sob demanda (quando a tarefa exigir)

```bash
skill_view(name='auto-assembly-workflow')    # Monta workflow automático
skill_view(name='conselho-ias')              # Deliberação multi-agente
skill_view(name='dag-workflow')              # Passos paralelos em grafo
skill_view(name='oss-absorb')                # Absorver OSS de terceiros
```

### Exemplos de Uso

```
👤 "Cria uma API de usuários com FastAPI, testa e faz deploy"
   → Pipeline autoload detecta: projeto novo
   → Monta: Executor + hooks pre/post → testes → deploy
   → Budget automático: Normal ($0.002)
   → Resultado: API no ar

👤 "Refatora o módulo de pagamentos e adiciona testes"
   → Carregar: skill_view(name='conselho-ias')
   → Conselho (4 papéis) delibera → Executor implementa → Taste-skill valida
   → Resultado: Código refatorado com qualidade gate aprovado

👤 "Absorve este projeto OSS: https://github.com/user/repo"
   → Carregar: skill_view(name='oss-absorb')
   → Pipeline A0→A6: intake → clone → license gate → decision → implement → commit
```

## Economia

A economia e feita por 3 camadas que agem em conjunto:

| Camada | Skill | Funcao | Economia |
|--------|-------|--------|----------|
| 1. Roteamento | `roteador-economico` / Shellz | S1 (Ollama $0) vs S3 (DeepSeek $) | Tarefas simples pagam $0 |
| 2. Compressao input | `headroom` (skill) + `headroom_proxy.py` | Comprime tool outputs 60-95% antes do LLM | Input custa 5-40% do normal |
| 3. Compressao output | Caveman (futuro) | Respostas minimalistas, 65-87% menos tokens | Output custa 13-35% do normal |

| Metrica | Valor |
|---------|-------|
| Custo por tarefa tipica | ~$0.002 |
| Custo diario (20 tarefas) | ~$0.04 |
| Custo mensal | ~$1.20 |
| vs Claude Opus (mesmo volume) | ~$900/mes |
| **Economia** | **~99.87%** |

## Stack Tecnica

```
LLM Padrao:      DeepSeek V4 Flash ($0.15/1M) via Headroom proxy (:8787)
LLM Fallback:    DeepSeek V4 Pro ($0.50/1M) — direto (fallback se proxy cair)
IA Local (S1):   Ollama qwen2.5-coder:7b (58tok/s, $0)
Proxy:           headroom_proxy.py v2 — compressao + SSE streaming + Threading
CLI compressao:  s3_headroom.py — project load, compress, search, map
Output minimize: Caveman (72.8K⭐, nao instalado) — 65-87% output savings
Orquestracao:    delegate_task + Hermes cron
Memoria:         Hermes memory + skills
Spec:            GitHub Spec Kit (specify CLI)
Armazenamento:   GitHub + self-hosted
Hooks:           hermes-hooks (pre/post tool call)
Quality Gate:    taste-skill (10 regras pre-commit)
OSS Compliance:  oss-absorb (license gate A3)
Recovery guide:  hermes-config-essentials.md — 7 passos ~15min se formatar o PC

## Referências

### Anthropic (Claude Code)
- **Effective Harnesses for Long-Running Agents** (Nov/2025): initializer + coding agent pattern, claude-progress.txt, feature list with passing/failing markers
- **Claude Code Autonomy** (Set/2025): checkpoints, hooks, sub-agents, background tasks
- **Programmatic Tool Calling** (Jan/2026): agent writes code to call tools dynamically
- **Claude Agent SDK**: same harness that powers Claude Code, available for custom agents

### 🇨🇳 China
- **DeerFlow** (ByteDance): https://github.com/bytedance/deer-flow — 37K⭐
- **OWL** (CAMEL-AI): https://github.com/camel-ai/owl — 19.9K⭐
- **EvoAgentX**: https://github.com/EvoAgentX/EvoAgentX — 3.1K⭐
- **LightAgent** (wanxingai): https://github.com/wanxingai/LightAgent — 1.1K⭐

### 🇯🇵 Japão
- **Shannon** (Kocoro-lab): https://github.com/Kocoro-lab/Shannon
- **OxiFY** (cool-japan): https://github.com/cool-japan/oxify

### 🇨🇳 China
- **DeerFlow** (ByteDance): https://github.com/bytedance/deer-flow — 37K⭐
- **OWL** (CAMEL-AI): https://github.com/camel-ai/owl — 19.9K⭐
- **EvoAgentX**: https://github.com/EvoAgentX/EvoAgentX — 3.1K⭐
- **LightAgent** (wanxingai): https://github.com/wanxingai/LightAgent — 1.1K⭐

### 🇯🇵 Japão
- **Shannon** (Kocoro-lab): https://github.com/Kocoro-lab/Shannon
- **OxiFY** (cool-japan): https://github.com/cool-japan/oxify

### 🌐 Outros
- **GitHub Spec Kit**: https://github.com/github/spec-kit (114K⭐)
- **Claude Code Leak**: https://github.com/chauncygu/collection-claude-code-source-code
- **System Prompts Leaks**: https://github.com/asgeirtj/system_prompts_leaks (43.3K⭐)
- **Hermes Agent**: https://github.com/NousResearch/hermes-agent

### ⭐ ECC — Agent Harness OS (Jul/2026) 🆕
- **ECC**: https://github.com/affaan-m/ECC — **⭐211.9K**
- **Site oficial**: https://ecc.tools
- **Discord**: https://discord.gg/36yGMHGFbR
- **npm**: `ecc-universal`, `ecc-agentshield`
- **Conceitos absorvidos**:
  - **66 agentes especializados** → criamos `python-reviewer`, `security-reviewer`, `architecture-reviewer`
  - **AgentShield** → criamos `security-reviewer` com scanning de 5 camadas
  - **Hooks avançados** → expandimos `hermes-hooks` com 17 novos hooks (governance, session-end, cost-tracker, mcp-health, gateguard)
  - **Continuous Learning** → criamos `continuous-learning` skill
  - **Memory Persistence** → hooks stop:session-end + stop:cost-tracker
  - **GateGuard** → pre:gateguard-fact-force hook no hermes-hooks
  - **Config Protection** → pre:config-protection hook no hermes-hooks
  - **Verification Loops** → checkpoint + eval hooks expandidos
