"""TersePolicy — Política de concisão para outputs de agentes internos.
Aplica-se seletivamente a papéis específicos (reviewer, compressor, handoffs)
sem afetar respostas finais para humanos.

Duas frentes:
1. Prompt wrapper: anexa instrução de concisão ao system prompt
2. Post-processor: encurta outputs verbosos (removendo justificativas, etc.)
"""
from __future__ import annotations

import re
from typing import Optional

# ─── Prompts de concisão por papel ──────────────────

TERSE_PROMPTS = {
    "reviewer": (
        "Seja CONCISO. Responda APENAS o JSON solicitado. "
        "Não explique sua resposta. Não inclua saudações, resumos ou comentários. "
        "Apenas o JSON puro."
    ),
    "compressor": (
        "Seja CONCISO. Preserve APENAS números, decisões, nomes de arquivos e conclusões. "
        "Remova artigos, advérbios, adjetivos e repetições. "
        "Responda em no máximo 2 frases."
    ),
    "executor": (
        "Seja direto. Responda APENAS o que foi perguntado. "
        "Sem introduções, conclusões ou elaborações desnecessárias."
    ),
}

# ─── Padrões de verbosidade para pós-processamento ──

VERBOSE_PATTERNS = [
    # Saudações e aberturas
    (r'(?i)^(claro!?|com certeza!?|ótimo!?|ok!?|okay!?|sim!?|vamos lá!?|aqui está!?|aqui vai!?)\s*', ''),
    (r'(?i)^(com\s+prazer!?|pois\s+não!?|pode\s+deixar!?|deixa\s+comigo!?)\s*', ''),
    # Fechamentos
    (r'(?i)\s*(espero\s+ter\s+ajudado!?|qualquer\s+dúvida!?|estou\s+aqui\s+para\s+ajudar!?|avise\s+se\s+precisar!?)\s*$', ''),
    (r'(?i)\s*(abraço|atenciosamente|grato|obrigado|:)\.?\s*$', ''),
    # Justificativas
    (r'(?i)\s*(isso\s+ocorre\s+porque|a\s+razão\s+é\s+que|devido\s+a|como\s+mencionado|conforme\s+explicado).{0,100}', ''),
]

# ─── Pós-processamento para JSON ────────────────────

JSON_VERBOSE_PATTERNS = [
    # Texto antes do primeiro JSON
    (r'^.*?(\{)', r'\1'),
    (r'^.*?(\[)', r'\1'),
    # Texto depois do último JSON
    (r'(\})[^}]*$', r'\1'),
    (r'(\])[^\]]*$', r'\1'),
]


class TersePolicy:
    """Política de concisão para agentes internos.
    
    Ativa por papel. Não afeta respostas finais para humanos.
    
    Uso:
        policy = TersePolicy()
        
        # Modificar prompt para ser conciso
        prompt = policy.wrap_prompt(original_prompt, role="reviewer")
        
        # Pós-processar resposta
        clean = policy.post_process(response_text, role="reviewer")
    """
    
    def __init__(self, enabled: bool = True, 
                 roles: Optional[list[str]] = None):
        """
        Args:
            enabled: Se False, passa tudo direto (sem efeito)
            roles: Lista de papéis que sofrem terse. Default: todos
        """
        self.enabled = enabled
        self.roles = roles or ["reviewer", "compressor", "executor"]
    
    def wrap_prompt(self, prompt: str, system: Optional[str] = None,
                    role: str = "executor") -> tuple[str, Optional[str]]:
        """Modifica prompt para solicitar resposta concisa.
        
        Returns:
            (prompt_modificado, system_modificado)
        """
        if not self.enabled or role not in self.roles:
            return prompt, system
        
        terse = TERSE_PROMPTS.get(role)
        if not terse:
            return prompt, system
        
        # Adiciona ao system prompt ou ao final do prompt
        if system:
            system = f"{system}\n\n{terse}"
        else:
            prompt = f"{terse}\n\n{prompt}"
        
        return prompt, system
    
    def post_process(self, text: str, role: str = "executor",
                     is_json: bool = False) -> str:
        """Remove verbosidade de uma resposta.
        
        Args:
            text: Texto da resposta
            role: Papel que gerou a resposta
            is_json: Se True, usa stripping mais agressivo para JSON
        
        Returns:
            Texto limpo
        """
        if not self.enabled or not text or role not in self.roles:
            return text
        
        result = text
        
        # Se é JSON, limpa texto antes/depois do JSON
        if is_json:
            trimmed = result.strip()
            
            # Prefixo: só remove se não começar com { ou [
            if trimmed and trimmed[0] not in ('{', '['):
                for pattern, replacement in JSON_VERBOSE_PATTERNS:
                    prev = result
                    result = re.sub(pattern, replacement, result, count=1, flags=re.DOTALL)
                    if result != prev and result.strip().startswith(('{', '[')):
                        break
            
            # Sufixo: sempre remove texto após o último } ou ]
            if '}' in result:
                result = re.sub(r'(\})[^}]*$', r'\1', result, flags=re.DOTALL)
            elif ']' in result:
                result = re.sub(r'(\])[^\]]*$', r'\1', result, flags=re.DOTALL)
        
        # Remove padrões de verbosidade
        for pattern, replacement in VERBOSE_PATTERNS:
            result = re.sub(pattern, replacement, result)
        
        return result.strip()
    
    def make_prompt_and_postprocess(self, prompt: str,
                                     system: Optional[str],
                                     role: str,
                                     is_json: bool = False) -> dict:
        """Wrapper completo: wrap + post-process em uma chamada.
        
        Returns:
            {"prompt": str, "system": str | None, "terse_applied": bool}
        """
        mod_prompt, mod_system = self.wrap_prompt(prompt, system, role)
        return {
            "prompt": mod_prompt,
            "system": mod_system,
            "terse_applied": (mod_prompt != prompt or mod_system != system),
        }
