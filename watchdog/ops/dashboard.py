"""Dashboard mínimo — relatório de custo, gatilhos e saúde do Neo Hermes.
Roda como: python ops/dashboard.py
Sem dependências de framework web. Fonte de verdade para decisões de ativação.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.audit import AuditLogger
from memory.store import MemoryStore


def print_dashboard(days: int = 7):
    """Imprime relatório de saúde do sistema."""
    audit = AuditLogger()
    store = MemoryStore()
    
    # Custo por role
    cost_stats = audit.query_cost_vs_estimate(since_days=days)
    
    # Frequência de gatilhos
    triggers = audit.query_trigger_frequency(since_days=days)
    
    # Estatísticas da memória
    mem_stats = store.get_stats()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print(f"\n{'='*60}")
    print(f"  NEO HERMES — Relatório de Saúde")
    print(f"  {now}  (últimos {days} dias)")
    print(f"{'='*60}")
    
    # Custo
    print(f"\n📊 CUSTO")
    print(f"{'─'*40}")
    print(f"  Estimado: ${cost_stats['estimated']:.6f}")
    print(f"  Real:     ${cost_stats['actual']:.6f}")
    if cost_stats.get('deviation_pct') is not None:
        icon = "✅" if abs(cost_stats['deviation_pct']) < 20 else "⚠️"
        print(f"  Desvio:   {icon} {cost_stats['deviation_pct']:+.1f}%")
    print(f"  Chamadas: {cost_stats['total_calls']}")
    
    by_role = cost_stats.get('by_role', {})
    if by_role:
        print(f"\n  Por papel:")
        for role, total in sorted(by_role.items()):
            icon = "🆓" if total == 0 else "💰"
            print(f"    {icon} {role}: ${total:.6f}")
    
    # Gatilhos
    total_triggers = sum(triggers.values())
    print(f"\n🔍 GATILHOS (total: {total_triggers})")
    print(f"{'─'*40}")
    g5_dominance = (triggers.get("G5", 0) / max(total_triggers, 1)) * 100
    for name, count in sorted(triggers.items(), key=lambda x: -x[1]):
        pct = (count / max(total_triggers, 1)) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        label = {
            "G1": "Crítico",
            "G2": "Baixa confiança", 
            "G3": "Resposta curta",
            "G4": "Cache rejeição",
            "G5": "Executor barato",
            "cache_approved": "Cache aprovado",
            "none": "Sem revisão",
            "dry_run_skip": "Dry-run pulado",
        }.get(name, name)
        print(f"  {bar} {label}: {count} ({pct:.1f}%)")
    
    print(f"\n  ⚠️  G5 domina {g5_dominance:.0f}% dos disparos — "
          f"{'✅ OK' if g5_dominance < 70 else '⚠️ Pode precisar calibrar'}")
    
    # Memória
    print(f"\n💾 MEMÓRIA")
    print(f"{'─'*40}")
    print(f"  Fatos: {mem_stats['facts']}")
    print(f"  Revisões: {mem_stats['reviews']}")
    print(f"  Entradas de custo: {mem_stats['cost_entries']}")
    print(f"  DB: {mem_stats.get('db_path', '?')}")
    print(f"  Tamanho: {mem_stats.get('db_size_bytes', 0)} bytes")
    
    # Decisões recentes
    recent = audit.query_recent_decisions(limit=5)
    if recent:
        print(f"\n📋 ÚLTIMAS DECISÕES")
        print(f"{'─'*40}")
        for d in recent:
            ts = d.get("created_at", "?")[11:19] if d.get("created_at") else "?"
            trig = d.get("trigger_fired", "?")
            prov = d.get("executor_chosen", "?")
            rev = "🔍" if d.get("needed_review") else "⬜"
            cost = d.get("cost_actual_usd", 0)
            print(f"  [{ts}] {rev} {trig} → {prov} (${cost:.6f})")
    
    print(f"\n{'='*60}")
    print(f"  ✅ Dashboard gerado. Dados do cost_ledger + decision_log.")
    print(f"{'='*60}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dashboard Neo Hermes")
    parser.add_argument("--days", type=int, default=7, help="Período em dias")
    args = parser.parse_args()
    print_dashboard(days=args.days)
    return 0


if __name__ == "__main__":
    main()
