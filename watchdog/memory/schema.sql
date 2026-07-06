-- ─── Memory Schema ─────────────────────────────────
-- SQLite: fatos estruturados (custo zero de infra)
-- Embeddings via Ollama (custo zero de API)

CREATE TABLE IF NOT EXISTS memory_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    fact_text TEXT NOT NULL,            -- Versão já resumida/comprimida do fato
    source_provider TEXT,
    source_role TEXT,                   -- executor | reviewer | compressor
    importance REAL DEFAULT 0.5,        -- 0-1, decai com o tempo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    embedding BLOB                      -- Vetor float32 serializado (via Ollama)
);

CREATE TABLE IF NOT EXISTS review_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_hash TEXT,                     -- Hash do tipo de tarefa
    approved INTEGER,                   -- 0 ou 1
    reviewer_provider TEXT,
    issues_json TEXT,                   -- JSON array de issues
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    provider_name TEXT,
    role TEXT,                          -- executor | reviewer | compressor | embeddings
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_facts_archive (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    fact_text TEXT,
    source_provider TEXT,
    source_role TEXT,
    importance REAL,
    created_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    access_count INTEGER,
    embedding BLOB,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Tabela de Auditoria V3 ────────────────────────
-- decision_log: registro de cada decisão de roteamento/revisão
-- Criada também em core/audit.py como fallback de segurança
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    task_hash TEXT NOT NULL,
    risk_level TEXT,
    executor_chosen TEXT,
    triggers_evaluated TEXT,            -- JSON: {"G1": false, "G5": true, ...}
    trigger_fired TEXT,                 -- G1 | G2 | G3 | G4 | G5 | cache_approved | none
    needed_review INTEGER,              -- 0 ou 1
    reviewer_chosen TEXT,
    rounds_used INTEGER DEFAULT 0,
    cost_estimated_usd REAL,
    cost_actual_usd REAL,
    latency_ms INTEGER,
    dry_run INTEGER DEFAULT 0,          -- 0=revisão real, 1=dry-run (custo zero)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Índices ───────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_facts_session ON memory_facts(session_id);
CREATE INDEX IF NOT EXISTS idx_facts_importance ON memory_facts(importance DESC);
CREATE INDEX IF NOT EXISTS idx_review_task_hash ON review_outcomes(task_hash);
CREATE INDEX IF NOT EXISTS idx_cost_session ON cost_ledger(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_created ON cost_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_decision_task_hash ON decision_log(task_hash);
CREATE INDEX IF NOT EXISTS idx_decision_created ON decision_log(created_at);
