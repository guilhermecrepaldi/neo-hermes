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

-- ─── Índices ───────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_facts_session ON memory_facts(session_id);
CREATE INDEX IF NOT EXISTS idx_facts_importance ON memory_facts(importance DESC);
CREATE INDEX IF NOT EXISTS idx_review_task_hash ON review_outcomes(task_hash);
CREATE INDEX IF NOT EXISTS idx_cost_session ON cost_ledger(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_created ON cost_ledger(created_at);
