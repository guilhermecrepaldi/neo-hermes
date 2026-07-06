"""Base Provider Interface — ABC que todos os provedores devem implementar."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderRequest:
    """Request padronizado para qualquer provedor."""
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    role: str = "executor"
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """Response padronizado de qualquer provedor."""
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    provider_name: str = ""
    model_name: str = ""
    raw: Optional[dict] = None
    success: bool = True
    error: Optional[str] = None


class ProviderInterface(ABC):
    """Interface abstrata para provedores de API.

    Attributes:
        name: Identificador único do provedor (ex.: "deepseek-flash").
        supports_roles: Lista de papéis que este provedor pode exercer.
    """

    name: str = "unknown"
    supports_roles: list[str] = ["executor"]

    @abstractmethod
    async def generate(self, req: ProviderRequest) -> ProviderResponse:
        """Gera uma resposta a partir do prompt."""
        ...

    @abstractmethod
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estima o custo em USD para um dado volume de tokens."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Retorna True se o provedor estiver acessível."""
        ...

    def estimate_tokens(self, text: str) -> int:
        """Aproximação simples: 1 token ~= 4 caracteres."""
        if not text:
            return 0
        return max(1, len(text) // 4)
