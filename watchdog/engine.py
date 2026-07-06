#!/usr/bin/env python3
"""Hermes Agent Engine — Context, Subagents, Checkpoints, Hooks, Cache.

Motor de servicos do Hermes 2.0: tudo que nao e loop puro nem harness.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Logger setup
try:
    from logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# CONTEXT ENGINEERING — hermes-progress.md
# ═══════════════════════════════════════════════

PROGRESS_FILE = ROOT / "hermes-progress.md"


def carregar_progresso() -> dict:
    """Carrega estado da sessao do hermes-progress.md."""
    if not PROGRESS_FILE.exists():
        return {"feito": [], "pendente": [], "artefatos": [],
                "ultima_sessao": ""}
    try:
        texto = PROGRESS_FILE.read_text(encoding="utf-8")
        estado = {"feito": [], "pendente": [],
                  "artefatos": [], "ultima_sessao": texto[:200]}
        for line in texto.split("\n"):
            l = line.strip()
            if l.startswith("- [x]") or l.startswith("- [X]"):
                estado["feito"].append(l[5:].strip())
            elif l.startswith("- [ ]"):
                estado["pendente"].append(l[5:].strip())
            elif l.startswith("  -"):
                estado["artefatos"].append(l.strip())
        return estado
    except Exception:
        return {"feito": [], "pendente": [],
                "artefatos": [], "ultima_sessao": ""}


def salvar_progresso(acao: str, resultado: str) -> None:
    """Registra progresso no hermes-progress.md."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- {ts}: {acao} -> {resultado[:80]}"
    try:
        if PROGRESS_FILE.exists():
            texto = PROGRESS_FILE.read_text(encoding="utf-8")
        else:
            texto = "# Hermes Progress\n\n"
        texto += f"\n{entry}"
        PROGRESS_FILE.write_text(texto, encoding="utf-8")
    except Exception:
        pass


# ═══════════════════════════════════════════════
# SUBAGENT SPAWNING — git worktrees
# ═══════════════════════════════════════════════

def criar_worktree(nome: str) -> dict:
    """Cria subagent isolado via git worktree."""
    path = ROOT / f"../subagents/{nome}"
    branch = f"agent/{nome}"
    try:
        r = subprocess.run(["git", "worktree", "list"],
                           capture_output=True, text=True,
                           cwd=str(ROOT), timeout=10)
        if nome in r.stdout:
            return {"status": "existente", "path": str(path)}

        subprocess.run(["git", "branch", "-f", branch, "main"],
                       capture_output=True, cwd=str(ROOT), timeout=10)
        r = subprocess.run(["git", "worktree", "add", str(path), branch],
                           capture_output=True, text=True,
                           cwd=str(ROOT), timeout=15)
        if r.returncode == 0:
            return {"status": "criado", "path": str(path), "branch": branch}
        return {"status": "erro", "erro": r.stderr[:200]}
    except Exception as e:
        return {"status": "erro", "erro": str(e)}


def remover_worktree(nome: str) -> dict:
    """Remove subagent (worktree)."""
    path = ROOT / f"../subagents/{nome}"
    branch = f"agent/{nome}"
    try:
        subprocess.run(["git", "worktree", "remove", str(path)],
                       capture_output=True, cwd=str(ROOT), timeout=10)
        subprocess.run(["git", "branch", "-D", branch],
                       capture_output=True, cwd=str(ROOT), timeout=5)
        return {"status": "removido"}
    except Exception as e:
        return {"status": "erro", "erro": str(e)}


# ═══════════════════════════════════════════════
# INITIALIZER + CODING AGENT PATTERN
# ═══════════════════════════════════════════════

class InitializerAgent:
    """Setup e planejamento."""

    @staticmethod
    def setup(descricao: str) -> dict:
        logger.info(f"Initializer: {descricao[:60]}...")
        salvar_progresso("INIT", descricao)
        return {
            "status": "setup_ok",
            "context": {
                "descricao": descricao,
                "rules": [
                    "Usar taste-skill: 10 regras",
                    "Sem paths hardcoded",
                    "Nao quebrar funcional",
                    "Commit a cada passo"
                ]
            }
        }


class CodingAgent:
    """Execucao incremental."""

    @staticmethod
    def plan_and_execute(setup: dict) -> list:
        logger.info("CodingAgent: plan_and_execute")
        carregar_progresso()
        plan = [
            f"1. {setup['context']['descricao'][:50]}",
            "2. Implementar com type hints",
            "3. Escrever testes pytest",
            "4. Verificar quality gate (taste-skill)",
            "5. Commit"
        ]
        salvar_progresso("PLAN", "; ".join(plan))
        return plan


# ═══════════════════════════════════════════════
# CHECKPOINTING + AUTO-COMPACTION
# ═══════════════════════════════════════════════

class CheckpointManager:
    """Gere checkpoints de estado."""

    DIR = ROOT / ".hermes" / "checkpoints"

    @classmethod
    def save(cls, nome: str = "auto") -> dict:
        cls.DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = cls.DIR / f"{nome}_{ts}.json"
        estado = {
            "nome": nome,
            "timestamp": ts,
            "progresso": carregar_progresso(),
        }
        try:
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True,
                               cwd=str(ROOT), timeout=5)
            estado["git_hash"] = r.stdout.strip()
        except Exception:
            estado["git_hash"] = "unknown"
        path.write_text(json.dumps(estado, indent=2), encoding="utf-8")
        logger.info(f"Checkpoint salvo: {path.name}")
        salvar_progresso("CHECKPOINT", path.name)
        return {"status": "ok", "path": str(path), "hash": estado["git_hash"]}

    @classmethod
    def list(cls) -> list:
        if not cls.DIR.exists():
            return []
        return sorted([p.name for p in cls.DIR.glob("*.json")], reverse=True)

    @classmethod
    def auto_compact(cls, max_cp: int = 10) -> dict:
        cps = cls.list()
        if len(cps) <= max_cp:
            return {"removidos": 0, "mantidos": len(cps)}
        for nome in cps[max_cp:]:
            (cls.DIR / nome).unlink(missing_ok=True)
        logger.info(f"Auto-compact: removidos {len(cps) - max_cp}, mantidos {max_cp}")
        return {"removidos": len(cps) - max_cp, "mantidos": max_cp}


# ═══════════════════════════════════════════════
# HOOKS EXECUTION
# ═══════════════════════════════════════════════

class HookManager:
    """Gere hooks pre/post para ferramentas."""

    _hooks: Dict[str, Dict[str, list]] = {"pre": {}, "post": {}}

    @classmethod
    def register(cls, hook_type: str, tool: str, fn) -> None:
        if tool not in cls._hooks[hook_type]:
            cls._hooks[hook_type][tool] = []
        cls._hooks[hook_type][tool].append(fn)
        logger.debug(f"Hook {hook_type}/{tool} registrado")

    @classmethod
    def execute(cls, hook_type: str, tool: str,
                ctx: dict) -> dict:
        hooks = cls._hooks.get(hook_type, {}).get(tool, [])
        results = []
        for fn in hooks:
            try:
                results.append(fn(ctx))
            except Exception as e:
                logger.error(f"Hook {hook_type}/{tool}: {e}")
                results.append({"error": str(e)})
        return {"executed": len(results), "results": results}

    @classmethod
    def setup_default(cls) -> None:
        def pre_patch(ctx):
            p = ctx.get("path", "")
            if p and not os.path.exists(p):
                return {"warning": f"Arquivo nao existe: {p}"}
            return {"status": "ok"}
        def post_terminal(ctx):
            ec = ctx.get("exit_code", -1)
            if ec != 0:
                return {"warning": f"Exit code {ec}"}
            return {"status": "ok"}
        cls.register("pre", "patch", pre_patch)
        cls.register("post", "terminal", post_terminal)
        logger.info("Default hooks configurados")


# ═══════════════════════════════════════════════
# KV CACHE
# ═══════════════════════════════════════════════

class KVCache:
    """Cache compartilhado entre sub-agents."""

    _cache: Dict[str, dict] = {}
    _max_size = 100

    @classmethod
    def get(cls, key: str) -> Any:
        entry = cls._cache.get(key)
        if entry and entry.get("expires", 0) > datetime.now().timestamp():
            return entry["value"]
        return None

    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 300) -> None:
        cls._cache[key] = {
            "value": value,
            "expires": datetime.now().timestamp() + ttl
        }
        if len(cls._cache) > cls._max_size:
            cls._compact()

    @classmethod
    def _compact(cls) -> None:
        now = datetime.now().timestamp()
        expired = [k for k, v in cls._cache.items()
                   if v.get("expires", 0) < now]
        for k in expired:
            del cls._cache[k]
        if len(cls._cache) > cls._max_size:
            items = sorted(cls._cache.items(),
                           key=lambda x: x[1].get("expires", 0),
                           reverse=True)
            cls._cache = dict(items[:cls._max_size])


# ═══════════════════════════════════════════════
# V3 INTEGRATION — Feature flags + RouterV2 hook
# ═══════════════════════════════════════════════
# Ativação segura: com flags false, comportamento = 100% original.
# Controlado por config/orchestrator.yaml.
# ═══════════════════════════════════════════════

# Carrega config (se falhar, defaults seguros)
_V3_CONFIG = {}
try:
    from core.config_loader import load_orchestrator_config
    _V3_CONFIG = load_orchestrator_config()
except Exception:
    pass

_ORCH_CFG = _V3_CONFIG.get("orchestrator", {}) if _V3_CONFIG else {}

# Inicializa componentes V3 (lazy, só se configurados)
_router_v2 = None
_audit_v3 = None
_store_v3 = None

if _ORCH_CFG.get("audit_enabled", True):
    try:
        from core.audit import AuditLogger
        _audit_v3 = AuditLogger()
        logger.info("V3: AuditLogger ativo")
    except Exception as e:
        logger.warning(f"V3: AuditLogger falhou: {e}")

if _ORCH_CFG.get("use_memory_v2", True):
    try:
        from memory.store import MemoryStore
        _store_v3 = MemoryStore()
    except Exception:
        pass

if _ORCH_CFG.get("use_router_v2", False):
    try:
        from core.router_v2 import RouterV2
        _router_v2 = RouterV2(
            memory_store=_store_v3,
            audit_logger=_audit_v3,
            config=_V3_CONFIG,
            dry_run=_ORCH_CFG.get("dry_run_review", True),
        )
        logger.info("V3: RouterV2 ativo (feature flag ON)")
    except Exception as e:
        logger.warning(f"V3: RouterV2 falhou ao inicializar: {e}")


async def processar_tarefa(task: str, system_prompt: str = None,
                            is_critical: bool = False,
                            session_id: str = "default") -> dict:
    """Processa uma tarefa usando o RouterV2 (se ativo) ou comportamento original.
    
    Feature flag `orchestrator.use_router_v2` em config/orchestrator.yaml:
    - true: usa RouterV2.execute() com revisão, memória, compressão
    - false: usa shellz original (comportamento 100% preservado)
    
    Args:
        task: Texto da tarefa
        system_prompt: System prompt opcional
        is_critical: Se é tarefa crítica
        session_id: Sessão para isolamento de memória/custo
    
    Returns:
        Dict com resultado + metadados
    """
    if _router_v2 is not None:
        return await _router_v2.execute(
            task=task,
            system_prompt=system_prompt,
            is_critical=is_critical,
            session_id=session_id,
        )
    
    # Comportamento original: chama shellz
    logger.info("V3: RouterV2 desligado, usando shellz original")
    try:
        from shellz import rotear_obrigatorio
        decision = rotear_obrigatorio(task)
        return {
            "response": f"Roteado para {decision.shell} ({decision.provider}:{decision.model})",
            "decision": {
                "provider": decision.provider,
                "model": decision.model,
                "risk": "unknown",
                "cost_estimate": decision.cost_per_1m / 1_000_000,
                "needed_review": False,
            },
            "verdict": {"approved": True, "reviewer": "legacy"},
            "cost": {"usd": 0.0},
            "performance": {"provider": "legacy"},
        }
    except Exception as e:
        logger.error(f"processar_tarefa (legacy) falhou: {e}")
        return {"error": str(e)}


def v3_status() -> dict:
    """Retorna status dos componentes V3."""
    return {
        "router_v2": _router_v2 is not None,
        "audit": _audit_v3 is not None,
        "memory_v2": _store_v3 is not None,
        "config_keys": list(_V3_CONFIG.keys()) if _V3_CONFIG else [],
        "flags": {
            "use_router_v2": _ORCH_CFG.get("use_router_v2", False),
            "use_cross_review": _ORCH_CFG.get("use_cross_review", False),
            "use_memory_v2": _ORCH_CFG.get("use_memory_v2", True),
            "use_compression": _ORCH_CFG.get("use_compression", True),
            "dry_run_review": _ORCH_CFG.get("dry_run_review", True),
            "audit_enabled": _ORCH_CFG.get("audit_enabled", True),
        },
    }


# ═══════════════════════════════════════════════
# EXPORT (atualizado com V3)
# ═══════════════════════════════════════════════

__all__ = [
    "carregar_progresso", "salvar_progresso",
    "criar_worktree", "remover_worktree",
    "InitializerAgent", "CodingAgent",
    "CheckpointManager", "HookManager", "KVCache",
    "processar_tarefa", "v3_status",
]
