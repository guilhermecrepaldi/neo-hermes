"""Benchmark determinístico do Neo Hermes.
Executa tasks.json contra o RouterV2, coleta métricas, salva resultado.
Cada rodada é auditável: salva JSON timestampado em results/.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Adiciona watchdog ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.audit import AuditLogger, DecisionRecord
from core.router_v2 import RouterV2
from memory.store import MemoryStore

BENCH_DIR = Path(__file__).parent
TASKS_FILE = BENCH_DIR / "tasks.json"
RESULTS_DIR = BENCH_DIR / "results"


def load_tasks() -> list[dict]:
    """Carrega tasks.json."""
    with open(TASKS_FILE, encoding="utf-8") as f:
        return json.load(f)


def summarize(executor_output: list, elapsed: float, audit_stats: dict) -> dict:
    """Compila resultados do benchmark."""
    total = len(executor_output)
    traps = [t for t in executor_output if t.get("is_trap")]
    traps_detected = [t for t in traps if t.get("council_rejected")]
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "total_tasks": total,
        "by_risk": {},
        "traps_total": len(traps),
        "traps_detected": len(traps_detected),
        "trap_detection_rate": round(len(traps_detected) / max(len(traps), 1) * 100, 1),
        "total_cost_usd": 0.0,
        "total_latency_ms": 0,
        "decisions": [],
    }
    
    for t in executor_output:
        risk = t.get("risk", "unknown")
        summary["by_risk"][risk] = summary["by_risk"].get(risk, 0) + 1
        summary["total_cost_usd"] += t.get("cost_usd", 0)
        summary["total_latency_ms"] += t.get("latency_ms", 0)
        summary["decisions"].append({
            "id": t.get("id"),
            "risk": risk,
            "provider": t.get("provider", ""),
            "needed_review": t.get("needed_review", False),
            "review_approved": t.get("council_approved", True),
            "rounds": t.get("rounds", 0),
            "cost_usd": t.get("cost_usd", 0),
            "latency_ms": t.get("latency_ms", 0),
        })
    
    if audit_stats:
        summary["audit"] = audit_stats
    
    return summary


def save_result(summary: dict) -> Path:
    """Salva resultado em results/ com timestamp."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"bench_{ts}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return path


async def run_benchmark(session_id: str = "benchmark",
                         use_review: bool = False,
                         dry_run: bool = True,
                         label: str = "") -> dict:
    """Executa o benchmark completo.
    
    Args:
        session_id: Sessão para isolar no cost_ledger
        use_review: Se true, ativa revisão real (custo real)
        dry_run: Se true, revisão em modo dry-run (custo zero)
        label: Rótulo opcional para o resultado
    
    Returns:
        Dict com resultados do benchmark
    """
    tasks = load_tasks()
    store = MemoryStore()
    audit = AuditLogger()
    router = RouterV2(memory_store=store)
    
    from core.council import CrossReviewCouncil
    council = CrossReviewCouncil(memory_store=store, dry_run=dry_run)
    router.council = council
    
    results = []
    start = time.time()
    
    for task_data in tasks:
        task_id = task_data["id"]
        task_text = task_data["task"]
        is_trap = task_data.get("is_trap", False)
        
        t0 = time.time()
        decision = router.decide(task_text, is_critical=(task_data["expected_risk"] == "high"))
        
        # Se for armadilha, anexa o erro plantado
        if is_trap:
            task_text = f"{task_text}\n\n{task_data.get('planted_error', '')}"
        
        result = await router.execute(
            task_text,
            session_id=session_id,
            is_critical=(task_data["expected_risk"] == "high"),
        )
        
        elapsed = int((time.time() - t0) * 1000)
        
        verdict = result.get("verdict", {})
        council_rejected = not verdict.get("approved", True)
        
        row = {
            "id": task_id,
            "risk": task_data["expected_risk"],
            "is_trap": is_trap,
            "provider": result.get("decision", {}).get("provider", ""),
            "needed_review": result.get("decision", {}).get("needed_review", False),
            "council_approved": verdict.get("approved", True),
            "council_rejected": council_rejected,
            "rounds": verdict.get("rounds", 0),
            "cost_usd": result.get("cost", {}).get("usd", 0),
            "latency_ms": elapsed,
        }
        results.append(row)
    
    elapsed = time.time() - start
    audit_stats = {}
    try:
        audit_stats = {
            "trigger_frequency": audit.query_trigger_frequency(since_days=30),
            "cost_vs_estimate": audit.query_cost_vs_estimate(since_days=30),
        }
    except Exception:
        pass
    
    summary = summarize(results, elapsed, audit_stats)
    if label:
        summary["label"] = label
    
    path = save_result(summary)
    summary["saved_to"] = str(path)
    
    return summary


def print_report(summary: dict):
    """Imprime relatório formatado."""
    print(f"\n{'='*60}")
    print(f"  BENCHMARK NEO HERMES")
    print(f"  {summary.get('label', 'sem rótulo')}")
    print(f"  {summary['timestamp']}")
    print(f"{'='*60}")
    print(f"  Duração: {summary['elapsed_seconds']}s")
    print(f"  Total de tarefas: {summary['total_tasks']}")
    print(f"  Por risco: {summary['by_risk']}")
    print(f"  Armadilhas: {summary['traps_detected']}/{summary['traps_total']} detectadas "
          f"({summary['trap_detection_rate']}%)")
    print(f"  Custo total: ${summary['total_cost_usd']:.6f}")
    print(f"  Latência média: {summary['total_latency_ms']//max(summary['total_tasks'],1)}ms")
    print(f"  Salvo em: {summary.get('saved_to', 'N/A')}")
    print(f"{'='*60}\n")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark Neo Hermes V3")
    parser.add_argument("--review", action="store_true", help="Ativa revisão real")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Modo dry-run (default)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Desativa dry-run")
    parser.add_argument("--label", default="", help="Rótulo para o resultado")
    args = parser.parse_args()
    
    summary = await run_benchmark(
        use_review=args.review,
        dry_run=args.dry_run,
        label=args.label or f"review={'on' if args.review else 'off'}_dry={'on' if args.dry_run else 'off'}",
    )
    print_report(summary)
    return 0


if __name__ == "__main__":
    asyncio.run(main())
