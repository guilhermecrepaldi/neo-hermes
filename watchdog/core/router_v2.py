"""Router Econômico v2 — Integra Provider Layer, Revisão, e Memória Externa.
Estende o shellz.py existente com:
- Decisão de roteamento por custo + risco
- Revisão condicional via Council
- Registro de custo por papel (executor/reviewer/compressor)
- Cache de decisão via memória externa
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from providers.base import ProviderInterface, ProviderRequest
from providers.registry import PROVIDER_REGISTRY, get_provider

try:
    from logger_pro import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    """Decisão completa de roteamento para uma tarefa."""
    provider_name: str          # deepseek-flash | deepseek-pro | ollama-local
    model_name: str             # deepseek-v4-flash | deepseek-v4-pro | qwen2.5-coder:7b
    role: str                   # executor | reviewer | compressor
    cost_estimate: float        # USD estimado
    needs_review: bool          # Se precisa de revisão cruzada
    task_hash: str              # Hash para cache de decisão
    risk_level: str             # low | medium | high


class RouterV2:
    """Router Econômico v2.
    
    Decide como executar cada tarefa baseado em:
    1. Risco (high → quality provider, revisão obrigatória)
    2. Custo (low risk → Ollama local, custo zero)
    3. Cache de memória (tarefas já aprovadas pulam revisão)
    4. Complexidade (tarefas longas com executor barato → revisão)
    """
    
    def __init__(self, memory_store=None, council=None,
                 audit_logger=None, config: Optional[dict] = None,
                 dry_run: bool = False):
        """
        Args:
            memory_store: Instância de MemoryStore para cache
            council: Instância de CrossReviewCouncil
            audit_logger: AuditLogger para registrar decisões
            config: Dict de config (orchestrator.yaml)
            dry_run: Se True, revisão em modo dry-run (custo zero)
        """
        self.memory_store = memory_store
        self.audit_logger = audit_logger
        self.config = config or {}
        self.dry_run = dry_run
        
        # Obtém flags de ativação do config
        orch_cfg = config.get("orchestrator", {}) if config else {}
        self._use_cross_review = orch_cfg.get("use_cross_review", False)
        # dry_run_review sobrescreve dry_run se explícito
        if orch_cfg.get("dry_run_review", True):
            self.dry_run = True
        
        if council:
            self.council = council
        else:
            from core.council import CrossReviewCouncil
            self.council = CrossReviewCouncil(
                memory_store=memory_store,
                dry_run=self.dry_run,
                config=(config or {}).get("council", {}).get("triggers", {}),
                audit_logger=audit_logger,
            )
    
    def _compute_task_hash(self, task: str) -> str:
        """Hash determinístico do tipo de tarefa."""
        normalized = task.lower().strip()[:200]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def classify_risk(self, task: str) -> str:
        """Classifica risco da tarefa (low/medium/high).
        
        High risk: produção, finanças, segurança, dados pessoais
        Medium risk: código novo, análise, refatoração
        Low risk: comandos locais, consultas simples
        """
        t = task.lower()
        
        high_risk = [
            "produção", "production", "deploy", "prod",
            "financeiro", "financial", "pagamento", "payment",
            "segurança", "security", "senha", "password",
            "cripto", "crypto", "dado pessoal", "pii",
            "banco", "bank", "crítico", "critical",
        ]
        for kw in high_risk:
            if kw in t:
                return "high"
        
        medium_risk = [
            "código", "code", "implementar", "implement",
            "analisar", "analyze", "refatorar", "refactor",
            "arquitetura", "architecture", "design",
            "api", "endpoint", "módulo", "module",
        ]
        for kw in medium_risk:
            if kw in t:
                return "medium"
        
        return "low"
    
    def select_executor(self, task: str,
                        risk_level: Optional[str] = None) -> Optional[ProviderInterface]:
        """Seleciona o melhor executor baseado em custo e risco."""
        if risk_level is None:
            risk_level = self.classify_risk(task)
        
        # High risk → deepseek-pro (qualidade máxima)
        if risk_level == "high":
            prov = get_provider("deepseek-pro")
            if prov and prov.health_check():
                return prov
        
        # Medium risk → deepseek-flash (bom custo-benefício)
        if risk_level == "medium":
            prov = get_provider("deepseek-flash")
            if prov and prov.health_check():
                return prov
        
        # Low risk → ollama-local (custo zero)
        prov = get_provider("ollama-local")
        if prov and prov.health_check():
            return prov
        
        # Fallback
        return get_provider("deepseek-flash")
    
    def decide(self, task: str, is_critical: bool = False) -> RouterDecision:
        """Toma decisão de roteamento para uma tarefa.
        
        Returns:
            RouterDecision com provider, custo, necessidade de revisão
        """
        risk = self.classify_risk(task)
        executor = self.select_executor(task, risk)
        
        if executor is None:
            executor = get_provider("deepseek-flash")
        
        task_hash = self._compute_task_hash(task)
        tokens_est = max(len(task) // 4, 1)
        
        # Precisa revisar? Verifica config flag primeiro
        if not self._use_cross_review:
            needs_review = False
        else:
            needs_review = is_critical or risk == "high"
            if not needs_review and self.memory_store:
                prev = self.memory_store.was_previously_approved(task_hash)
                if prev is False:
                    needs_review = True
        
        # Estima custo
        cost = executor.estimate_cost(tokens_est, tokens_est // 2)
        
        return RouterDecision(
            provider_name=executor.name,
            model_name=getattr(executor, '_model', executor.name),
            role="executor",
            cost_estimate=cost,
            needs_review=needs_review,
            task_hash=task_hash,
            risk_level=risk,
        )
    
    async def execute(self, task: str, system_prompt: Optional[str] = None,
                       is_critical: bool = False,
                       session_id: str = "default",
                       max_review_rounds: int = 2) -> dict:
        """Executa tarefa completa com o fluxo V2.
        
        Fluxo:
        1. Router decide provedor + necessidade de revisão
        2. Executor gera resposta
        3. Council revisa (se necessário, máx N rounds)
        4. Grava na memória externa
        5. Retorna resultado + metadados de custo
        """
        decision = self.decide(task, is_critical)
        executor = get_provider(decision.provider_name)
        
        if not executor:
            return {"error": f"Provider {decision.provider_name} não encontrado",
                    "decision": decision}
        
        logger.info(f"Router: {decision.provider_name} | risco={decision.risk_level} | "
                    f"revisão={'sim' if decision.needs_review else 'não'}")
        
        # ─── Executa ─────────────────────────────────
        req = ProviderRequest(
            prompt=task,
            system=system_prompt,
            max_tokens=4096,
            temperature=0.3 if decision.risk_level == "high" else 0.7,
            role="executor",
        )
        
        start = time.time()
        try:
            response = await executor.generate(req)
        except Exception as e:
            err = f"Executor {decision.provider_name} falhou: {e}"
            logger.error(err)
            return {"error": err, "decision": decision}
        
        duration_ms = int((time.time() - start) * 1000)
        current_response = response.text
        
        # ─── Revisão (se necessário) ─────────────────
        rounds = 0
        final_verdict = None
        
        if decision.needs_review:
            while rounds < max_review_rounds:
                # Busca contexto da memória para o revisor
                memory_context = ""
                if self.memory_store:
                    try:
                        facts = self.memory_store.retrieve_relevant(
                            session_id, task, top_k=3
                        )
                        if facts:
                            memory_context = "\n".join(
                                f"- {f.fact_text}" for f in facts
                            )
                    except Exception:
                        pass
                
                verdict = await self.council.review(
                    response=current_response,
                    original_task=task,
                    executor_provider=decision.provider_name,
                    memory_context=memory_context,
                    is_critical=is_critical,
                )
                
                final_verdict = verdict
                
                if verdict.approved:
                    break
                
                # Retry com correções
                rounds += 1
                if rounds < max_review_rounds and verdict.suggested_fix:
                    issues_text = "\n".join(f"- {i}" for i in verdict.issues)
                    retry_task = (
                        f"{task}\n\n"
                        f"## Issues da Revisão Anterior\n{issues_text}\n\n"
                        f"## Correção Sugerida\n{verdict.suggested_fix}\n\n"
                        "Por favor, corrija os pontos acima e gere uma nova resposta "
                        "corrigindo especificamente cada issue apontado."
                    )
                    req = ProviderRequest(
                        prompt=retry_task,
                        system=system_prompt,
                        max_tokens=4096,
                        temperature=0.3,
                        role="executor",
                    )
                    try:
                        response = await executor.generate(req)
                        current_response = response.text
                    except Exception:
                        break
        
        # ─── Grava na memória externa ───────────────
        if self.memory_store:
            try:
                # Fato comprimido
                fact_text = (
                    f"Tarefa [{decision.risk_level}]: {task[:200]} → "
                    f"Provider: {decision.provider_name} | "
                    f"Custo: ${response.cost_usd:.6f} | "
                    f"Revisão: {'aprovada' if final_verdict and final_verdict.approved else 'não revisada'}"
                )
                self.memory_store.add_fact(
                    session_id=session_id,
                    fact_text=fact_text[:500],
                    source_provider=decision.provider_name,
                    source_role="executor",
                    importance=0.7 if (not final_verdict or final_verdict.approved) else 0.4,
                )
                
                # Cost ledger
                self.memory_store.record_cost(
                    session_id=session_id,
                    provider_name=decision.provider_name,
                    role="executor",
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    cost_usd=response.cost_usd,
                )
                
                if final_verdict:
                    self.memory_store.record_cost(
                        session_id=session_id,
                        provider_name=final_verdict.reviewer_provider,
                        role="reviewer",
                        tokens_in=response.tokens_in // 2,  # approx
                        tokens_out=len(final_verdict.issues),
                        cost_usd=0,  # revisão com Ollama = $0
                    )
            except Exception as e:
                logger.warning(f"Falha ao gravar na memória: {e}")
        
        return {
            "success": True,
            "response": current_response,
            "decision": {
                "provider": decision.provider_name,
                "model": decision.model_name,
                "risk": decision.risk_level,
                "cost_estimate": decision.cost_estimate,
                "needed_review": decision.needs_review,
            },
            "verdict": {
                "approved": final_verdict.approved if final_verdict else True,
                "reviewer": final_verdict.reviewer_provider if final_verdict else "auto",
                "confidence": final_verdict.confidence if final_verdict else 1.0,
                "issues": final_verdict.issues if final_verdict else [],
                "rounds": rounds,
            },
            "cost": {
                "usd": response.cost_usd,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
            },
            "performance": {
                "duration_ms": duration_ms,
                "provider": decision.provider_name,
            },
        }
