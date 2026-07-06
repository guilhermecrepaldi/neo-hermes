"""Testes de Integração — Sistema V2 (Orquestrador Multi-API)
Testa: Provider Layer, Memory Store, Cross-Review Council, Router V2.
"""
import pytest
import sys
import os
from pathlib import Path

# Adiciona watchdog ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestProviderLayer:
    """F1: Provider Interface + adapters."""

    def test_provider_registry_loaded(self):
        from providers.registry import PROVIDER_REGISTRY, get_provider, list_providers
        assert "deepseek-flash" in PROVIDER_REGISTRY
        assert "deepseek-pro" in PROVIDER_REGISTRY
        assert "ollama-local" in PROVIDER_REGISTRY
        assert get_provider("ollama-local") is not None
        assert get_provider("nonexistent") is None

    def test_provider_interfaces(self):
        from providers.base import ProviderInterface, ProviderRequest, ProviderResponse
        from providers.deepseek_provider import DeepSeekProvider
        from providers.ollama_provider import OllamaProvider

        flash = DeepSeekProvider(profile="flash")
        pro = DeepSeekProvider(profile="pro")
        local = OllamaProvider(model="qwen2.5-coder:7b")

        assert isinstance(flash, ProviderInterface)
        assert isinstance(pro, ProviderInterface)
        assert isinstance(local, ProviderInterface)

        assert flash.name == "deepseek-flash"
        assert pro.name == "deepseek-pro"
        assert local.name == "ollama-local"

        assert "executor" in flash.supports_roles
        assert "reviewer" in pro.supports_roles
        assert "compressor" in local.supports_roles
        assert "embeddings" in local.supports_roles

    def test_estimate_cost(self):
        from providers.deepseek_provider import DeepSeekProvider
        from providers.ollama_provider import OllamaProvider

        flash = DeepSeekProvider(profile="flash")
        pro = DeepSeekProvider(profile="pro")
        local = OllamaProvider(model="qwen2.5-coder:7b")

        # Flash: 1000 tokens in/out
        cost = flash.estimate_cost(1000, 500)
        assert cost > 0
        assert cost < 1.0  # Sanity: não pode ser absurdo

        # Pro: mais caro que flash
        cost_pro = pro.estimate_cost(1000, 500)
        assert cost_pro > cost

        # Local: sempre zero
        assert local.estimate_cost(10000, 5000) == 0.0

    def test_ollama_health(self):
        from providers.ollama_provider import OllamaProvider
        local = OllamaProvider()
        # Ollama deve estar rodando
        assert local.health_check() is True

    def test_provider_dataclasses(self):
        from providers.base import ProviderRequest, ProviderResponse

        req = ProviderRequest(prompt="teste", system="sistema", max_tokens=512)
        assert req.prompt == "teste"
        assert req.system == "sistema"
        assert req.max_tokens == 512
        assert req.role == "executor"

        resp = ProviderResponse(
            text="resposta", tokens_in=100, tokens_out=50,
            cost_usd=0.001, latency_ms=500,
            provider_name="test", model_name="test-model",
        )
        assert resp.text == "resposta"
        assert resp.tokens_in == 100

    def test_estimate_tokens_helper(self):
        from providers.ollama_provider import OllamaProvider
        local = OllamaProvider()
        # 100 chars ≈ 25 tokens
        assert local.estimate_tokens("a" * 100) >= 25
        # Empty string
        assert local.estimate_tokens("") == 0
        # Single char (1 // 4 = 0, but max(1, 0) = 1)
        assert local.estimate_tokens("a") == 1


class TestMemoryStore:
    """F2+F3: Memory Store SQLite + embeddings."""

    def test_memory_store_singleton(self):
        from memory.store import MemoryStore
        m1 = MemoryStore()
        m2 = MemoryStore()
        assert m1 is m2

    def test_add_and_retrieve_fact(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        fact_id = store.add_fact(
            session_id="test_session",
            fact_text="O usuário prefere respostas concisas",
            source_provider="test",
            source_role="executor",
            importance=0.8,
        )
        assert fact_id > 0

        # Recupera por palavra-chave
        results = store.retrieve_relevant("test_session", "respostas concisas", top_k=5)
        assert len(results) >= 1
        assert "concisas" in results[0].fact_text
        assert results[0].session_id == "test_session"

    def test_add_fact_empty_session(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        fact_id = store.add_fact(
            session_id="empty_test",
            fact_text="Fato de teste isolado",
            source_provider="test",
            source_role="test",
        )
        results = store.retrieve_relevant("empty_test", "teste", top_k=3)
        assert len(results) >= 1

    def test_retrieve_without_match(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        results = store.retrieve_relevant("nonexistent_session", "algo inexistente", top_k=3)
        assert len(results) == 0

    def test_review_outcomes(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        task_hash = "abc123"
        
        store.record_review_outcome(
            session_id="test",
            task_hash=task_hash,
            approved=True,
            reviewer_provider="deepseek-flash",
            issues=["Nenhum problema encontrado"],
        )
        
        assert store.was_previously_approved(task_hash) is True
        assert store.was_previously_approved("nonexistent") is None

    def test_cost_ledger(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        entry_id = store.record_cost(
            session_id="test",
            provider_name="deepseek-flash",
            role="executor",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.0003,
        )
        assert entry_id > 0

    def test_decay_importance(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        stats_before = store.get_stats()
        result = store.decay_importance(rate=0.05, max_days=1)
        assert "archived" in result
        assert "remaining" in result
        assert result["archived"] >= 0
        assert result["remaining"] >= 0

    def test_get_stats(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        stats = store.get_stats()
        assert "facts" in stats
        assert "reviews" in stats
        assert "cost_entries" in stats
        assert "total_cost_usd" in stats
        assert "db_path" in stats
        assert stats["facts"] >= 0


class TestContextCompressor:
    """F4: Context Compressor."""

    def test_estimate_tokens(self):
        from memory.compressor import ContextCompressor
        from providers.ollama_provider import OllamaProvider
        local = OllamaProvider()
        compressor = ContextCompressor(local, token_threshold=500)
        
        # 100 chars ≈ 25 tokens → abaixo do threshold
        tokens = compressor.estimate_tokens("a" * 100)
        assert tokens >= 20
        assert tokens <= 30

    def test_compress_not_needed_small(self):
        from memory.compressor import ContextCompressor
        from providers.ollama_provider import OllamaProvider
        local = OllamaProvider()
        compressor = ContextCompressor(local, token_threshold=5000)
        
        # Contexto pequeno: não deve comprimir
        ctx = [{"role": "user", "content": "teste pequeno"}]
        import asyncio
        result = asyncio.run(compressor.compress_if_needed("test", ctx))
        assert len(result) == 1
        assert result[0]["content"] == "teste pequeno"

    def test_compress_fact_simple(self):
        from memory.compressor import ContextCompressor
        from providers.ollama_provider import OllamaProvider
        local = OllamaProvider()
        compressor = ContextCompressor(local)
        
        import asyncio
        # Texto curto, deve passar direto
        result = asyncio.run(compressor.compress_fact("Curto"))
        assert result == "Curto"


class TestCouncil:
    """F5: Cross-Review Council."""

    def test_should_review_critical(self):
        from core.council import CrossReviewCouncil
        council = CrossReviewCouncil()
        
        should, reason = council.should_review(
            response="Resposta ok", task="Tarefa", executor_provider="ollama-local",
            is_critical=True,
        )
        assert should is True
        assert "crítica" in reason

    def test_should_review_low_confidence(self):
        from core.council import CrossReviewCouncil
        council = CrossReviewCouncil()
        
        should, reason = council.should_review(
            response="Não tenho certeza sobre isso",
            task="Tarefa complexa",
            executor_provider="ollama-local",
        )
        assert should is True
        assert "confiança" in reason

    def test_should_not_review_short_task(self):
        from core.council import CrossReviewCouncil
        council = CrossReviewCouncil()
        
        should, reason = council.should_review(
            response="Resposta confiante e completa.",
            task="Oi",
            executor_provider="deepseek-pro",
        )
        assert should is False

    def test_should_review_cheap_provider(self):
        from core.council import CrossReviewCouncil
        import hashlib
        
        # Config default do orchestrator.yaml (min_task_len=400, sample_rate=0.3)
        council = CrossReviewCouncil()
        
        # Task longa o suficiente (> 400 chars)
        task = "Tarefa não trivial " * 25
        task_hash = council._compute_task_hash(task)
        bucket = int(task_hash[:8], 16) % 100
        
        should, reason = council.should_review(
            response="Resposta longa o suficiente para não cair em G3 (>100 chars). " * 3,
            task=task,
            executor_provider="ollama-local",
        )
        
        # Com sample_rate=0.3, o resultado depende do hash estar no bucket
        if bucket < 30:
            assert should is True, f"Esperava True, bucket={bucket}, hash={task_hash[:8]}"
            assert "G5" in reason, f"Esperava G5 na reason, got: {reason}"
        else:
            assert should is False, f"Esperava False, bucket={bucket}, hash={task_hash[:8]}"

    def test_g5_sample_rate_distribution(self):
        from core.g5_fires import g5_fires
        import hashlib
        
        # Gera 200 task_hashes sintéticos determinísticos
        hashes = [
            hashlib.sha256(f"bench-task-{i}".encode()).hexdigest()[:8]
            for i in range(200)
        ]
        
        results = [g5_fires(h, 500, min_task_len=400, sample_rate=0.3) for h in hashes]
        true_count = sum(results)
        ratio = true_count / 200
        
        assert 0.20 <= ratio <= 0.40, (
            f"g5_fires sample_rate=0.3: {true_count}/200 = {ratio:.3f} "
            f"— fora da margem 0.20-0.40"
        )

    def test_parse_verdict_json(self):
        from core.council import CrossReviewCouncil, ReviewVerdict
        council = CrossReviewCouncil()
        
        verdict = council._parse_verdict(
            '{"approved": true, "confidence": 0.9, "issues": [], "suggested_fix": null}',
            "deepseek-flash",
        )
        assert verdict.approved is True
        assert verdict.confidence == 0.9
        assert len(verdict.issues) == 0

    def test_parse_verdict_markdown_fence(self):
        from core.council import CrossReviewCouncil
        council = CrossReviewCouncil()
        
        verdict = council._parse_verdict(
            '```json\n{"approved": false, "confidence": 0.4, "issues": ["Erro lógico"], "suggested_fix": "Corrigir X"}\n```',
            "deepseek-flash",
        )
        assert verdict.approved is False
        assert len(verdict.issues) == 1
        assert verdict.suggested_fix == "Corrigir X"

    def test_reviewer_selection(self):
        from core.council import CrossReviewCouncil
        council = CrossReviewCouncil()
        
        # Ollama → DeepSeek Flash
        reviewer = council.select_reviewer("ollama-local")
        assert reviewer is not None
        assert reviewer.name == "deepseek-flash"

        # DeepSeek Pro → Ollama (sanity check barato)
        reviewer = council.select_reviewer("deepseek-pro")
        assert reviewer is not None
        assert reviewer.name == "ollama-local"


class TestRouterV2:
    """F6: Router Econômico v2 + integração."""

    def test_classify_risk(self):
        from core.router_v2 import RouterV2
        router = RouterV2()
        
        assert router.classify_risk("deploy para produção") == "high"
        assert router.classify_risk("implementar API de pagamento") == "high"
        assert router.classify_risk("refatorar módulo de login") == "medium"
        assert router.classify_risk("listar arquivos") == "low"

    def test_task_hash(self):
        from core.router_v2 import RouterV2
        router = RouterV2()
        
        h1 = router._compute_task_hash("implementar função de busca")
        h2 = router._compute_task_hash("Implementar Função de Busca  ")
        h3 = router._compute_task_hash("algo completamente diferente")
        
        assert h1 == h2  # Normalização
        assert h1 != h3  # Diferentes

    def test_select_executor_low_risk(self):
        from core.router_v2 import RouterV2
        router = RouterV2()
        
        executor = router.select_executor("listar arquivos", "low")
        assert executor is not None
        assert executor.estimate_cost(1000, 500) == 0.0  # Deve ser local/grátis

    def test_select_executor_high_risk(self):
        from core.router_v2 import RouterV2
        router = RouterV2()
        
        executor = router.select_executor("deploy produção", "high")
        assert executor is not None

    def test_decide_structure(self):
        from core.router_v2 import RouterV2
        router = RouterV2()
        
        decision = router.decide("listar arquivos no diretório", is_critical=False)
        assert decision.provider_name is not None
        assert decision.task_hash is not None
        assert decision.risk_level is not None
        assert isinstance(decision.cost_estimate, float)
        assert isinstance(decision.needs_review, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
