"""Config Loader — Carrega config de YAML com valores default seguros.
Usa PyYAML para parsing (instalado como dependência do ecossistema).
Se o arquivo não existir, retorna defaults — zero breakage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "orchestrator.yaml"

# Defaults seguros — idênticos ao YAML, garantem funcionamento sem arquivo
DEFAULTS = {
    "orchestrator": {
        "use_router_v2": False,
        "use_cross_review": False,
        "use_memory_v2": True,
        "use_compression": True,
        "dry_run_review": True,
        "audit_enabled": True,
    },
    "council": {
        "triggers": {
            "g1_critical": {"enabled": True},
            "g2_low_confidence": {"enabled": True, "keywords": [
                "não tenho certeza", "não sei", "talvez", "possivelmente",
                "acredito que", "pode ser que", "não tenho dados",
            ]},
            "g3_short_response": {"enabled": True, "min_task_len": 300, "max_response_len": 100},
            "g4_rejection_cache": {"enabled": True},
            "g5_cheap_executor": {"enabled": True, "min_task_len": 400, "sample_rate": 0.3},
        }
    },
    "pairing_defaults": {
        "ollama-local": "deepseek-flash",
        "deepseek-flash": "ollama-local",
        "deepseek-pro": "ollama-local",
    },
}


def _load_yaml_simple(path: Path) -> dict:
    """Carrega YAML usando PyYAML com fallback silencioso."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge profundo: override substitui base recursivamente."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_orchestrator_config() -> dict:
    """Carrega config do YAML, faz merge com defaults.
    
    Returns:
        Dicionário completo com defaults + overrides do YAML.
    """
    yaml_config = _load_yaml_simple(CONFIG_PATH)
    merged = _deep_merge(DEFAULTS, yaml_config)
    return merged


def get_config_value(key_path: str, default=None) -> Any:
    """Acessa config por path pontilhado (ex: 'council.triggers.g5_cheap_executor.min_task_len')."""
    config = load_orchestrator_config()
    parts = key_path.split(".")
    current = config
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return default
    return current if current is not None else default
