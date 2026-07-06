"""G5 Fires — Deterministic trigger sampling.
Em vez de revisar 100% das tarefas que passam no filtro de executor barato,
revisa uma amostra determinística baseada no task_hash.

Isso garante:
- Determinismo: mesma tarefa sempre cai do mesmo lado da amostragem
- Reprodutibilidade: testável com fixture fixa
- Controle contínuo: sample_rate 0.0 a 1.0 em vez de corte binário
"""
from __future__ import annotations

from typing import Optional


def g5_fires(task_hash: str, task_len: int,
              min_task_len: int = 400,
              sample_rate: float = 0.3) -> bool:
    """Decide se o gatilho G5 dispara para esta tarefa.
    
    Args:
        task_hash: Hash SHA256 da tarefa (hex string)
        task_len: Comprimento em caracteres da tarefa
        min_task_len: Threshold mínimo para considerar revisão
        sample_rate: Fração (0.0-1.0) de tarefas que passam no filtro
    
    Returns:
        True se deve revisar, False se pula
    """
    if task_len <= min_task_len:
        return False
    
    # Amostragem determinística: usa os primeiros 8 chars do hash
    bucket = int(task_hash[:8], 16) % 100
    threshold = int(sample_rate * 100)
    
    return bucket < threshold


def g5_should_review(task: str, task_hash: str,
                      executor_provider: str,
                      config: Optional[dict] = None) -> tuple[bool, str]:
    """Versão integrada: verifica se G5 deve disparar.
    
    Args:
        task: Texto da tarefa
        task_hash: Hash da tarefa
        executor_provider: Nome do provider que executou
        config: Dict de config (ou None para defaults)
    
    Returns:
        (deve_revisar, motivo)
    """
    cheap_providers = {"ollama-local", "deepseek-flash"}
    if executor_provider not in cheap_providers:
        return False, "executor não é barato"
    
    if config:
        min_len = config.get("min_task_len", 400)
        rate = config.get("sample_rate", 0.3)
    else:
        min_len = 400
        rate = 0.3
    
    fires = g5_fires(task_hash, len(task), min_len, rate)
    if fires:
        return True, f"G5: executor barato ({executor_provider}), sample_rate={rate}, len={len(task)} > {min_len}"
    
    return False, f"G5: executor barato mas fora da amostra (hash bucket >= {int(rate*100)})"
