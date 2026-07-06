"""Registry central de provedores — carregados do providers.yaml."""
from __future__ import annotations

from typing import Optional

from providers.base import ProviderInterface
from providers.deepseek_provider import DeepSeekProvider
from providers.ollama_provider import OllamaProvider

PROVIDER_REGISTRY: dict[str, ProviderInterface] = {}


def _init_registry() -> None:
    """Inicializa registry com os provedores default."""
    flash = DeepSeekProvider(profile="flash")
    pro = DeepSeekProvider(profile="pro")
    local = OllamaProvider(model="qwen2.5-coder:7b")
    PROVIDER_REGISTRY["deepseek-flash"] = flash
    PROVIDER_REGISTRY["deepseek-pro"] = pro
    PROVIDER_REGISTRY["ollama-local"] = local


def get_provider(name: str) -> Optional[ProviderInterface]:
    """Retorna um provedor pelo nome, ou None se não encontrado."""
    if not PROVIDER_REGISTRY:
        _init_registry()
    return PROVIDER_REGISTRY.get(name)


def list_providers(role: Optional[str] = None) -> list[ProviderInterface]:
    """Lista provedores, opcionalmente filtrando por papel.

    Args:
        role: Se fornecido, filtra apenas provedores que suportam este papel.
              Ex.: "executor", "reviewer", "compressor", "embeddings".
    """
    if not PROVIDER_REGISTRY:
        _init_registry()
    if role:
        return [
            p for p in PROVIDER_REGISTRY.values()
            if role in p.supports_roles
        ]
    return list(PROVIDER_REGISTRY.values())


def reload_from_yaml(path: Optional[str] = None) -> None:
    """Futuro: carregar provedores do providers.yaml (F1 extensível).

    Args:
        path: Caminho para o arquivo YAML. Se None, usa o default.
    """
    pass


# Inicialização automática no momento da importação
_init_registry()
