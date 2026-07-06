"""AuditLogger — Camada de auditoria de decisões do orquestrador.
Grava cada decisão de roteamento/revisão em `decision_log` (SQLite).
Nunca lança exceção que interrompa o fluxo principal.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from logger_pro import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


DB_PATH = Path.home() / ".hermes" / "memory.db"


@dataclass
class DecisionRecord:
    """Registro completo de uma decisão de roteamento."""
    request_id: str
    session_id: str
    task_hash: str
    risk_level: str                          # low | medium | high
    executor_chosen: str
    triggers_evaluated: dict[str, bool]      # {"G1": False, "G2": False, ..., "G5": True}
    trigger_fired: str                       # qual gatilho decidiu (ou "cache_approved" / "none")
    needed_review: bool
    reviewer_chosen: Optional[str] = None
    rounds_used: int = 0
    cost_estimated_usd: float = 0.0
    cost_actual_usd: float = 0.0
    latency_ms: int = 0
    dry_run: bool = False
    created_at: str = ""


class AuditLogger:
    """Singleton — escreve em decision_log. Falha silenciosa: nunca interrompe o fluxo.
    
    Uso:
        audit = AuditLogger()
        audit.record(DecisionRecord(...))
        
        stats = audit.query_trigger_frequency(since_days=7)
        cost_stats = audit.query_cost_vs_estimate(since_days=7)
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if AuditLogger._initialized:
            return
        AuditLogger._initialized = True
        self._init_db()
    
    def _init_db(self) -> None:
        """Adiciona tabela decision_log ao SQLite existente (schema aditivo)."""
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(DB_PATH))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    task_hash TEXT NOT NULL,
                    risk_level TEXT,
                    executor_chosen TEXT,
                    triggers_evaluated TEXT,
                    trigger_fired TEXT,
                    needed_review INTEGER,
                    reviewer_chosen TEXT,
                    rounds_used INTEGER DEFAULT 0,
                    cost_estimated_usd REAL,
                    cost_actual_usd REAL,
                    latency_ms INTEGER,
                    dry_run INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_task_hash ON decision_log(task_hash)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_created ON decision_log(created_at)")
            self._conn.commit()
            logger.info("AuditLogger pronto: decision_log ativo")
        except Exception as e:
            logger.error(f"AuditLogger falhou ao inicializar DB: {e}")
            self._conn = None
    
    def _request_id(self) -> str:
        """Gera UUID único para correlação com cost_ledger."""
        return uuid.uuid4().hex[:16]
    
    def record(self, decision: DecisionRecord) -> None:
        """Grava uma decisão. Falha silenciosa — auditoria não pode quebrar o fluxo."""
        if self._conn is None:
            return
        
        if not decision.request_id:
            decision.request_id = self._request_id()
        if not decision.created_at:
            decision.created_at = datetime.now(timezone.utc).isoformat()
        
        try:
            self._conn.execute(
                """INSERT INTO decision_log 
                   (request_id, session_id, task_hash, risk_level, executor_chosen,
                    triggers_evaluated, trigger_fired, needed_review, reviewer_chosen,
                    rounds_used, cost_estimated_usd, cost_actual_usd, latency_ms, dry_run)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.request_id, decision.session_id,
                    decision.task_hash, decision.risk_level,
                    decision.executor_chosen,
                    json.dumps(decision.triggers_evaluated),
                    decision.trigger_fired,
                    1 if decision.needed_review else 0,
                    decision.reviewer_chosen or "",
                    decision.rounds_used,
                    decision.cost_estimated_usd,
                    decision.cost_actual_usd,
                    decision.latency_ms,
                    1 if decision.dry_run else 0,
                )
            )
            self._conn.commit()
        except Exception as e:
            logger.warning(f"AuditLogger.record() falhou (segue fluxo): {e}")
    
    def query_trigger_frequency(self, since_days: int = 7) -> dict[str, int]:
        """Retorna quantas vezes cada gatilho disparou nos últimos N dias.
        
        Returns:
            {"G1": 5, "G2": 12, "G3": 0, "G4": 3, "G5": 45, "cache_approved": 20, "none": 100}
        """
        result = {
            "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0,
            "cache_approved": 0, "none": 0, "dry_run_skip": 0,
        }
        if self._conn is None:
            return result
        
        try:
            rows = self._conn.execute(
                """SELECT trigger_fired, COUNT(*) as cnt 
                   FROM decision_log 
                   WHERE created_at >= datetime('now', ? || ' days')
                   GROUP BY trigger_fired""",
                (f"-{since_days}",)
            ).fetchall()
            for row in rows:
                result[row["trigger_fired"]] = row["cnt"]
        except Exception as e:
            logger.warning(f"query_trigger_frequency falhou: {e}")
        
        return result
    
    def query_cost_vs_estimate(self, since_days: int = 7) -> dict:
        """Compara custo estimado vs real agregado.
        
        Returns:
            {"estimated": 0.50, "actual": 0.48, "deviation_pct": -4.0, 
             "by_role": {"executor": 0.45, "reviewer": 0.03, "compressor": 0.0},
             "total_calls": 150}
        """
        result = {
            "estimated": 0.0, "actual": 0.0, "deviation_pct": 0.0,
            "by_role": {}, "total_calls": 0,
        }
        if self._conn is None:
            return result
        
        try:
            # Decision log: estimated vs actual
            row = self._conn.execute(
                """SELECT COALESCE(SUM(cost_estimated_usd), 0) as est,
                          COALESCE(SUM(cost_actual_usd), 0) as act,
                          COUNT(*) as calls
                   FROM decision_log
                   WHERE created_at >= datetime('now', ? || ' days')""",
                (f"-{since_days}",)
            ).fetchone()
            result["estimated"] = round(row["est"], 6)
            result["actual"] = round(row["act"], 6)
            result["total_calls"] = row["calls"]
            if row["est"] > 0:
                result["deviation_pct"] = round(
                    ((row["act"] - row["est"]) / row["est"]) * 100, 2
                )
            
            # Cost ledger: by role
            role_rows = self._conn.execute(
                """SELECT role, COALESCE(SUM(cost_usd), 0) as total
                   FROM cost_ledger
                   WHERE created_at >= datetime('now', ? || ' days')
                   GROUP BY role""",
                (f"-{since_days}",)
            ).fetchall()
            for r in role_rows:
                result["by_role"][r["role"]] = round(r["total"], 6)
        
        except Exception as e:
            logger.warning(f"query_cost_vs_estimate falhou: {e}")
        
        return result
    
    def query_recent_decisions(self, limit: int = 20) -> list[dict]:
        """Últimas N decisões para debug/dashboard."""
        if self._conn is None:
            return []
        try:
            rows = self._conn.execute(
                """SELECT * FROM decision_log 
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []
