"""Memória Externa — SQLite persistente + embeddings Ollama para busca semântica.
Fatos compartilhados entre agentes, revisões, e ledger de custos.
"""
from memory.store import MemoryStore, MemoryFact
from memory.compressor import ContextCompressor

__all__ = ["MemoryStore", "MemoryFact", "ContextCompressor"]
