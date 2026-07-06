"""ContextCompressor — Compressão de contexto de entrada e de gravação via Ollama.
Duas frentes:
1. Compressão de entrada (antes de enviar ao provider)
2. Compressão de gravação (antes de salvar na memória)
Sempre via Ollama local (custo zero). NUNCA via DeepSeek (pago).
"""
from __future__ import annotations

from typing import Optional

from providers.base import ProviderInterface, ProviderRequest

try:
    from logger_pro import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ─── Prompts de compressão ──────────────────────────

CONTEXT_COMPRESS_PROMPT = (
    "Resuma o histórico abaixo em no máximo 3 frases, preservando: "
    "decisões tomadas, números/valores citados, e pendências em aberto. "
    "Descarte small talk e repetições."
)

FACT_COMPRESS_PROMPT = (
    "Resuma o evento abaixo em uma frase concisa, preservando: "
    "decisões, números, nomes de arquivos, e conclusões importantes. "
    "Seja objetivo e factual."
)


class ContextCompressor:
    """Comprime contexto antes de enviar ao provider e antes de gravar na memória.
    
    Regra de ouro:
    - Nunca comprimir as últimas N mensagens (turno atual)
    - Nunca comprimir as primeiras N mensagens (contexto de sistema)
    - Sempre preservar números e decisões
    - Usar APENAS Ollama local (custo zero)
    """
    
    def __init__(self, compressor_provider: ProviderInterface,
                 token_threshold: int = 3000,
                 protect_last_n: int = 4,
                 protect_first_n: int = 2):
        """
        Args:
            compressor_provider: Provider para compressão (DEVE ser Ollama, custo zero)
            token_threshold: Só comprime se total de tokens > este valor
            protect_last_n: Últimas N mensagens não comprimidas
            protect_first_n: Primeiras N mensagens não comprimidas
        """
        self.provider = compressor_provider
        self.token_threshold = token_threshold
        self.protect_last_n = protect_last_n
        self.protect_first_n = protect_first_n
    
    def estimate_tokens(self, text: str) -> int:
        """Aproximação: ~4 chars por token."""
        if not text:
            return 0
        return len(text) // 4
    
    async def compress_if_needed(self, session_id: str,
                                  raw_context: list[dict]) -> list[dict]:
        """Comprime contexto se estiver acima do threshold.
        
        Args:
            session_id: ID da sessão (para log)
            raw_context: Lista de mensagens [{"role": ..., "content": ...}]
        
        Returns:
            Mensagens comprimidas (ou originais se abaixo do threshold)
        """
        total_tokens = sum(
            self.estimate_tokens(m.get("content", ""))
            for m in raw_context
        )
        
        if total_tokens <= self.token_threshold:
            logger.debug(f"Compressão ignorada: {total_tokens} tok ≤ {self.token_threshold}")
            return raw_context
        
        # Protege primeiras e últimas mensagens
        if len(raw_context) <= self.protect_first_n + self.protect_last_n:
            logger.debug("Contexto muito curto para compressão")
            return raw_context
        
        first_n = raw_context[:self.protect_first_n]
        last_n = raw_context[-self.protect_last_n:]
        middle = raw_context[self.protect_first_n:-self.protect_last_n]
        
        if not middle:
            return raw_context
        
        # Concatena o bloco do meio para compressão
        middle_text = "\n---\n".join(
            f"{m.get('role', 'unknown')}: {str(m.get('content', ''))[:2000]}"
            for m in middle
        )
        
        logger.info(
            f"Comprimindo bloco médio: {len(middle)} msgs, "
            f"{self.estimate_tokens(middle_text)} tok"
        )
        
        compressed = await self._compress_text(middle_text, CONTEXT_COMPRESS_PROMPT)
        
        # Monta resultado: primeiras + resumo + últimas
        result = first_n + [
            {
                "role": "system",
                "content": (
                    f"[Contexto comprimido ({self.estimate_tokens(middle_text)} tok → "
                    f"{self.estimate_tokens(compressed)} tok): {compressed[:3000]}]"
                ),
            }
        ] + last_n
        
        tokens_antes = total_tokens
        tokens_depois = sum(self.estimate_tokens(m.get("content", "")) for m in result)
        economia = tokens_antes - tokens_depois
        pct = (economia / tokens_antes * 100) if tokens_antes else 0
        
        logger.info(f"Compressão: {tokens_antes} → {tokens_depois} tok ({pct:.0f}% redução)")
        
        return result
    
    async def compress_fact(self, text: str) -> str:
        """Comprime texto para armazenamento como fato na memória.
        
        Se o texto for curto (< 200 chars), passa direto.
        """
        if not text or len(text) < 200:
            return text
        
        return await self._compress_text(text, FACT_COMPRESS_PROMPT)
    
    async def _compress_text(self, text: str, system_prompt: str) -> str:
        """Chama o provider de compressão (Ollama local, custo zero).
        
        Args:
            text: Texto a comprimir
            system_prompt: Instrução de compressão
        
        Returns:
            Texto comprimido, ou original se falhar
        """
        if not text.strip():
            return text
        
        # Limita tamanho do texto de entrada
        input_text = text[:4000]
        
        req = ProviderRequest(
            prompt=f"{system_prompt}\n\n{input_text}",
            system="Você é um compressor de texto. Seja conciso e preciso. "
                   "Preserve números, decisões, e nomes próprios.",
            max_tokens=1024,
            temperature=0.1,
            role="compressor",
        )
        
        try:
            resp = await self.provider.generate(req)
            compressed = resp.text.strip()
            
            if compressed and len(compressed) < len(text):
                logger.debug(f"Comprimido: {len(text)} → {len(compressed)} chars")
                return compressed
            
            logger.debug("Compressão não reduziu tamanho, mantendo original")
            return text
            
        except Exception as e:
            logger.warning(f"Compressão falhou: {e}. Usando original.")
            return text  # Fallback seguro
