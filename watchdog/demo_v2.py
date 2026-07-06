"""Demo do Sistema V2 — Orquestrador Multi-API com Revisão Cruzada.
Executa um fluxo completo: roteamento → execução → revisão → memória → custo.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Adiciona watchdog ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))


async def demo_v2():
    print("=" * 60)
    print("  NEO HERMES V2 — Demo do Orquestrador Multi-API")
    print("=" * 60)

    # ─── 1. Provider Layer ──────────────────────────
    print("\n📦 F1: Provider Layer")
    from providers.registry import PROVIDER_REGISTRY, list_providers

    for name, prov in PROVIDER_REGISTRY.items():
        healthy = "✅" if prov.health_check() else "❌"
        roles = ", ".join(prov.supports_roles)
        cost = prov.estimate_cost(1000, 500)
        print(f"  {healthy} {name}: [{roles}] ~${cost:.6f}/1K tok")
        print(f"     {'→ Local (custo $0)' if prov.estimate_cost(0,0) == 0 else '→ API paga'}")

    # ─── 2. Memory Store ────────────────────────────
    print("\n💾 F2+F3: Memory Store (SQLite + Embeddings)")
    from memory.store import MemoryStore

    store = MemoryStore()
    store.add_fact("demo", "Usuário prefere respostas concisas e diretas",
                   source_provider="demo", source_role="executor", importance=0.9)
    store.add_fact("demo", "Regra R1: compressão sempre via Ollama, nunca DeepSeek",
                   source_provider="demo", source_role="executor", importance=0.8)
    store.add_fact("demo", "Cross-review: revisor nunca é o mesmo perfil do executor",
                   source_provider="demo", source_role="executor", importance=0.7)

    facts = store.retrieve_relevant("demo", "como comprimir contexto", top_k=3)
    print(f"  Fatos na memória: {store.get_stats()['facts']}")
    for f in facts:
        print(f"  📌 {f.fact_text[:80]}...")

    # ─── 3. Context Compressor ──────────────────────
    print("\n📉 F4: Context Compressor")
    from memory.compressor import ContextCompressor
    from providers.ollama_provider import OllamaProvider

    compressor = ContextCompressor(OllamaProvider(), token_threshold=500)
    ctx = [
        {"role": "system", "content": "Você é um assistente"},
        {"role": "user", "content": "Olá, tudo bem?"},
        {"role": "assistant", "content": "Tudo ótimo!"},
        {"role": "user", "content": "Preciso de uma explicação detalhada sobre como "
         "implementar um sistema de revisão cruzada entre múltiplos provedores de IA, "
         "com cache de decisão, fallbacks, e métricas de custo. " * 5},
    ]
    compressed = await compressor.compress_if_needed("demo", ctx)
    tokens_antes = sum(len(m.get("content", "")) // 4 for m in ctx)
    tokens_depois = sum(len(m.get("content", "")) // 4 for m in compressed)
    economia = tokens_antes - tokens_depois
    pct = (economia / tokens_antes * 100) if tokens_antes else 0
    print(f"  Tokens: {tokens_antes} → {tokens_depois} ({pct:.0f}% redução)")

    # ─── 4. Cross-Review Council ────────────────────
    print("\n🔍 F5: Cross-Review Council")
    from core.council import CrossReviewCouncil

    council = CrossReviewCouncil(memory_store=store)

    # Teste 1: resposta de baixa confiança
    should, reason = council.should_review(
        response="Não tenho certeza sobre isso, talvez funcione.",
        task="Implementar autenticação JWT",
        executor_provider="ollama-local",
    )
    print(f"  {'✅' if should else '⬜'} Baixa confiança: revisão necessária → {reason}")

    # Teste 2: resposta confiante
    should, reason = council.should_review(
        response="A implementação segue o RFC 7519 com tokens JWT. "
                 "Usar PyJWT com RS256. Documentação completa.",
        task="Como implementar JWT?",
        executor_provider="deepseek-pro",
    )
    print(f"  {'✅' if should else '⬜'} Confiante+Pro: revisão ignorada → {reason}")

    # Teste 3: parse de JSON com markdown fence
    verdict = council._parse_verdict(
        '```json\n{"approved": true, "confidence": 0.95, '
        '"issues": [], "suggested_fix": null}\n```',
        "deepseek-flash",
    )
    print(f"  {'✅' if verdict.approved else '❌'} Markdown fence parse: "
          f"aprovado={verdict.approved}, confiança={verdict.confidence}")

    # ─── 5. Router V2 ───────────────────────────────
    print("\n🧭 F6: Router Econômico v2")
    from core.router_v2 import RouterV2

    router = RouterV2(memory_store=store, council=council)

    tarefas = [
        ("listar arquivos do diretório", False),
        ("implementar API de pagamento com PCI compliance", False),
        ("refatorar módulo de autenticação", True),
    ]

    for task, critical in tarefas:
        decision = router.decide(task, is_critical=critical)
        risco_icono = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        print(f"  {risco_icono.get(decision.risk_level, '⚪')} {task[:50]}...")
        print(f"     → {decision.provider_name} | risco={decision.risk_level} | "
              f"custo=${decision.cost_estimate:.6f} | "
              f"revisão={'sim' if decision.needs_review else 'não'}")

    # ─── 6. Estatísticas Finais ─────────────────────
    print("\n" + "=" * 60)
    print("  📊 ESTATÍSTICAS FINAIS")
    print("=" * 60)
    stats = store.get_stats()
    print(f"  Fatos na memória: {stats['facts']}")
    print(f"  Revisões registradas: {stats['reviews']}")
    print(f"  Entradas de custo: {stats['cost_entries']}")
    print(f"  Custo total acumulado: ${stats['total_cost_usd']:.6f}")
    print(f"  DB: {stats['db_path']} ({stats['db_size_bytes']} bytes)")

    print("\n" + "=" * 60)
    print("  ✅ SISTEMA V2 OPERACIONAL")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_v2())
