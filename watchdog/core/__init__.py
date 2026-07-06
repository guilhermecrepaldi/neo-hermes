"""Core do Orquestrador V2 — Router + Cross-Review Council.
Integra Provider Layer, Memória Externa, Compressão e Revisão Cruzada.
"""
from core.council import CrossReviewCouncil, ReviewVerdict
from core.router_v2 import RouterV2

__all__ = ["CrossReviewCouncil", "ReviewVerdict", "RouterV2"]
