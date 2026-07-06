"""DeterministicCompressor — Compressor puramente lógico, zero LLM, zero custo.
Comprime tool outputs, logs, JSON arrays e strings longas usando regras
determinísticas. NUNCA chama Ollama ou qualquer API.

Idempotente: comprimir o mesmo input N vezes produz o mesmo resultado.
Proteção: preserva números, erros, exceções, paths de arquivo.

Uso:
    from memory.deterministic_compressor import DeterministicCompressor
    dc = DeterministicCompressor()
    compressed = dc.compress_tool_output(long_output)
"""
from __future__ import annotations

import json
import re
from typing import Any


class DeterministicCompressor:
    """Compressor determinístico baseado em regras.
    
    Características:
    - Zero LLM: nunca chama Ollama ou API
    - Zero custo: puro Python
    - Idempotente: mesmo input → mesmo output
    - Preserva: números, erros, exceções, caminhos de arquivo, códigos
    """
    
    def __init__(self, max_array_items: int = 20,
                 max_log_lines: int = 15,
                 max_str_len: int = 8000,
                 min_size_to_compress: int = 500):
        """
        Args:
            max_array_items: Máximo de itens em arrays antes de truncar
            max_log_lines: Máximo de linhas preservadas em logs (início + fim)
            max_str_len: Máximo de caracteres em strings longas
            min_size_to_compress: Só comprime se texto > este valor
        """
        self.max_array_items = max_array_items
        self.max_log_lines = max_log_lines
        self.max_str_len = max_str_len
        self.min_size_to_compress = min_size_to_compress
    
    def compress_tool_output(self, raw: str) -> str:
        """Comprime um output de ferramenta (logs, JSON, texto).
        
        Args:
            raw: Texto bruto do output
        
        Returns:
            Texto comprimido (ou original se já for pequeno)
        """
        if not raw or len(raw) < self.min_size_to_compress:
            return raw
        
        # Tenta parse como JSON
        trimmed = raw.strip()
        if trimmed and (trimmed[0] in ('{', '[')):
            try:
                data = json.loads(trimmed)
                compressed = self._compress_obj(data)
                # Re-serializa compacto
                result = json.dumps(compressed, ensure_ascii=False, indent=None)
                if len(result) < len(raw) * 0.8:  # Só usa se realmente reduziu
                    return result
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Logs / texto multi-linha
        lines = raw.splitlines()
        if len(lines) > self.max_log_lines * 2:
            return self._compress_lines(lines)
        
        # String longa genérica
        if len(raw) > self.max_str_len:
            return raw[:self.max_str_len] + f"\n... [truncado: {len(raw) - self.max_str_len} chars]"
        
        return raw
    
    def _compress_lines(self, lines: list[str]) -> str:
        """Comprime linhas preservando início, fim e linhas de erro."""
        n = len(lines)
        keep: set[int] = set()
        
        # Início
        keep.update(range(min(self.max_log_lines, n)))
        
        # Fim
        keep.update(range(max(0, n - self.max_log_lines), n))
        
        # Linhas de erro/exceção (preserva contexto ±2 linhas)
        error_pattern = re.compile(
            r'error|fail|exception|traceback|warning|critical|fatal|denied|refused',
            re.IGNORECASE,
        )
        for i, line in enumerate(lines):
            if error_pattern.search(line):
                keep.update(range(max(0, i - 2), min(n, i + 3)))
        
        # Linhas com números/paths/códigos relevantes
        code_pattern = re.compile(r'\d{3,}|/[a-zA-Z]:[\\/]|File\s|at\s|line\s\d+')
        for i, line in enumerate(lines):
            if code_pattern.search(line):
                keep.update(range(max(0, i - 1), min(n, i + 2)))
        
        sorted_keep = sorted(keep)
        compressed = []
        prev = -1
        for idx in sorted_keep:
            if prev >= 0 and idx - prev > 1:
                gap = idx - prev - 1
                compressed.append(f"... [omitido: {gap} linhas] ...")
            compressed.append(lines[idx])
            prev = idx
        
        # Mostra contagem
        if n > len(sorted_keep):
            compressed.insert(0, f"[output: {n} linhas → {len(sorted_keep)} linhas preservadas]")
        
        return "\n".join(compressed)
    
    def _compress_obj(self, obj: Any) -> Any:
        """Comprime objetos JSON recursivamente."""
        if isinstance(obj, list):
            if len(obj) > self.max_array_items:
                result = [self._compress_obj(x) for x in obj[:self.max_array_items]]
                result.append(f"... e mais {len(obj) - self.max_array_items} itens")
                return result
            return [self._compress_obj(x) for x in obj]
        
        if isinstance(obj, dict):
            return {k: self._compress_obj(v) for k, v in obj.items()}
        
        if isinstance(obj, str):
            if len(obj) > self.max_str_len:
                # Preserva início e fim
                keep = self.max_str_len // 2
                return obj[:keep] + "\n... [texto longo truncado] ...\n" + obj[-keep:]
            return obj
        
        if isinstance(obj, (int, float, bool)):
            return obj
        
        if obj is None:
            return None
        
        return str(obj)
    
    def compress_fact(self, fact_text: str) -> str:
        """Comprime texto para armazenamento como fato na memória.
        
        Mais agressivo que compress_tool_output — extrai só o essencial.
        """
        if not fact_text or len(fact_text) < 200:
            return fact_text
        
        # Remove linhas em branco repetidas
        lines = [l for l in fact_text.splitlines() if l.strip()]
        
        # Junta em blocos lógicos
        result = []
        for line in lines:
            stripped = line.strip()
            # Pula linhas de decoração (só símbolos ou maioria símbolos)
            deco_chars = sum(1 for c in stripped if c in '-=*#_~')
            if deco_chars >= len(stripped) * 0.4:
                continue
            # Pula linhas de separação (só números com decoração)
            if re.match(r'^[\d\s\-=*#_~.]+$', stripped):
                continue
            result.append(stripped)
        
        # Limita tamanho
        joined = " ".join(result)
        if len(joined) > 1000:
            joined = joined[:500] + "\n... [resumo] ...\n" + joined[-500:]
        
        return joined
