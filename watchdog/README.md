# Neo Hermes — Orquestrador Multi-Agent Determinístico

**Motor de orquestração para múltiplos provedores de IA com revisão cruzada, memória externa, compressão de tokens e auditoria.**

---

## Sumário

1. [Arquitetura](#1-arquitetura)
2. [Stack](#2-stack)
3. [Estrutura de Diretórios](#3-estrutura-de-diretórios)
4. [Provider Layer](#4-provider-layer)
5. [Memória Externa](#5-memória-externa)
6. [Context Compressor](#6-context-compressor)
7. [Deterministic Compressor (V3)](#7-deterministic-compressor-v3)
8. [Cross-Review Council](#8-cross-review-council)
9. [Terse Policy (V3)](#9-terse-policy-v3)
10. [Router Econômico](#10-router-econômico)
11. [Auditoria (V3)](#11-auditoria-v3)
12. [Benchmark (V3)](#12-benchmark-v3)
13. [Dashboard (V3)](#13-dashboard-v3)
14. [Feature Flags](#14-feature-flags)
15. [Testes](#15-testes)
16. [Modelo de Custos](#16-modelo-de-custos)
17. [Como Adicionar um Provider](#17-como-adicionar-um-provider)
18. [Roadmap](#18-roadmap)

---

## 1. Arquitetura

```
                 ┌─────────────────────────────┐
                 │     engine.py               │
                 │  processar_tarefa()          │
                 │  ┌─────────────────────┐    │
                 │  │ v3_status()         │    │
                 │  │ feature flags       │    │
                 │  │ use_router_v2: false│    │
                 │  └─────────────────────┘    │
                 └──────────┬──────────────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ shellz.py (V1)   │  │ core/router_v2   │
        │ (fallback)       │  │ RouterV2          │
        └──────────────────┘  └────────┬─────────┘
                                       │
              ┌────────────────────────┼────────────────────┐
              ▼                        ▼                    ▼
   ┌──────────────────┐    ┌──────────────────┐  ┌──────────────────┐
   │ providers/       │    │ memory/store.py  │  │ core/council.py  │
   │ ProviderInterface│    │ MemoryStore      │  │ Council          │
   │ ├ deepseek-flash │    │ (SQLite + emb)   │  │ ├ evaluate_trig  │
   │ ├ deepseek-pro   │    │ cost_ledger      │  │ ├ review()       │
   │ └ ollama-local   │    │ decision_log     │  │ └ dry_run        │
   └──────────────────┘    └──────────────────┘  └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ ops/dashboard.py │
                              │ (relatório)      │
                              └──────────────────┘
```

## 2. Stack

| Componente | Tecnologia | Custo |
|-----------|-----------|-------|
| **Runtime** | Python 3.11+ | $0 |
| **Banco** | SQLite (WAL mode) | $0 |
| **Embeddings** | Ollama (nomic-embed-text / qwen2.5-coder) | $0 |
| **Compressão** | Ollama qwen2.5-coder:7b | $0 |
| **Provider barato** | DeepSeek V4 Flash | $0.15/M input, $0.30/M output |
| **Provider premium** | DeepSeek V4 Pro | $0.55/M input, $2.19/M output |
| **Provider local** | Ollama qwen2.5-coder:7b | $0 |
| **Config** | YAML (sem dependências externas) | $0 |
| **Testes** | pytest 9.x | $0 |

## 3. Estrutura de Diretórios

```
neo-hermes/watchdog/
├── providers/              ← Provider Layer (Interface + adapters)
│   ├── base.py             ← ProviderInterface ABC
│   ├── deepseek_provider.py
│   ├── ollama_provider.py  ← + embeddings
│   └── registry.py
├── memory/                 ← Memória Externa
│   ├── schema.sql          ← SQLite schema (5 tabelas + índices)
│   ├── store.py            ← MemoryStore (singleton)
│   └── compressor.py       ← ContextCompressor
├── core/                   ← Orquestração V2+V3
│   ├── council.py          ← CrossReviewCouncil (evaluate_triggers, dry_run)
│   ├── router_v2.py        ← RouterV2 (audit_logger, config)
│   ├── audit.py            ← AuditLogger + decision_log
│   ├── g5_fires.py         ← Amostragem determinística G5
│   └── config_loader.py    ← YAML loader + deep merge
├── config/                 ← Configuração declarativa
│   ├── providers.yaml      ← Registro de providers
│   └── orchestrator.yaml   ← Feature flags + calibração
├── ops/                    ← Operação/Observabilidade
│   ├── dashboard.py        ← Relatório de custo/saúde
│   └── reload_providers.py ← Hot-reload de providers
├── benchmark/              ← Harness de regressão
│   ├── tasks.json          ← 23 tarefas (10 low, 5 medium, 3 high, 4 traps)
│   ├── run_bench.py        ← Executor do benchmark
│   ├── run_comparison.py   ← Comparação G5 before/after
│   └── results/            ← Resultados timestampados
├── tests/                  ← Testes (35 no total)
│   ├── test_v2_orchestration.py  ← 30 testes (Provider, Memory, Compressor, Council, Router)
│   └── test_audit.py             ← 5 testes (AuditLogger)
└── engine.py               ← Hook V3 com feature flags
```

## 4. Provider Layer

Interface única para todos os provedores de API. Para adicionar um novo: **1 arquivo + 1 registro**, 0 mudanças no core.

```python
class ProviderInterface(ABC):
    name: str
    supports_roles: list[str] = ["executor"]
    
    async def generate(self, req: ProviderRequest) -> ProviderResponse
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float
    def health_check(self) -> bool
    def estimate_tokens(self, text: str) -> int  # len//4 chars
```

**Providers registrados:**

| Nome | Modelo | Custo input/1M | Custo output/1M | Roles |
|------|--------|---------------|----------------|-------|
| `deepseek-flash` | deepseek-v4-flash | $0.15 | $0.30 | executor |
| `deepseek-pro` | deepseek-v4-pro | $0.55 | $2.19 | executor, reviewer |
| `ollama-local` | qwen2.5-coder:7b | $0.00 | $0.00 | executor, reviewer, compressor, embeddings |

## 5. Memória Externa

**MemoryStore** — Singleton. Persistência SQLite em `~/.hermes/memory.db`.

| Método | Descrição |
|--------|-----------|
| `add_fact()` | Insere fato + gera embedding via Ollama |
| `retrieve_relevant()` | Busca top-K por similaridade semântica (cosine) ou keyword fallback |
| `record_review_outcome()` | Registra veredito de revisão |
| `was_previously_approved()` | Cache: tarefa do mesmo tipo já foi aprovada? |
| `record_cost()` | Registra custo no cost_ledger |
| `decay_importance()` | Decai importância de fatos antigos + arquiva obsoletos |

**Ciclo de vida:** importance decai 5%/semana sem acesso. Fatos com importance < 0.1 e access_count = 0 após 30 dias → arquivados.

## 6. Context Compressor

Compressão de contexto **sempre via Ollama local (custo $0)**. Nunca via API paga (regra R1).

| Frente | Quando | Proteção |
|--------|--------|----------|
| `compress_if_needed()` | Antes de enviar ao provider (threshold: 3000 tokens) | Últimas 4 msgs + primeiras 2 sempre preservadas |
| `compress_fact()` | Antes de salvar na memória | Só comprime se texto > 200 chars |

## 7. Deterministic Compressor (V3-F8)

Compressor puramente lógico — **zero LLM, zero custo**. Usa regras determinísticas para comprimir tool outputs, logs, JSON e strings longas sem chamar Ollama ou qualquer API.

| Característica | Descrição |
|---------------|-----------|
| **Custo** | $0 (puro Python, sem API) |
| **Idempotente** | Mesmo input N vezes → mesmo output |
| **Preserva** | Erros, exceções, tracebacks, números, paths |
| **JSON** | Trunca arrays > 20 itens, strings > 8K chars |
| **Logs** | Preserva início (15 linhas) + fim (15 linhas) + linhas com erro ±2 |

```python
from memory.deterministic_compressor import DeterministicCompressor
dc = DeterministicCompressor()

# Comprime JSON longo
compressed = dc.compress_tool_output(json.dumps(big_list))

# Comprime logs preservando erros
compressed = dc.compress_tool_output(log_output)

# Comprime fato para memória
fact = dc.compress_fact(raw_text)
```

**Prioridade de uso:** DeterministicCompressor SEMPRE antes do ContextCompressor (Ollama). Se o determinístico não reduzir o suficiente (>30%), aí chama o Ollama.

## 8. Cross-Review Council

Revisão cruzada entre agentes de diferentes provedores. **Revisor nunca é o mesmo perfil que executou.**

### Gatilhos (avaliados em ordem)

| # | Gatilho | Condição | Ação |
|---|---------|----------|------|
| G1 | Crítica | `is_critical=True` | Sempre revisa |
| G2 | Baixa confiança | Resposta contém "não tenho certeza", "talvez", etc. | Revisa |
| G3 | Resposta curta | `len(task) > 300` e `len(response) < 100` | Revisa |
| G4 | Cache rejeição | `was_previously_approved(task_hash) == False` | Revisa |
| G5 | Executor barato | Provider cheap + `len(task) > 400` + amostra 30% | Revisa (amostra) |

### Pareamento executor → revisor

| Executor | Revisor |
|----------|---------|
| `ollama-local` | `deepseek-flash` |
| `deepseek-flash` | `ollama-local` |
| `deepseek-pro` | `ollama-local` |

### Dry-run

Modo `dry_run=True`: loga a decisão de revisão sem chamar o revisor de fato. Custo $0. Use para calibrar antes de ativar.

## 9. Terse Policy (V3-F9)

Política de concisão para outputs de agentes internos. Aplica-se **seletivamente** por papel (reviewer, compressor, executor) — **nunca afeta respostas finais para humanos**.

**Duas frentes:**
1. **Prompt wrapper**: anexa instrução de concisão ao system prompt por papel
2. **Post-processor**: remove saudações, fechamentos, justificativas e texto extra ao redor de JSON

```python
from core.terse_policy import TersePolicy
tp = TersePolicy()

# Wrap prompt: adiciona "Seja CONCISO" ao prompt do revisor
prompt, system = tp.wrap_prompt("Analise isso", role="reviewer")

# Post-process: remove verbosidade da resposta
clean = tp.post_process(resposta_do_revisor, role="reviewer", is_json=True)
```

**Comportamento por papel:**

| Papel | Prompt adicionado | Pós-processamento |
|-------|------------------|-------------------|
| `reviewer` | "Seja CONCISO. Responda APENAS o JSON." | Remove texto antes/depois do JSON |
| `compressor` | "Seja CONCISO. Preserve APENAS números." | Remove saudações/fechamentos |
| `executor` | "Seja direto. Sem introduções." | Remove saudações/fechamentos |

## 10. Router Econômico

Decide como executar cada tarefa baseado em risco e custo.

| Risco | Provider | Custo | Uso típico |
|-------|----------|-------|------------|
| **high** | `deepseek-pro` | $0.55/M in + $2.19/M out | Produção, deploy, segurança |
| **medium** | `deepseek-flash` | $0.15/M in + $0.30/M out | Código, análise, API |
| **low** | `ollama-local` | $0.00 | Comandos locais, consultas |

## 11. Auditoria (V3)

**AuditLogger** — Singleton. Grava cada decisão de roteamento/revisão em `decision_log` (SQLite aditivo à V2).

```python
@dataclass
class DecisionRecord:
    request_id: str
    session_id: str
    task_hash: str
    risk_level: str
    executor_chosen: str
    triggers_evaluated: dict[str, bool]  # {"G1": False, ..., "G5": True}
    trigger_fired: str                   # G1 | G2 | G3 | G4 | G5 | cache_approved | none
    needed_review: bool
    reviewer_chosen: str | None
    rounds_used: int
    cost_estimated_usd: float
    cost_actual_usd: float
    latency_ms: int
    dry_run: bool
```

**Queries de auditoria:**
- `query_trigger_frequency(since_days=7)` — frequência de cada gatilho
- `query_cost_vs_estimate(since_days=7)` — estimado vs real, por papel
- `query_recent_decisions(limit=20)` — últimas N decisões

## 12. Benchmark (V3)

Harness determinístico de regressão. 23 tarefas fixas em `benchmark/tasks.json`.

```
10 trivial    (low risk, sem armadilha)
5  code       (medium risk, sem armadilha)
3  critical   (high risk, sem armadilha)
4  trap       (low risk, COM erro plantado)
1  decoy      (low risk, resposta correta)
```

**Uso:**
```bash
# Benchmark completo com dry-run
python benchmark/run_bench.py

# Comparação G5 before/after
python benchmark/run_comparison.py
```

**Resultados salvos em:** `benchmark/results/g5_before.json` e `g5_after.json`

## 13. Dashboard (V3)

Relatório de custo, gatilhos e saúde. Fonte de verdade para decisões de ativação.

```bash
python ops/dashboard.py --days 7
```

**Saída:** custo por papel, frequência de gatilhos (com barras visuais), estatísticas da memória, últimas decisões.

## 14. Feature Flags

Controladas por `config/orchestrator.yaml`. **Todas desligadas por default** — zero mudança de comportamento até você ativar.

| Flag | Default | O que controla |
|------|---------|----------------|
| `use_router_v2` | `false` | engine.py usa RouterV2.execute() |
| `use_cross_review` | `false` | Council ativo (revisão real) |
| `dry_run_review` | `true` | Council loga sem chamar revisor |
| `use_memory_v2` | `true` | MemoryStore ativo (já é aditivo, seguro ligar) |
| `use_compression` | `true` | ContextCompressor ativo |
| `audit_enabled` | `true` | AuditLogger sempre ligado (observação) |

**Plano de rollout recomendado:**

| Passo | Flag | Validação |
|-------|------|-----------|
| 1 | `use_memory_v2: true` | MemoryStore.get_stats() crescendo |
| 2 | `use_compression: true` | tokens_in médio caindo |
| 3 | `use_router_v2: true`, review off | Custo ≈ igual ao shellz antigo |
| 4 | `dry_run_review: true` (3-7 dias) | AuditLogger: quanto custaria |
| 5 | `use_cross_review: true`, dry_run off | Monitorar cost_ledger diariamente |

## 15. Testes

**89 testes, todos passando:**

```
tests/test_v2_orchestration.py  → 30 testes (5 classes)
  ├── TestProviderLayer         →  6 testes
  ├── TestMemoryStore           →  8 testes
  ├── TestContextCompressor     →  3 testes
  ├── TestCouncil               →  8 testes (inclui g5_sample_rate_distribution)
  └── TestRouterV2              →  5 testes

tests/test_audit.py             →  5 testes (AuditLogger)

tests/test_f8_f9.py             → 24 testes (F8+F9)
  ├── TestDeterministicCompressor  → 12 testes
  └── TestTersePolicy              → 12 testes
```

```bash
python -m pytest tests/ -v
```

## 16. Modelo de Custos

| Operação | Custo real | Se fosse API paga | Economia |
|----------|-----------|-------------------|----------|
| Compressão de contexto | $0 (Ollama) | $0.15/M (DeepSeek) | 100% |
| Embeddings | $0 (Ollama) | $0.10/M (OpenAI ada) | 100% |
| Revisão ollama→flash | $0.15/M (já existente) | $0.15/M | Custo já existe |
| Revisão flash→ollama | $0 (Ollama) | $0.15/M (DeepSeek) | 100% |
| Revisão pro→ollama | $0 (Ollama) | $0.15/M (DeepSeek) | 100% |

**Regras de operação (imutáveis):**
- **R1:** Compressão SEMPRE via Ollama. Nunca DeepSeek.
- **R2:** Headroom exterminado (commit 34859e4). Zero proxy.
- **R3:** Revisor NUNCA é o mesmo perfil do executor (tabela de pareamento fixa).
- **R4:** Hard cap de 2 rounds de retry por revisão.

## 17. Como Adicionar um Provider

```python
# 1. Criar o adapter
# providers/meu_provider.py
class MeuProvider(ProviderInterface):
    name = "meu-provider"
    supports_roles = ["executor"]
    
    async def generate(self, req): ...
    def estimate_cost(self, tokens_in, tokens_out): ...
    def health_check(self): ...

# 2. Registrar no registry
# providers/registry.py
PROVIDER_REGISTRY["meu-provider"] = MeuProvider(...)

# 3. Opcional: configurar pareamento
# config/orchestrator.yaml
pairing_defaults:
  meu-provider: ollama-local

# 4. Hot-reload sem restart
python -c "from ops.reload_providers import reload_from_yaml; print(reload_from_yaml())"
```

## 18. Roadmap

| Prioridade | O quê | Status |
|-----------|-------|--------|
| P0 | Auditoria: core/audit.py + decision_log | ✅ V3-F1 |
| P1 | engine.py hook com feature flags | ✅ V3-F4 |
| P2 | Dry-run formal do Council | ✅ V3-F5 |
| P3 | Dashboard de custo por papel | ✅ V3-F6 |
| P4 | Hot-reload de providers.yaml | ✅ V3-F7 |
| P5 | sqlite-vec (quando fatos > 50K) | ⏳ Gatilho |
| — | Calibração G5: min_task_len 150→400, sample_rate 0.3 | ✅ V3-F2 |
| — | Benchmark determinístico com 23 tarefas | ✅ V3-F3 |
| — | Teste de distribuição G5 (200 hashes, margem 20-40%) | ✅ |
| — | DeterministicCompressor (F8) — zero LLM, zero custo | ✅ |
| — | TersePolicy (F9) — concisão por papel, sem afetar humanos | ✅ |
| — | 89/89 testes passando (V2+V3+F8+F9) | ✅ |

---

*Neo Hermes V3 — 2026-07-06 — 89/89 testes — $0 de custo de infraestrutura*
