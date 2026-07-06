"""Ollama Provider — inferência local via servidor Ollama."""
from __future__ import annotations

import json
import time
from typing import Optional

import requests

from logger import get_logger
from providers.base import ProviderInterface, ProviderRequest, ProviderResponse

logger = get_logger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
FALLBACK_EMBED_MODEL = "qwen2.5-coder:7b"


class OllamaProvider(ProviderInterface):
    """Provedor local via servidor Ollama.

    Args:
        model: Modelo a ser usado (padrão: qwen2.5-coder:7b).
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model_name = model
        self.name = "ollama-local"
        self.supports_roles = [
            "executor", "reviewer", "compressor", "embeddings",
        ]

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    async def generate(self, req: ProviderRequest) -> ProviderResponse:
        """Chama /api/generate no servidor Ollama local."""
        payload = {
            "model": self.model_name,
            "prompt": req.prompt,
            "system": req.system or "",
            "stream": False,
            "options": {
                "num_predict": req.max_tokens,
                "temperature": req.temperature,
            },
        }

        # Inclui metadata extra se houver
        if req.metadata:
            payload["options"].update(req.metadata)

        headers = {"Content-Type": "application/json"}
        t0 = time.time()
        last_error: Optional[str] = None

        for attempt in range(2):  # 1 tentativa + 1 retry
            try:
                resp = requests.post(
                    OLLAMA_GENERATE_URL,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                elapsed_ms = (time.time() - t0) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("response", "")

                    # Ollama não retorna contagem de tokens em todos os modelos;
                    # usamos o campo 'eval_count' se disponível, senão estimamos.
                    tokens_in = data.get("prompt_eval_count", 0)
                    tokens_out = data.get("eval_count", 0)

                    return ProviderResponse(
                        text=text,
                        tokens_in=tokens_in or self.estimate_tokens(req.prompt),
                        tokens_out=tokens_out or self.estimate_tokens(text),
                        cost_usd=0.0,
                        latency_ms=elapsed_ms,
                        provider_name=self.name,
                        model_name=self.model_name,
                        raw=data,
                        success=True,
                    )

                last_error = (
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                logger.warning(
                    "[ollama-local] Tentativa %d falhou: %s",
                    attempt + 1, last_error,
                )

            except requests.exceptions.Timeout:
                last_error = "Timeout após 120s"
                logger.warning(
                    "[ollama-local] Tentativa %d timeout", attempt + 1,
                )
            except requests.exceptions.ConnectionError as exc:
                last_error = f"Erro de conexão — Ollama está rodando?: {exc}"
                logger.warning(
                    "[ollama-local] Tentativa %d conexão falhou: %s",
                    attempt + 1, exc,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    "[ollama-local] Tentativa %d erro inesperado: %s",
                    attempt + 1, exc,
                )

            if attempt == 0:
                time.sleep(0.5)

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
    # Embeddings
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> list[float]:
        """Gera embedding vetorial para o texto usando /api/embeddings.

        Tenta usar 'nomic-embed-text' primeiro; se não existir, usa o
        modelo configurado (qwen2.5-coder:7b).
        """
        model = DEFAULT_EMBED_MODEL

        # Testa se o modelo de embedding dedicado existe
        try:
            tags_resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if tags_resp.status_code == 200:
                models = tags_resp.json().get("models", [])
                available = {m.get("name", "") for m in models}
                if DEFAULT_EMBED_MODEL not in available:
                    model = FALLBACK_EMBED_MODEL
                    logger.info(
                        "Modelo '%s' não encontrado, usando '%s' para embedding",
                        DEFAULT_EMBED_MODEL, model,
                    )
        except Exception:
            model = FALLBACK_EMBED_MODEL

        payload = {
            "model": model,
            "prompt": text,
        }

        try:
            resp = requests.post(
                OLLAMA_EMBED_URL,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embedding", [])
            logger.error(
                "Embedding HTTP %d: %s", resp.status_code, resp.text[:200],
            )
        except Exception as exc:
            logger.error("Erro ao gerar embedding: %s", exc)

        return []

    # ------------------------------------------------------------------
    # Custo (sempre zero — local)
    # ------------------------------------------------------------------

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Ollama local é gratuito."""
        return 0.0

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Verifica se o servidor Ollama está respondendo."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
