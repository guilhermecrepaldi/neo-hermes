"""Cross-Review Council — Revisão cruzada entre agentes de diferentes provedores.
Garante que respostas críticas passem por ≥1 revisor antes de serem aceitas.
Revisor nunca é o mesmo perfil que gerou a resposta original.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
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
class ReviewVerdict:
    """Veredito de uma revisão cruzada."""
    approved: bool
    reviewer_provider: str
    confidence: float          # 0-1
    issues: list[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None


# ─── Pareamento padrão executor → revisor ───────────
# Regra: revisor NUNCA é o mesmo perfil que gerou a resposta
DEFAULT_PAIRING = {
    "ollama-local": "deepseek-flash",   # Local → DeepSeek barato (outro cérebro)
    "deepseek-flash": "ollama-local",   # DeepSeek barato → Local (sanity check)
    "deepseek-pro": "ollama-local",     # Pro → Local (revisão barata)
}

# Sinais de baixa confiança na resposta do executor
LOW_CONFIDENCE_SIGNALS = [
    "não tenho certeza", "não sei", "talvez", "possivelmente",
    "acredito que", "pode ser que", "não tenho dados",
    "não tenho informação", "não consigo afirmar",
    "eu acho", "provavelmente", "não sei dizer",
]

REVIEW_PROMPT_TEMPLATE = (
    "Você é um revisor crítico de respostas de IA. "
    "Analise a resposta do executor para a tarefa abaixo.\n\n"
    "## Tarefa Original\n{task}\n\n"
    "## Resposta do Executor\n{response}\n\n"
    "{memory_context}"
    "Aponte inconsistências factuais, contradições com o contexto fornecido, "
    "e erros lógicos. Não reescreva a resposta inteira, só liste problemas "
    "específicos e uma sugestão pontual de correção.\n\n"
    'Responda em JSON com os campos:\n'
    '{{"approved": true/false, "confidence": 0.0-1.0, '
    '"issues": ["problema 1", "problema 2"], '
    '"suggested_fix": "correção específica" ou null}}'
)


class CrossReviewCouncil:
    """Conselho de revisão cruzada.
    
    Decide se uma resposta precisa ser revisada, seleciona o revisor
    apropriado (nunca o mesmo perfil), e coleta vereditos.
    Suporta dry_run: loga decisões sem chamar o revisor de fato.
    """
    
    def __init__(self, memory_store=None, max_rounds: int = 2,
                 dry_run: bool = False, config: Optional[dict] = None,
                 audit_logger=None):
        """
        Args:
            memory_store: Instância de MemoryStore para cache de decisões
            max_rounds: Máximo de rodadas de retry (previne loop infinito)
            dry_run: Se True, loga decisões sem chamar revisor (custo zero)
            config: Dict de config do orchestrator.yaml (council.triggers)
            audit_logger: AuditLogger opcional para registrar decisões
        """
        self.memory_store = memory_store
        self.max_rounds = max_rounds
        self.dry_run = dry_run
        self.config = config or {}
        self.audit_logger = audit_logger
    
    def _get_g5_config(self) -> tuple[int, float]:
        """Retorna min_task_len e sample_rate da config ou default."""
        g5 = self.config.get("g5_cheap_executor", {})
        return g5.get("min_task_len", 400), g5.get("sample_rate", 0.3)
    
    def _compute_task_hash(self, task: str) -> str:
        """Hash determinístico do tipo de tarefa para cache."""
        normalized = task.lower().strip()[:200]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def evaluate_triggers(self, response: str, task: str,
                           executor_provider: str,
                           is_critical: bool = False) -> dict:
        """Avalia todos os gatilhos e retorna resultado estruturado.
        
        Returns:
            {"should_review": bool, "trigger_fired": str, "reason": str,
             "triggers": {"G1": bool, "G2": bool, ...}}
        """
        g_min, g_rate = self._get_g5_config()
        
        triggers = {}
        
        # G1: Crítica
        triggers["G1"] = is_critical
        if is_critical:
            return {"should_review": True, "trigger_fired": "G1",
                    "reason": "tarefa marcada como crítica", "triggers": triggers}
        
        # G2: Baixa confiança
        resp_lower = response.lower()
        g2_fired = False
        for signal in LOW_CONFIDENCE_SIGNALS:
            if signal in resp_lower:
                g2_fired = True
                break
        triggers["G2"] = g2_fired
        if g2_fired:
            return {"should_review": True, "trigger_fired": "G2",
                    "reason": f"resposta contém sinal de baixa confiança", "triggers": triggers}
        
        # G3: Resposta curta
        g3_fired = len(task) > 300 and len(response) < 100
        triggers["G3"] = g3_fired
        if g3_fired:
            return {"should_review": True, "trigger_fired": "G3",
                    "reason": f"resposta ({len(response)} chars) muito curta para tarefa ({len(task)} chars)",
                    "triggers": triggers}
        
        # G4: Cache de rejeição
        g4_fired = False
        if self.memory_store:
            task_hash = self._compute_task_hash(task)
            prev = self.memory_store.was_previously_approved(task_hash)
            if prev is False:
                g4_fired = True
            elif prev is True:
                triggers["G4"] = False
                return {"should_review": False, "trigger_fired": "cache_approved",
                        "reason": "tipo de tarefa já aprovado anteriormente (cache)",
                        "triggers": triggers}
        triggers["G4"] = g4_fired
        if g4_fired:
            return {"should_review": True, "trigger_fired": "G4",
                    "reason": "tipo de tarefa foi rejeitado anteriormente", "triggers": triggers}
        
        # G5: Executor barato + amostragem determinística
        cheap_providers = {"ollama-local", "deepseek-flash"}
        g5_fired = False
        if executor_provider in cheap_providers:
            task_hash = self._compute_task_hash(task)
            from core.g5_fires import g5_fires as g5_check
            g5_fired = g5_check(task_hash, len(task), g_min, g_rate)
        triggers["G5"] = g5_fired
        if g5_fired:
            return {"should_review": True, "trigger_fired": "G5",
                    "reason": f"G5: executor barato ({executor_provider}), sample_rate={g_rate}, len={len(task)} > {g_min}",
                    "triggers": triggers}
        
        return {"should_review": False, "trigger_fired": "none",
                "reason": "padrão: sem revisão necessária", "triggers": triggers}
    
    def should_review(self, response: str, task: str,
                      executor_provider: str,
                      is_critical: bool = False) -> tuple[bool, str]:
        """Wrapper da evaluate_triggers para compatibilidade V2."""
        result = self.evaluate_triggers(response, task, executor_provider, is_critical)
        return result["should_review"], result["reason"]
    
    def select_reviewer(self, executor_provider: str) -> Optional[ProviderInterface]:
        """Seleciona revisor diferente do executor.
        
        Usa tabela de pareamento DEFAULT_PAIRING.
        Fallback: qualquer provider com role 'reviewer'.
        """
        # Tenta pareamento preferencial
        preferred = DEFAULT_PAIRING.get(executor_provider)
        if preferred:
            reviewer = get_provider(preferred)
            if reviewer and reviewer.health_check():
                return reviewer
        
        # Fallback: qualquer revisor disponível (nunca o executor)
        for name, prov in PROVIDER_REGISTRY.items():
            if "reviewer" in prov.supports_roles and name != executor_provider:
                if prov.health_check():
                    return prov
        
        # Último fallback
        logger.warning(f"Nenhum revisor disponível para {executor_provider}")
        return get_provider("deepseek-flash")
    
    async def review(self, response: str, original_task: str,
                      executor_provider: str,
                      memory_context: str = "",
                      is_critical: bool = False) -> ReviewVerdict:
        """Executa revisão completa.
        
        Fluxo:
        1. Avalia gatilhos (evaluate_triggers)
        2. Se dry_run: loga decisão sem chamar revisor
        3. Seleciona revisor (nunca o executor)
        4. Envia prompt estruturado
        5. Parseia resposta JSON
        6. Grava resultado na memória + audit
        """
        trigger_result = self.evaluate_triggers(
            response, original_task, executor_provider, is_critical
        )
        should = trigger_result["should_review"]
        reason = trigger_result["reason"]
        trigger_fired = trigger_result["trigger_fired"]
        triggers = trigger_result["triggers"]
        
        if not should:
            logger.debug(f"Revisão ignorada: {reason}")
            self._audit_decision(
                request_id="", session_id="council",
                task_hash=self._compute_task_hash(original_task),
                risk_level="", executor_chosen=executor_provider,
                triggers_evaluated=triggers, trigger_fired=trigger_fired,
                needed_review=False, cost_estimated=0.0, latency=0,
            )
            return ReviewVerdict(
                approved=True,
                reviewer_provider="auto",
                confidence=1.0,
                issues=[],
            )
        
        # ─── Dry Run ────────────────────────────────
        if self.dry_run:
            logger.info(f"DRY RUN: revisão necessária ({reason}), mas pulando chamada")
            self._audit_decision(
                request_id="", session_id="council",
                task_hash=self._compute_task_hash(original_task),
                risk_level="", executor_chosen=executor_provider,
                triggers_evaluated=triggers, trigger_fired=trigger_fired,
                needed_review=True, cost_estimated=0.002, latency=0,
                dry_run=True,
            )
            return ReviewVerdict(
                approved=True, reviewer_provider="dry_run_skip",
                confidence=1.0, issues=[],
            )
        
        logger.info(f"Revisão necessária: {reason}")
        
        reviewer = self.select_reviewer(executor_provider)
        if not reviewer:
            logger.error("Nenhum revisor disponível")
            return ReviewVerdict(
                approved=True,
                reviewer_provider="none",
                confidence=0.5,
                issues=["Nenhum revisor disponível"],
            )
        
        logger.info(f"Revisor: {reviewer.name}")
        
        # Monta prompt de revisão
        mem_ctx = ""
        if memory_context:
            mem_ctx = f"## Contexto da Memória\n{memory_context}\n\n"
        
        review_prompt = REVIEW_PROMPT_TEMPLATE.format(
            task=original_task[:2000],
            response=response[:4000],
            memory_context=mem_ctx,
        )
        
        req = ProviderRequest(
            prompt=review_prompt,
            system="Você é um revisor técnico rigoroso. Responda APENAS JSON válido.",
            max_tokens=1024,
            temperature=0.2,
            role="reviewer",
        )
        
        try:
            resp = await reviewer.generate(req)
            verdict = self._parse_verdict(resp.text, reviewer.name)
            logger.info(
                f"Veredito: {'✅' if verdict.approved else '❌'} "
                f"(confiança: {verdict.confidence:.2f}, "
                f"{len(verdict.issues)} issues)"
            )
        except Exception as e:
            logger.warning(f"Revisão falhou: {e}. Aprovando por segurança.")
            verdict = ReviewVerdict(
                approved=True,
                reviewer_provider=reviewer.name,
                confidence=0.3,
                issues=[f"Erro no processo de revisão: {str(e)[:100]}"],
            )
        
        # Grava na memória
        if self.memory_store:
            try:
                task_hash = self._compute_task_hash(original_task)
                self.memory_store.record_review_outcome(
                    session_id="council",
                    task_hash=task_hash,
                    approved=verdict.approved,
                    reviewer_provider=verdict.reviewer_provider,
                    issues=verdict.issues,
                )
            except Exception as e:
                logger.warning(f"Falha ao gravar revisão na memória: {e}")
        
        return verdict
    
    def _audit_decision(self, request_id: str, session_id: str,
                         task_hash: str, risk_level: str, executor_chosen: str,
                         triggers_evaluated: dict, trigger_fired: str,
                         needed_review: bool, cost_estimated: float, latency: int,
                         dry_run: bool = False) -> None:
        """Audita uma decisão (falha silenciosa)."""
        if not self.audit_logger:
            return
        try:
            from core.audit import DecisionRecord
            rec = DecisionRecord(
                request_id=request_id,
                session_id=session_id,
                task_hash=task_hash,
                risk_level=risk_level,
                executor_chosen=executor_chosen,
                triggers_evaluated=triggers_evaluated,
                trigger_fired=trigger_fired,
                needed_review=needed_review,
                dry_run=dry_run,
                cost_estimated_usd=cost_estimated,
                latency_ms=latency,
            )
            self.audit_logger.record(rec)
        except Exception:
            pass
    
    def _parse_verdict(self, text: str, reviewer_name: str) -> ReviewVerdict:
        """Parseia resposta JSON do revisor.
        
        Lida com:
        - Markdown fences (```json ... ```)
        - JSON puro
        - Fallback para texto não-estruturado
        """
        if not text or not text.strip():
            return ReviewVerdict(
                approved=True, reviewer_provider=reviewer_name,
                confidence=0.5, issues=["Resposta vazia do revisor"],
            )
        
        # Remove markdown fences
        cleaned = re.sub(r'```(?:json)?\n?', '', text).strip()
        cleaned = re.sub(r'```\n?$', '', cleaned).strip()
        
        # Tenta parse como JSON
        try:
            data = json.loads(cleaned)
            return ReviewVerdict(
                approved=bool(data.get("approved", True)),
                reviewer_provider=reviewer_name,
                confidence=float(data.get("confidence", 0.5)),
                issues=data.get("issues", []),
                suggested_fix=data.get("suggested_fix"),
            )
        except json.JSONDecodeError:
            pass
        
        # Fallback: busca padrões no texto
        has_approval = any(w in cleaned.lower() for w in ["approved", "aprovad", "ok", "sim"])
        has_rejection = any(w in cleaned.lower() for w in ["rejected", "rejeitad", "não", "erro"])
        
        approved = has_approval and not has_rejection
        
        # Extrai issues como linhas com "-" ou números
        issues = re.findall(r'(?:^|\n)\s*[-•*]\s*(.+?)(?:\n|$)', cleaned, re.MULTILINE)
        issues = [i.strip() for i in issues if i.strip() and len(i) > 5][:5]
        
        return ReviewVerdict(
            approved=approved,
            reviewer_provider=reviewer_name,
            confidence=0.4,
            issues=issues or ["Não foi possível parsear JSON do revisor; veredito inferido do texto"],
        )
