"""Provider Abstraction Layer — Interface única para múltiplos provedores de API."""
from providers.base import ProviderInterface, ProviderRequest, ProviderResponse
from providers.deepseek_provider import DeepSeekProvider
from providers.ollama_provider import OllamaProvider
from providers.registry import PROVIDER_REGISTRY, get_provider, list_providers

__all__ = [
    "ProviderInterface", "ProviderRequest", "ProviderResponse",
    "DeepSeekProvider", "OllamaProvider",
    "PROVIDER_REGISTRY", "get_provider", "list_providers",
]
