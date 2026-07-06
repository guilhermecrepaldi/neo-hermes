"""MemoryStore — SQLite persistente + busca semântica via embeddings Ollama.
Singleton. Fatos compartilhados entre todos os agentes.
Sobrevive a restarts. Custo zero de infra.
"""
from __future__ import annotations

import json
import os
import sqlite3
import hashlib
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from logger_pro import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    import requests as http_requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ─── Config ─────────────────────────────────────────
DB_PATH = Path.home() / ".hermes" / "memory.db"
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_URL = f"{OLLAMA_BASE}/api/embeddings"

# Import relativo do schema
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@dataclass
class MemoryFact:
    """Um fato armazenado na memória externa."""
    id: int
    session_id: str
    fact_text: str
    source_provider: str = ""
    source_role: str = ""
    importance: float = 0.5
    created_at: str = ""
    last_accessed_at: str = ""
    access_count: int = 0
    embedding: Optional[list] = None


class MemoryStore:
    """Armazenamento persistente de fatos, revisões e custos.
    
    Singleton — uma única instância por processo.
    Usa SQLite (zero infra) + embeddings Ollama (custo zero).
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if MemoryStore._initialized:
            return
        MemoryStore._initialized = True
        self._init_db()
    
    def _init_db(self) -> None:
        """Inicializa banco SQLite com schema."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        
        if SCHEMA_PATH.exists():
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            self._conn.executescript(schema)
            self._conn.commit()
            logger.info(f"MemoryStore pronto: {DB_PATH}")
    
    # ─── Embeddings ─────────────────────────────────
    
    def _get_ollama_embedding(self, text: str) -> list[float]:
        """Gera embedding via Ollama local (custo zero).
        
        Tenta nomic-embed-text, fallback para qwen. Retorna [] se falhar.
        """
        if not HAS_REQUESTS or not text.strip():
            return []
        
        models = ["nomic-embed-text", "qwen2.5-coder:7b"]
        for model in models:
            try:
                resp = http_requests.post(
                    EMBED_URL,
                    json={"model": model, "prompt": text[:2000]},
                    timeout=10,
                )
                if resp.status_code == 200:
                    emb = resp.json().get("embedding", [])
                    if emb:
                        return emb
            except Exception:
                continue
        return []
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Similaridade do cosseno entre dois vetores."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0
    
    def _serialize_embedding(self, emb: list) -> bytes:
        return json.dumps(emb).encode() if emb else b''
    
    def _deserialize_embedding(self, blob: bytes) -> list:
        return json.loads(blob.decode()) if blob else []
    
    # ─── CRUD de Fatos ──────────────────────────────
    
    def add_fact(self, session_id: str, fact_text: str,
                 source_provider: str = "", source_role: str = "",
                 importance: float = 0.5) -> int:
        """Adiciona um fato à memória externa.
        
        Gera embedding automaticamente via Ollama.
        
        Returns:
            ID do fato inserido
        """
        embedding = self._get_ollama_embedding(fact_text)
        now = datetime.now(timezone.utc).isoformat()
        
        cur = self._conn.execute(
            """INSERT INTO memory_facts 
               (session_id, fact_text, source_provider, source_role,
                importance, created_at, last_accessed_at, access_count, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (session_id, fact_text, source_provider, source_role,
             importance, now, now, self._serialize_embedding(embedding))
        )
        self._conn.commit()
        fact_id = cur.lastrowid
        logger.debug(f"Fato #{fact_id}: {fact_text[:60]}...")
        return fact_id
    
    def retrieve_relevant(self, session_id: str, query: str,
                          top_k: int = 5) -> list[MemoryFact]:
        """Busca fatos relevantes por similaridade semântica.
        
        Usa embedding da query para busca por cosseno.
        Fallback: keyword matching se embedding falhar.
        
        Args:
            session_id: Sessão para filtrar
            query: Texto de busca
            top_k: Máximo de resultados
        
        Returns:
            Lista de MemoryFact ordenados por relevância
        """
        query_emb = self._get_ollama_embedding(query)
        
        rows = self._conn.execute(
            """SELECT * FROM memory_facts 
               WHERE session_id = ? 
               ORDER BY importance DESC, access_count DESC 
               LIMIT 50""",
            (session_id,)
        ).fetchall()
        
        scored = []
        for row in rows:
            # Embedding score
            emb = self._deserialize_embedding(row["embedding"])
            if query_emb and emb:
                score = self._cosine_similarity(query_emb, emb)
            else:
                # Fallback: keyword overlap
                qwords = set(query.lower().split())
                fwords = set(row["fact_text"].lower().split())
                score = len(qwords & fwords) / max(len(qwords), 1)
            
            # Bônus por importância e acesso
            score = score * 0.7 + (row["importance"] * 0.2) + min(row["access_count"] / 10, 0.1)
            
            scored.append((score, row))
        
        scored.sort(key=lambda x: -x[0])
        
        results = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for score, row in scored[:top_k]:
            # Atualiza stats de acesso
            self._conn.execute(
                """UPDATE memory_facts 
                   SET access_count = access_count + 1, last_accessed_at = ?
                   WHERE id = ?""",
                (now_iso, row["id"])
            )
            
            fact = MemoryFact(
                id=row["id"], session_id=row["session_id"],
                fact_text=row["fact_text"],
                source_provider=row["source_provider"],
                source_role=row["source_role"],
                importance=row["importance"],
                created_at=row["created_at"],
                last_accessed_at=row["last_accessed_at"],
                access_count=row["access_count"],
            )
            results.append(fact)
        
        self._conn.commit()
        return results
    
    # ─── Revisões ───────────────────────────────────
    
    def record_review_outcome(self, session_id: str, task_hash: str,
                               approved: bool, reviewer_provider: str,
                               issues: list[str]) -> int:
        """Registra resultado de uma revisão cruzada."""
        cur = self._conn.execute(
            """INSERT INTO review_outcomes 
               (session_id, task_hash, approved, reviewer_provider, issues_json)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, task_hash, 1 if approved else 0,
             reviewer_provider, json.dumps(issues))
        )
        self._conn.commit()
        return cur.lastrowid
    
    def was_previously_approved(self, task_hash: str) -> Optional[bool]:
        """Verifica se task similar já foi revisada.
        
        Returns:
            True se aprovada, False se rejeitada, None se sem histórico
        """
        row = self._conn.execute(
            """SELECT approved FROM review_outcomes 
               WHERE task_hash = ? ORDER BY created_at DESC LIMIT 1""",
            (task_hash,)
        ).fetchone()
        return bool(row["approved"]) if row else None
    
    # ─── Cost Ledger ────────────────────────────────
    
    def record_cost(self, session_id: str, provider_name: str, role: str,
                     tokens_in: int, tokens_out: int, cost_usd: float) -> int:
        """Registra custo de uma chamada."""
        cur = self._conn.execute(
            """INSERT INTO cost_ledger 
               (session_id, provider_name, role, tokens_in, tokens_out, cost_usd)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, provider_name, role, tokens_in, tokens_out, cost_usd)
        )
        self._conn.commit()
        return cur.lastrowid
    
    # ─── Manutenção ─────────────────────────────────
    
    def decay_importance(self, rate: float = 0.05, max_days: int = 30) -> dict:
        """Decai importância de fatos não acessados e arquiva obsoletos."""
        # Decai importance
        self._conn.execute(
            """UPDATE memory_facts 
               SET importance = MAX(0.01, importance * (1 - ?))
               WHERE last_accessed_at < datetime('now', ? || ' days')""",
            (rate, f"-{max_days // 2}")
        )
        
        # Arquiva fatos irrelevantes
        self._conn.execute("""
            INSERT OR IGNORE INTO memory_facts_archive 
            SELECT *, datetime('now') FROM memory_facts 
            WHERE importance < 0.1 AND access_count = 0 
              AND last_accessed_at < datetime('now', '-30 days')
        """)
        
        archived = self._conn.execute("""
            DELETE FROM memory_facts 
            WHERE importance < 0.1 AND access_count = 0 
              AND last_accessed_at < datetime('now', '-30 days')
        """).rowcount
        
        self._conn.commit()
        
        remaining = self._conn.execute(
            "SELECT COUNT(*) FROM memory_facts"
        ).fetchone()[0]
        
        logger.info(f"Memory decay: {archived} arquivados, {remaining} restantes")
        return {"archived": archived, "remaining": remaining}
    
    def get_stats(self) -> dict:
        """Estatísticas da memória."""
        facts = self._conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]
        reviews = self._conn.execute("SELECT COUNT(*) FROM review_outcomes").fetchone()[0]
        costs = self._conn.execute("SELECT COUNT(*) FROM cost_ledger").fetchone()[0]
        total_cost = self._conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM cost_ledger"
        ).fetchone()[0]
        
        return {
            "facts": facts,
            "reviews": reviews,
            "cost_entries": costs,
            "total_cost_usd": round(total_cost, 6),
            "db_path": str(DB_PATH),
            "db_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        }
