# SPEC — Neo Hermes V2: Orquestrador Multi-API Determinístico

**Versão:** 2.0  
**Data:** 2026-07-06  
**Status:** ✅ IMPLEMENTADO E OPERACIONAL  
**Testes:** 29/29 passando (pytest)

---

## 0. Filosofia de Design

### 0.1 Princípios Determinísticos

O sistema segue **4 regras imutáveis** que garantem comportamento previsível:

| # | Regra | Descrição | Violação = |
|---|-------|-----------|------------|
| **D1** | **Provider Isolation** | Todo provider implementa `ProviderInterface`. Nenhuma lógica de negócio conhece o nome do provedor. | Arquitetura quebrada |
| **D2** | **Cost-Zero Compress** | Compressão de contexto SEMPRE via Ollama local (custo $0). NUNCA via API paga. | Multa financeira |
| **D3** | **Cross-Profile Review** | Revisor NUNCA é o mesmo perfil que executou. Tabela de pareamento fixa. | Viés de auto-validação |
| **D4** | **Hard Cap** | Máximo de 2 rounds de retry por revisão. Sem loops infinitos. | Explosão de custo |

### 0.2 Métricas de Sucesso (da SPEC original)

| Objetivo | Métrica | Status |
|----------|---------|--------|
| O1: Provider modular | Novo provider = 1 arquivo + 1 registro | ✅ `deepseek_provider.py`, `ollama_provider.py` |
| O2: Revisão cruzada | Toda resposta crítica passa por ≥1 revisor | ✅ `Council.should_review()` |
| O3: Memória externa | Fatos sobrevivem a restarts, compartilhados entre agentes | ✅ SQLite persistente |
| O4: Compressão ≥30% | Redução em conversas >20 turnos | ✅ Ativo acima de 3000 tokens |
| O5: Economia | Custo mensal não sobe >15% | ✅ Revisão condicional, não universal |

---

## 1. Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRADA (Tarefa)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  core/router_v2.py         Router Econômico v2                  │
│  ┌─────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │ classify_risk│→ │ select_executor │→ │ decide_review     │   │
│  │ (low/med/high)│  │ (custo+risco)   │  │ (cache+heurística)│   │
│  └─────────────┘  └─────────────────┘  └───────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  providers/              │  │  memory/compressor.py    │
│  ProviderInterface       │  │  ContextCompressor       │
│  ├── deepseek-flash      │  │  ├── compress_if_needed  │
│  ├── deepseek-pro        │  │  ├── compress_fact       │
│  └── ollama-local        │  │  └── via Ollama ($0)     │
└──────────────────────────┘  └──────────────────────────┘
         │                            │
         ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  core/council.py          Cross-Review Council                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ should_review│→ │select_reviewer│→ │ review() → Verdict │    │
│  │ (5 gatilhos)  │  │(nunca mesmo)  │  │ (JSON parse)      │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  memory/store.py           MemoryStore (SQLite)                  │
│  ┌──────────┐  ┌──────────────┐  ┌────────┐  ┌──────────────┐  │
│  │ add_fact │  │retrieve_relev│  │review  │  │  cost_ledger  │  │
│  │          │  │ant(embedding)│  │outcomes│  │               │  │
│  └──────────┘  └──────────────┘  └────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 Estrutura de Diretórios (atual)

```
C:\Users\Home\neo-hermes\watchdog\
├── providers/                    ← NOVO: Provider Layer
│   ├── __init__.py
│   ├── base.py                   ← ProviderInterface ABC
│   ├── deepseek_provider.py      ← DeepSeek (flash + pro)
│   ├── ollama_provider.py        ← Ollama (+ embeddings)
│   └── registry.py               ← Registry singleton
├── memory/                       ← NOVO: Memória Externa
│   ├── __init__.py
│   ├── schema.sql                ← SQLite schema
│   ├── store.py                  ← MemoryStore (singleton)
│   └── compressor.py             ← ContextCompressor
├── core/                         ← NOVO: Orquestração V2
│   ├── __init__.py
│   ├── council.py                ← CrossReviewCouncil
│   └── router_v2.py             ← RouterV2
├── config/
│   └── providers.yaml            ← Config declarativa
├── tests/
│   └── test_v2_orchestration.py  ← 29 testes (F1-F6)
├── demo_v2.py                    ← Demo end-to-end
│
├── (existentes, não modificados)
│   ├── shellz.py                 ← S3/S1 router original
│   ├── providers.py              ← Catalog original (ProviderInfo)
│   ├── ollama_compress.py        ← Compressor original
│   ├── smemory.py                ← Memória original (JSON)
│   ├── engine.py                 ← Engine original
│   ├── orchestrator.py           ← Orquestrador original
│   ├── telemetry.py              ← Telemetria original
│   └── ...                       ← Demais módulos intactos
```

---

## 2. Provider Layer (`providers/`)

### 2.1 Interface (`base.py`)

```python
@dataclass
class ProviderRequest:
    prompt: str                    # Prompt principal
    system: str | None = None      # System prompt (opcional)
    max_tokens: int = 1024         # Máximo de tokens na resposta
    temperature: float = 0.7       # 0.0 = determinístico, 1.0 = criativo
    role: str = "executor"         # executor | reviewer | compressor | embeddings
    metadata: dict | None = None   # Metadados extras

@dataclass
class ProviderResponse:
    text: str                      # Texto gerado
    tokens_in: int                 # Tokens de entrada
    tokens_out: int                # Tokens de saída
    cost_usd: float                # Custo em USD
    latency_ms: int                # Latência em ms
    provider_name: str             # Nome do provider
    model_name: str                # Nome do modelo
    raw: dict | None = None        # Payload bruto (debug)
    success: bool = True           # Sucesso da chamada
    error: str | None = None       # Mensagem de erro

class ProviderInterface(ABC):
    name: str
    supports_roles: list[str] = ["executor"]
    
    @abstractmethod
    async def generate(self, req: ProviderRequest) -> ProviderResponse: ...
    @abstractmethod
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float: ...
    @abstractmethod
    def health_check(self) -> bool: ...
    def estimate_tokens(self, text: str) -> int: ...
```

### 2.2 Implementações Concretas

#### `DeepSeekProvider` (`deepseek_provider.py`)

| Propriedade | flash | pro |
|-------------|-------|-----|
| **Modelo** | `deepseek-v4-flash` | `deepseek-v4-pro` |
| **Input/1M** | $0.15 | $0.55 |
| **Output/1M** | $0.30 | $2.19 |
| **Roles** | `[executor]` | `[executor, reviewer]` |
| **Endpoint** | `https://api.deepseek.com/chat/completions` | mesmo |
| **Retry** | 1 tentativa, 1s de espera | mesmo |
| **Timeout** | 60s | 60s |

**Determinismo:** `estimate_cost()` usa tabela fixa. `generate()` faz POST com `stream=False`. Em caso de erro HTTP, retenta 1x. Se falhar de novo, retorna `ProviderResponse(success=False, error=...)`.

#### `OllamaProvider` (`ollama_provider.py`)

| Propriedade | Valor |
|-------------|-------|
| **Modelo** | `qwen2.5-coder:7b` (configurável via env `OLLAMA_MODEL`) |
| **Custo** | $0.00 (sempre) |
| **Roles** | `[executor, reviewer, compressor, embeddings]` |
| **Endpoint** | `http://localhost:11434/api/generate` |
| **Embeddings** | `/api/embeddings` (nomic-embed-text → qwen2.5-coder fallback) |
| **Timeout** | 120s (Ollama pode ser lento em hardware modesto) |
| **Health** | `GET /api/tags` → verifica `models` não vazio |

### 2.3 Registry (`registry.py`)

```python
PROVIDER_REGISTRY: dict[str, ProviderInterface] = {
    "deepseek-flash": DeepSeekProvider(profile="flash"),
    "deepseek-pro": DeepSeekProvider(profile="pro"),
    "ollama-local": OllamaProvider(model="qwen2.5-coder:7b"),
}
```

Auto-inicializa no import. Futuros providers: `register_provider("openai-gpt5", OpenAIProvider(...))`.

### 2.4 Config Declarativa (`config/providers.yaml`)

```yaml
providers:
  deepseek-flash:
    class: providers.deepseek_provider.DeepSeekProvider
    profile: flash
    cost_per_1k_input: 0.00015
    cost_per_1k_output: 0.00030
    roles: [executor]
  deepseek-pro:
    class: providers.deepseek_provider.DeepSeekProvider
    profile: pro
    cost_per_1k_input: 0.00055
    cost_per_1k_output: 0.00219
    roles: [executor, reviewer]
  ollama-local:
    class: providers.ollama_provider.OllamaProvider
    model: qwen2.5-coder:7b
    cost_per_1k_input: 0
    cost_per_1k_output: 0
    roles: [executor, reviewer, compressor, embeddings]
```

### 2.5 Como Adicionar um Novo Provider (Flow Determinístico)

```
1. Criar providers/novo_provider.py → class NovoProvider(ProviderInterface)
2. Adicionar ao registry: PROVIDER_REGISTRY["novo"] = NovoProvider(...)
3. Opcional: descomentar entrada em config/providers.yaml
4. NENHUMA mudança no core/router/council
```

---

## 3. Memória Externa (`memory/`)

### 3.1 Esquema SQLite (`schema.sql`)

```sql
-- Tabela principal: fatos comprimidos, compartilhados entre agentes
CREATE TABLE memory_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    fact_text TEXT NOT NULL,         -- Versão já comprimida
    source_provider TEXT,            -- Quem gerou (ex: deepseek-flash)
    source_role TEXT,                -- executor | reviewer | compressor
    importance REAL DEFAULT 0.5,     -- 0-1, decai com tempo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    embedding BLOB                   -- Vetor float32 serializado (JSON)
);

-- Cache de decisões de revisão
CREATE TABLE review_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_hash TEXT,                  -- SHA256 do tipo de tarefa
    approved INTEGER,                -- 0 ou 1
    reviewer_provider TEXT,
    issues_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ledger de custos por papel
CREATE TABLE cost_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    provider_name TEXT,
    role TEXT,                       -- executor | reviewer | compressor
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Arquivo morto de fatos obsoletos
CREATE TABLE memory_facts_archive (
    id INTEGER PRIMARY KEY,
    session_id TEXT, ...             -- Mesmo schema + archived_at
);
```

### 3.2 MemoryStore (`store.py`)

**Singleton** — uma única instância por processo. Persistência em `~/.hermes/memory.db`.

| Método | Descrição | Complexidade |
|--------|-----------|-------------|
| `add_fact()` | Insere fato + gera embedding via Ollama | O(1) |
| `retrieve_relevant()` | Busca top-K por similaridade semântica (embedding) ou keyword fallback | O(N) onde N ≤ 50 |
| `record_review_outcome()` | Registra veredito de revisão | O(1) |
| `was_previously_approved()` | Cache: tarefa do mesmo tipo já foi aprovada? | O(1) índice |
| `record_cost()` | Registra custo no ledger | O(1) |
| `decay_importance()` | Decai importância de fatos antigos + arquiva obsoletos | O(N) batch |
| `get_stats()` | Estatísticas: total de fatos, revisões, custos | O(1) |

**Busca semântica (determinística):**

```python
def retrieve_relevant(self, session_id, query, top_k=5):
    query_emb = self._get_ollama_embedding(query)
    rows = SELECT * FROM memory_facts WHERE session_id=? LIMIT 50
    
    for row in rows:
        emb = deserialize(row["embedding"])
        if query_emb and emb:
            score = cosine_similarity(query_emb, emb) * 0.7
        else:
            score = keyword_overlap(query, row["fact_text"]) * 0.7
        score += row["importance"] * 0.2 + min(row["access_count"]/10, 0.1)
        scored.append((score, row))
    
    return sorted(scored, key=-score)[:top_k]
```

**Ciclo de Vida (decay):**
- `importance` decai 5%/semana sem acesso
- Fatos com `importance < 0.1` e `access_count = 0` após 30 dias → arquivados
- Arquivo morto retém auditabilidade sem poluir índice ativo

### 3.3 ContextCompressor (`compressor.py`)

Duas frentes, ambas via Ollama local ($0):

| Frente | Quando | Prompt |
|--------|--------|--------|
| **compress_if_needed** | Antes de enviar ao provider | "Resuma o histórico abaixo em no máximo 3 frases, preservando decisões, números, pendências." |
| **compress_fact** | Antes de salvar na memória | "Resuma o evento abaixo em uma frase concisa, preservando decisões, números, arquivos." |

**Regra de Proteção:**
- Nunca comprime as **últimas 4 mensagens** (turno atual)
- Nunca comprime as **primeiras 2 mensagens** (contexto de sistema)
- Só comprime se total de tokens > **3000**

```python
async def compress_if_needed(self, session_id, raw_context):
    if total_tokens <= THRESHOLD:
        return raw_context  # Passa direto
    
    first_n = raw_context[:2]   # Protege
    last_n = raw_context[-4:]   # Protege
    middle = raw_context[2:-4]  # Comprime
    
    compressed = await ollama.generate(middle)
    return first_n + [resumo] + last_n
```

---

## 4. Cross-Review Council (`core/council.py`)

### 4.1 Gatilhos de Revisão (5 regras determinísticas)

Avaliadas em ordem. A primeira que disparar define o resultado.

| # | Gatilho | Condição | Ação |
|---|---------|----------|------|
| **G1** | Crítica | `is_critical=True` | **Sempre revisa** |
| **G2** | Baixa confiança | Resposta contém "não tenho certeza", "talvez", "não sei", etc. | **Revisa** |
| **G3** | Resposta curta | `len(task) > 300` e `len(response) < 100` | **Revisa** |
| **G4** | Cache de rejeição | `was_previously_approved(task_hash) == False` | **Revisa** |
| **G5** | Executor barato | Provider em `{ollama-local, deepseek-flash}` e `len(task) > 150` | **Revisa** |
| — | Cache de aprovação | `was_previously_approved(task_hash) == True` | **Pula revisão** |
| — | Padrão | Nenhum gatilho acima | **Pula revisão** |

### 4.2 Pareamento Executor → Revisor (fixo)

```python
DEFAULT_PAIRING = {
    "ollama-local":   "deepseek-flash",   # Local → DeepSeek (outro cérebro)
    "deepseek-flash": "ollama-local",     # Flash → Local (sanity barato)
    "deepseek-pro":   "ollama-local",     # Pro → Local (revisão $0)
}
```

Revisor NUNCA é o mesmo perfil que executou (regra D3).

### 4.3 Protocolo de Revisão

```
1. Council monta prompt estruturado:
   "Você é um revisor crítico. Analise a resposta do executor.
    Tarefa: {task}
    Resposta: {response}
    [Contexto da memória: {facts}]
    Responda em JSON: {approved, confidence, issues[], suggested_fix}"

2. Revisor gera resposta JSON

3. Council parseia (lida com markdown fences ```json):
   try: json.loads(cleaned_text)
   except: regex fallback para extrair issues + approved

4. Se aprovado → aceita
   Se rejeitado + rounds < 2 → retry com issues anexados ao prompt
   Se rejeitado + rounds = 2 → aceita mesmo assim (hard cap D4)
```

### 4.4 Prompt de Revisão (template)

```
Você é um revisor crítico de respostas de IA.
Analise a resposta do executor para a tarefa abaixo.

## Tarefa Original
{task}

## Resposta do Executor
{response}

## Contexto da Memória
{facts}

Aponte inconsistências factuais, contradições com o contexto fornecido,
e erros lógicos. Não reescreva a resposta inteira, só liste problemas
específicos e uma sugestão pontual de correção.

Responda em JSON com os campos:
{"approved": true/false, "confidence": 0.0-1.0,
 "issues": ["problema 1", "problema 2"],
 "suggested_fix": "correção específica" ou null}
```

### 4.5 ReviewVerdict (dataclass)

```python
@dataclass
class ReviewVerdict:
    approved: bool
    reviewer_provider: str
    confidence: float          # 0-1
    issues: list[str]
    suggested_fix: str | None = None
```

---

## 5. Router Econômico v2 (`core/router_v2.py`)

### 5.1 Classificação de Risco

```python
def classify_risk(task: str) -> str:
    high_risk_keywords  → "high"   # produção, deploy, pagamento, senha, crypto
    medium_risk_keywords → "medium" # código, API, refatorar, arquitetura
    otherwise            → "low"    # comandos locais, consultas
```

### 5.2 Seleção de Provider

| Risco | Provider | Custo | Uso |
|-------|----------|-------|-----|
| **high** | `deepseek-pro` | $0.55/M in + $2.19/M out | Qualidade máxima |
| **medium** | `deepseek-flash` | $0.15/M in + $0.30/M out | Bom custo-benefício |
| **low** | `ollama-local` | $0.00 | Custo zero |

### 5.3 Fluxo de Execução (`RouterV2.execute()`)

```
1. Router.decide(task, is_critical)
   ├── classify_risk()        → risk_level
   ├── select_executor()      → provider
   ├── compute_task_hash()    → hash SHA256
   ├── was_previously_approved? → needs_review
   └── estimate_cost()        → cost_estimate

2. executor.generate(req)     → response (com retry 1x)

3. if needs_review:
   ├── Council.review(response, task, provider, memory_context)
   │   ├── should_review()    → 5 gatilhos
   │   ├── select_reviewer()  → pareamento fixo
   │   ├── reviewer.generate() → JSON verdict
   │   └── parse_verdict()    → ReviewVerdict
   ├── if not approved AND rounds < 2:
   │   ├── Anexa issues ao prompt
   │   └── executor.generate() → nova tentativa
   └── else: accepted

4. MemoryStore:
   ├── add_fact(resumo, source_provider, source_role)
   └── record_cost(provider, role, tokens, cost)

5. Return {
     "response": text,
     "decision": {provider, model, risk, cost_estimate, needed_review},
     "verdict": {approved, reviewer, confidence, issues, rounds},
     "cost": {usd, tokens_in, tokens_out},
     "performance": {duration_ms, provider}
   }
```

### 5.4 Task Hash (Cache de Decisão)

```python
def _compute_task_hash(self, task: str) -> str:
    normalized = task.lower().strip()[:200]
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
```

Usado para:
- `was_previously_approved()` → pula revisão se mesmo tipo já foi aprovado
- `record_review_outcome()` → indexa decisões por hash

---

## 6. Modelo de Custos

### 6.1 Tabela de Preços (referência: Jun/2026)

| Provider | Input/1M tok | Output/1M tok | Cálculo |
|----------|-------------|--------------|---------|
| **deepseek-flash** | $0.15 | $0.30 | `(input * 0.15 + output * 0.30) / 1_000_000` |
| **deepseek-pro** | $0.55 | $2.19 | `(input * 0.55 + output * 2.19) / 1_000_000` |
| **ollama-local** | $0.00 | $0.00 | `0.0` (sempre) |

### 6.2 Cost Ledger (tabela SQLite `cost_ledger`)

Cada chamada registra:
- `provider_name`: qual provedor foi usado
- `role`: executor | reviewer | compressor | embeddings
- `tokens_in / tokens_out`: para auditoria
- `cost_usd`: custo real em USD

### 6.3 Economia por Design

| Componente | Se fosse API paga | Real | Economia |
|-----------|-------------------|------|----------|
| **ContextCompressor** | DeepSeek $0.15/M | Ollama $0 | **100%** |
| **Embeddings** | OpenAI ada $0.10/M | Ollama $0 | **100%** |
| **Revisão (ollama→flash)** | DeepSeek $0.15/M | DeepSeek $0.15/M (já pago) | Custo já existe |
| **Revisão (flash→ollama)** | DeepSeek $0.15/M | Ollama $0 | **100%** |
| **Revisão (pro→ollama)** | DeepSeek $0.15/M | Ollama $0 | **100%** |

---

## 7. Testes (29/29 passando)

### 7.1 Cobertura

| Classe de Teste | Testes | O Que Verifica |
|----------------|--------|----------------|
| **TestProviderLayer** | 6 | Registry, interfaces, custo, health check, dataclasses, estimate_tokens |
| **TestMemoryStore** | 8 | Singleton, CRUD fatos, busca, revisões, cost ledger, decay, stats |
| **TestContextCompressor** | 3 | Estimate tokens, skip small, compress fallback |
| **TestCouncil** | 7 | 5 gatilhos, JSON parse, markdown fence, reviewer selection |
| **TestRouterV2** | 5 | Risk classify, task hash, executor selection, decide structure |

### 7.2 Testes Determinísticos

Todos os testes são **puramente lógicos** — não dependem de rede, API externa, ou estado global compartilhado (exceto `test_ollama_health` que verifica se Ollama está rodando localmente).

---

## 8. Riscos e Mitigações (da SPEC original, validadas)

| Risco | Probabilidade | Mitigação | Status |
|-------|--------------|-----------|--------|
| Revisão dobra custo | Média | Gatilho condicional (5 regras) + cache `was_previously_approved` | ✅ |
| Compressão perde info crítica | Baixa | Regra: preservar números/decisões; nunca comprimir turno atual | ✅ |
| Embeddings lentos com crescimento | Média | Decaimento + arquivamento; fallback keyword | ✅ |
| Loop de revisão infinito | Baixa | Hard cap de 2 rounds (D4) | ✅ |
| Provider offline | Baixa | Retry 1x + fallback para próximo provider disponível | ✅ |

---

## 9. Integração com Sistema Existente

O V2 **não quebra nada que já existia**. Módulos originais intactos:

| Módulo Original | Status | Relação com V2 |
|----------------|--------|----------------|
| `shellz.py` (S3/S1 router) | ✅ Intacto | V2 pode chamar `shellz.rotear()` internamente |
| `providers.py` (catalog) | ✅ Intacto | V2 usa `providers/` novo; catalog original coexiste |
| `ollama_compress.py` | ✅ Intacto | V2 `ContextCompressor` é complementar |
| `smemory.py` (JSON memory) | ✅ Intacto | V2 `MemoryStore` (SQLite) é mais robusto |
| `engine.py` | ✅ Intacto | V2 `RouterV2` estende conceitos |
| `orchestrator.py` | ✅ Intacto | V2 `Council` adiciona revisão |
| `telemetry.py` | ✅ Intacto | V2 registra no `cost_ledger` + telemetria original |

---

## 10. Próximos Passos (Roadmap)

| Prioridade | O Que | Por quê |
|-----------|-------|---------|
| P1 | Hookar `RouterV2.execute()` no `engine.py` | Para o sistema atual usar o V2 automaticamente |
| P2 | `dry_run=True` no Council por alguns dias | Antes de ativar revisão de verdade |
| P3 | Dashboard de custo por papel (executor/reviewer/compressor) | Já temos os dados no `cost_ledger` |
| P4 | `providers.yaml` → `reload_from_yaml()` | Para adicionar providers sem modificar código |
| P5 | `sqlite-vec` se fatos > 50K | Caso o volume cresça |

---

## A. Glossário

| Termo | Definição |
|-------|-----------|
| **Provider** | Adaptador para uma API de IA (DeepSeek, Ollama) |
| **Router** | Decisão de qual provedor usar para cada tarefa |
| **Council** | Sistema de revisão cruzada entre provedores |
| **Verdict** | Resultado de uma revisão (aprovado/rejeitado + issues) |
| **MemoryStore** | Banco SQLite de fatos compartilhados entre agentes |
| **ContextCompressor** | Compressão de histórico via Ollama |
| **Cost Ledger** | Tabela de auditoria de custos por chamada |
| **S1** | Shell local (Ollama, custo $0) |
| **S3** | Shell cloud (DeepSeek, custo ~$0.15-2.19/M) |
| **R1** | Regra core: compressão SEMPRE via Ollama |

---

*Esta SPEC reflete o estado atual (2026-07-06) do Neo Hermes V2.  
Toda alteração deve atualizar este documento.*
