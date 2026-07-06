"""Testes unitários para o módulo providers/ do Orquestrador V2."""
from __future__ import annotations

import pytest

from providers.base import ProviderInterface, ProviderRequest, ProviderResponse
from providers.deepseek_provider import DeepSeekProvider
from providers.ollama_provider import OllamaProvider
from providers.registry import PROVIDER_REGISTRY, get_provider, list_providers


class TestProviderRequest:
    """ProviderRequest dataclass."""

    def test_defaults(self):
        req = ProviderRequest(prompt="Hello")
        assert req.prompt == "Hello"
        assert req.system is None
        assert req.max_tokens == 1024
        assert req.temperature == 0.7
        assert req.role == "executor"
        assert req.metadata == {}

    def test_custom(self):
        req = ProviderRequest(
            prompt="Test",
            system="Be concise",
            max_tokens=512,
            temperature=0.3,
            role="reviewer",
            metadata={"foo": "bar"},
        )
        assert req.max_tokens == 512
        assert req.temperature == 0.3
        assert req.role == "reviewer"
        assert req.metadata == {"foo": "bar"}


class TestProviderResponse:
    """ProviderResponse dataclass."""

    def test_defaults(self):
        resp = ProviderResponse(text="Hello")
        assert resp.text == "Hello"
        assert resp.success is True
        assert resp.error is None
        assert resp.cost_usd == 0.0
        assert resp.tokens_in == 0
        assert resp.tokens_out == 0

    def test_error_resp(self):
        resp = ProviderResponse(text="", success=False, error="API down")
        assert resp.success is False
        assert resp.error == "API down"


class TestProviderInterface:
    """ABC base — testa método auxiliar estimate_tokens."""

    def test_estimate_tokens(self):
        # Classe concreta fictícia para testar o helper
        class FakeProvider(ProviderInterface):
            name = "fake"
            async def generate(self, req): ...
            def estimate_cost(self, tin, tout): return 0.0
            def health_check(self): return True

        p = FakeProvider()
        assert p.estimate_tokens("abcd") == 1       # 4 // 4
        assert p.estimate_tokens("") == 0            # vazio = 0
        assert p.estimate_tokens("a" * 100) == 25    # 100 // 4


class TestDeepSeekProvider:
    """DeepSeek provider — construção, roles, pricing, health."""

    def test_flash_default(self):
        p = DeepSeekProvider()
        assert p.name == "deepseek-flash"
        assert p.model_name == "deepseek-v4-flash"
        assert p.supports_roles == ["executor"]

    def test_pro_profile(self):
        p = DeepSeekProvider(profile="pro")
        assert p.name == "deepseek-pro"
        assert p.model_name == "deepseek-v4-pro"
        assert "reviewer" in p.supports_roles

    def test_invalid_profile(self):
        with pytest.raises(ValueError, match="inválido"):
            DeepSeekProvider(profile="gpt5")

    def test_pricing_flash(self):
        p = DeepSeekProvider(profile="flash")
        # 1M tokens in = $0.15, 1M out = $0.30
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(0.45, rel=1e-3)

    def test_pricing_pro(self):
        p = DeepSeekProvider(profile="pro")
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(2.74, rel=1e-3)

    def test_pricing_zero(self):
        p = DeepSeekProvider(profile="flash")
        assert p.estimate_cost(0, 0) == 0.0

    @pytest.mark.asyncio
    async def test_generate_without_key_returns_error(self):
        p = DeepSeekProvider()
        req = ProviderRequest(prompt="hello")
        resp = await p.generate(req)
        assert resp.success is False
        assert "DEEPSEEK_API_KEY" in (resp.error or "")

    def test_health_check(self):
        p = DeepSeekProvider()
        # Deve retornar False (sem rede real), não lançar exceção
        result = p.health_check()
        assert isinstance(result, bool)


class TestOllamaProvider:
    """Ollama provider — construção, roles, custo zero, embeddings."""

    def test_default_model(self):
        p = OllamaProvider()
        assert p.name == "ollama-local"
        assert p.model_name == "qwen2.5-coder:7b"

    def test_custom_model(self):
        p = OllamaProvider(model="llama3.2:3b")
        assert p.model_name == "llama3.2:3b"

    def test_supports_all_roles(self):
        p = OllamaProvider()
        assert p.supports_roles == [
            "executor", "reviewer", "compressor", "embeddings",
        ]

    def test_cost_zero(self):
        p = OllamaProvider()
        assert p.estimate_cost(1_000_000, 1_000_000) == 0.0
        assert p.estimate_cost(0, 0) == 0.0

    def test_health_check(self):
        p = OllamaProvider()
        # Deve retornar False (Ollama não rodando), não lançar exceção
        result = p.health_check()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_generate_response_shape(self):
        """Testa que generate retorna ProviderResponse bem formado."""
        p = OllamaProvider()
        req = ProviderRequest(prompt="hello")
        resp = await p.generate(req)
        assert isinstance(resp, ProviderResponse)
        assert resp.provider_name == "ollama-local"
        assert resp.model_name == "qwen2.5-coder:7b"
        # Se o servidor estiver rodando, deve ter texto e custo zero
        if resp.success:
            assert len(resp.text) > 0
            assert resp.cost_usd == 0.0
            assert resp.latency_ms > 0
        else:
            assert resp.error is not None

    def test_estimate_tokens_inherited(self):
        p = OllamaProvider()
        assert p.estimate_tokens("hello world") == 2  # 11//4


class TestRegistry:
    """Registry — get_provider, list_providers, role filtering."""

    def test_registry_initialized(self):
        assert len(PROVIDER_REGISTRY) >= 3
        assert "deepseek-flash" in PROVIDER_REGISTRY
        assert "deepseek-pro" in PROVIDER_REGISTRY
        assert "ollama-local" in PROVIDER_REGISTRY

    def test_get_provider_found(self):
        p = get_provider("deepseek-flash")
        assert p is not None
        assert p.name == "deepseek-flash"

    def test_get_provider_not_found(self):
        assert get_provider("nonexistent") is None

    def test_list_all(self):
        all_p = list_providers()
        names = {p.name for p in all_p}
        assert names == {"deepseek-flash", "deepseek-pro", "ollama-local"}

    def test_list_by_role_executor(self):
        ps = list_providers(role="executor")
        assert len(ps) == 3  # todos suportam executor

    def test_list_by_role_reviewer(self):
        ps = list_providers(role="reviewer")
        names = {p.name for p in ps}
        assert names == {"deepseek-pro", "ollama-local"}

    def test_list_by_role_embeddings(self):
        ps = list_providers(role="embeddings")
        assert len(ps) == 1
        assert ps[0].name == "ollama-local"

    def test_list_by_role_compressor(self):
        ps = list_providers(role="compressor")
        assert len(ps) == 1
        assert ps[0].name == "ollama-local"

    def test_reload_from_yaml_exists(self):
        from providers.registry import reload_from_yaml
        reload_from_yaml()  # não deve lançar
