"""DeepSeek Provider — conexão com a API oficial da DeepSeek (flash e pro)."""
from __future__ import annotations

import json
import os
import time
from typing import Optional

import requests

from logger import get_logger
from providers.base import ProviderInterface, ProviderRequest, ProviderResponse

logger = get_logger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"

# Pricing (USD por 1M tokens)
PRICING = {
    "deepseek-flash": {"in": 0.15, "out": 0.30},
    "deepseek-pro":   {"in": 0.55, "out": 2.19},
}

MODEL_MAP = {
    "flash": "deepseek-v4-flash",
    "pro":   "deepseek-v4-pro",
}


class DeepSeekProvider(ProviderInterface):
    """Provedor para a API oficial da DeepSeek.

    Args:
        profile: "flash" (padrão, mais barato) ou "pro" (mais potente).
    """

    def __init__(self, profile: str = "flash") -> None:
        profile = profile.lower()
        if profile not in MODEL_MAP:
            raise ValueError(f"Perfil inválido: {profile}. Use 'flash' ou 'pro'.")

        self._profile = profile
        self.model_name = MODEL_MAP[profile]
        self.name = f"deepseek-{profile}"
        self.supports_roles = (
            ["executor", "reviewer"] if profile == "pro" else ["executor"]
        )
        self._pricing = PRICING[self.name]

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    async def generate(self, req: ProviderRequest) -> ProviderResponse:
        """Chama o chat completion da DeepSeek."""
        api_key = os.environ.get(DEEPSEEK_API_KEY_ENV)
        if not api_key:
            return ProviderResponse(
                text="",
                success=False,
                error=f"Variável de ambiente {DEEPSEEK_API_KEY_ENV} não definida.",
                provider_name=self.name,
                model_name=self.model_name,
            )

        messages = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.time()
        last_error: Optional[str] = None

        for attempt in range(2):  # 1 tentativa + 1 retry
            try:
                resp = requests.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
                elapsed_ms = (time.time() - t0) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    text = choice["message"]["content"]

                    usage = data.get("usage", {})
                    tokens_in = usage.get("prompt_tokens", 0)
                    tokens_out = usage.get("completion_tokens", 0)

                    return ProviderResponse(
                        text=text,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=self.estimate_cost(tokens_in, tokens_out),
                        latency_ms=elapsed_ms,
                        provider_name=self.name,
                        model_name=self.model_name,
                        raw=data,
                        success=True,
                    )

                # Erro HTTP
                last_error = (
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                logger.warning(
                    "[%s] Tentativa %d falhou: %s",
                    self.name, attempt + 1, last_error,
                )

            except requests.exceptions.Timeout:
                last_error = "Timeout após 60s"
                logger.warning(
                    "[%s] Tentativa %d timeout", self.name, attempt + 1,
                )
            except requests.exceptions.ConnectionError as exc:
                last_error = f"Erro de conexão: {exc}"
                logger.warning(
                    "[%s] Tentativa %d conexão falhou: %s",
                    self.name, attempt + 1, exc,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    "[%s] Tentativa %d erro inesperado: %s",
                    self.name, attempt + 1, exc,
                )

            # Pequena pausa antes do retry
            if attempt == 0:
                time.sleep(1)

        # Se chegou aqui, todas as tentativas falharam
        elapsed_ms = (time.time() - t0) * 1000
        return ProviderResponse(
            text="",
            success=False,
            error=last_error or "Falha desconhecida após retry",
            latency_ms=elapsed_ms,
            provider_name=self.name,
            model_name=self.model_name,
        )

    # ------------------------------------------------------------------
    # Estimativa de custo
    # ------------------------------------------------------------------

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Calcula custo baseado no pricing por milhão de tokens."""
        cost_in = (tokens_in / 1_000_000) * self._pricing["in"]
        cost_out = (tokens_out / 1_000_000) * self._pricing["out"]
        return round(cost_in + cost_out, 6)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Tenta um GET simples na API da DeepSeek."""
        try:
            resp = requests.get(
                "https://api.deepseek.com/v1/models",
                timeout=5,
            )
            return resp.status_code < 500  # 2xx ou 4xx = online
        except Exception:
            return False
