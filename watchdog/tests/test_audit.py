"""Testes da Camada de Auditoria (V3-F1)."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestAuditLogger:
    """Testa DecisionRecord e AuditLogger."""

    def test_decision_record_defaults(self):
        from core.audit import DecisionRecord
        
        rec = DecisionRecord(
            request_id="abc123",
            session_id="test",
            task_hash="hash123",
            risk_level="low",
            executor_chosen="ollama-local",
            triggers_evaluated={"G1": False, "G5": True},
            trigger_fired="G5",
            needed_review=True,
        )
        assert rec.request_id == "abc123"
        assert rec.risk_level == "low"
        assert rec.needed_review is True
        assert rec.rounds_used == 0
        assert rec.cost_actual_usd == 0.0
        assert rec.dry_run is False

    def test_audit_logger_singleton(self):
        from core.audit import AuditLogger
        a1 = AuditLogger()
        a2 = AuditLogger()
        assert a1 is a2

    def test_record_and_query(self):
        from core.audit import AuditLogger, DecisionRecord
        
        audit = AuditLogger()
        
        # Grava decisões
        for i in range(3):
            rec = DecisionRecord(
                request_id=f"req_{i}",
                session_id="audit_test",
                task_hash=f"hash_{i}",
                risk_level="low",
                executor_chosen="ollama-local",
                triggers_evaluated={"G1": False, "G5": True},
                trigger_fired="G5" if i < 2 else "none",
                needed_review=(i < 2),
                cost_estimated_usd=0.001,
                cost_actual_usd=0.0005,
                latency_ms=100 * (i + 1),
            )
            audit.record(rec)
        
        # Query trigger frequency
        freq = audit.query_trigger_frequency(since_days=30)
        assert freq["G5"] >= 2
        assert freq["none"] >= 1

    def test_record_with_dry_run(self):
        from core.audit import AuditLogger, DecisionRecord
        
        audit = AuditLogger()
        rec = DecisionRecord(
            request_id="dry_test",
            session_id="audit_test",
            task_hash="dry_hash",
            risk_level="medium",
            executor_chosen="deepseek-flash",
            triggers_evaluated={"G3": True, "G5": False},
            trigger_fired="G3",
            needed_review=True,
            dry_run=True,
            cost_estimated_usd=0.002,
            cost_actual_usd=0.0,
        )
        audit.record(rec)

    def test_cost_vs_estimate_query(self):
        from core.audit import AuditLogger
        
        audit = AuditLogger()
        stats = audit.query_cost_vs_estimate(since_days=30)
        assert "estimated" in stats
        assert "actual" in stats
        assert "by_role" in stats
        assert "total_calls" in stats
        assert isinstance(stats["estimated"], float)
        assert isinstance(stats["total_calls"], int)

    def test_recent_decisions(self):
        from core.audit import AuditLogger
        
        audit = AuditLogger()
        recent = audit.query_recent_decisions(limit=5)
        assert isinstance(recent, list)
        if recent:
            assert "request_id" in recent[0]
            assert "trigger_fired" in recent[0]
