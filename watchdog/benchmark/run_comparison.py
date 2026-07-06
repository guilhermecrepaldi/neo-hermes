"""Benchmark comparativo: G5 before (150/1.0) vs after (400/0.3).
Executa tasks.json duas vezes com configs diferentes, salva resultados.
"""
import asyncio, json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.router_v2 import RouterV2
from core.council import CrossReviewCouncil
from memory.store import MemoryStore
from core.audit import AuditLogger
from benchmark.run_bench import load_tasks, save_result


async def run_once(label: str, g5_config: dict, session_id: str) -> dict:
    """Executa benchmark com config G5 específica."""
    store = MemoryStore()
    audit = AuditLogger()
    
    # Council com a calibração exata
    council = CrossReviewCouncil(
        memory_store=store,
        dry_run=False,  # revisão real
        config={"g5_cheap_executor": g5_config},
        audit_logger=audit,
    )
    router = RouterV2(
        memory_store=store, council=council, dry_run=False,
        config={"orchestrator": {"use_cross_review": True, "dry_run_review": False}},
    )
    
    tasks = load_tasks()
    results = []
    start = time.time()
    
    for td in tasks:
        t0 = time.time()
        task_text = td["task"]
        if td.get("is_trap"):
            task_text = f"{task_text}\n\n{td.get('planted_error', '')}"
        
        result = await router.execute(
            task_text,
            session_id=session_id,
            is_critical=(td["expected_risk"] == "high"),
        )
        
        elapsed = int((time.time() - t0) * 1000)
        verdict = result.get("verdict", {})
        
        results.append({
            "id": td["id"],
            "risk": td["expected_risk"],
            "is_trap": td.get("is_trap", False),
            "provider": result.get("decision", {}).get("provider", ""),
            "needed_review": result.get("decision", {}).get("needed_review", False),
            "council_approved": verdict.get("approved", True),
            "council_rejected": not verdict.get("approved", True),
            "cost_usd": result.get("cost", {}).get("usd", 0),
            "latency_ms": elapsed,
        })
    
    elapsed = time.time() - start
    
    # Compila resumo
    traps = [r for r in results if r["is_trap"]]
    traps_detected = [r for r in traps if r["council_rejected"]]
    
    total_cost = sum(r["cost_usd"] for r in results)
    g5_count = sum(1 for r in results if r["needed_review"])
    
    summary = {
        "label": label,
        "g5_config": g5_config,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "total_tasks": len(results),
        "total_cost_usd": round(total_cost, 6),
        "total_g5_triggers": g5_count,
        "traps_total": len(traps),
        "traps_detected": len(traps_detected),
        "trap_detection_rate": round(len(traps_detected) / max(len(traps), 1) * 100, 1),
        "decisions": results,
    }
    
    return summary


async def main():
    print("=" * 60)
    print("  BENCHMARK COMPARATIVO — G5 Before vs After")
    print("=" * 60)
    
    # Rodada 1: calibração ANTIGA (150 chars, 100% amostra)
    print("\n▶ Rodada 1: G5 antigo (min_task_len=150, sample_rate=1.0)...")
    before = await run_once(
        label="G5_150_1.0",
        g5_config={"min_task_len": 150, "sample_rate": 1.0},
        session_id="bench_before",
    )
    before_path = Path(__file__).parent / "results" / "g5_before.json"
    before_path.write_text(json.dumps(before, indent=2, ensure_ascii=False))
    print(f"  Salvo: {before_path}")
    
    # Rodada 2: calibração NOVA (400 chars, 30% amostra)
    print("\n▶ Rodada 2: G5 novo (min_task_len=400, sample_rate=0.3)...")
    after = await run_once(
        label="G5_400_0.3",
        g5_config={"min_task_len": 400, "sample_rate": 0.3},
        session_id="bench_after",
    )
    after_path = Path(__file__).parent / "results" / "g5_after.json"
    after_path.write_text(json.dumps(after, indent=2, ensure_ascii=False))
    print(f"  Salvo: {after_path}")
    
    # Comparação
    print(f"\n{'='*60}")
    print(f"  COMPARAÇÃO")
    print(f"{'='*60}")
    print(f"{'Métrica':<35} {'Antes (150/1.0)':<20} {'Depois (400/0.3)':<20}")
    print(f"{'-'*35} {'-'*20} {'-'*20}")
    print(f"{'G5 triggers':<35} {before['total_g5_triggers']:<20} {after['total_g5_triggers']:<20}")
    print(f"{'Custo total (USD)':<35} ${before['total_cost_usd']:<18.6f} ${after['total_cost_usd']:<18.6f}")
    print(f"{'Armadilhas detectadas':<35} {before['traps_detected']}/{before['traps_total']:<19} {after['traps_detected']}/{after['traps_total']:<19}")
    print(f"{'Taxa de detecção':<35} {before['trap_detection_rate']:<19.1f}% {after['trap_detection_rate']:<18.1f}%")
    print(f"{'Duração':<35} {before['elapsed_seconds']:<19.1f}s {after['elapsed_seconds']:<18.1f}s")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())
