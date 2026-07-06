"""Hot-reload de providers.yaml — adiciona providers sem restart.
Além dos providers em si, carrega o pareamento executor→revisor do YAML.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from providers.registry import PROVIDER_REGISTRY, register_provider

try:
    from logger_pro import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


PROVIDERS_YAML = Path(__file__).resolve().parent.parent / "config" / "providers.yaml"

# Cache do último estado carregado
_last_loaded: dict = {}


def _parse_yaml_providers(path: Path) -> dict:
    """Parser simplificado para ler providers.yaml."""
    if not path.exists():
        logger.warning(f"Arquivo não encontrado: {path}")
        return {"providers": {}, "pairing_defaults": {}}
    
    result = {"providers": {}, "pairing_defaults": {}}
    text = path.read_text(encoding="utf-8")
    
    current_section = None
    current_provider = None
    
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            continue
        
        if stripped.rstrip(":").strip() in ("providers", "pairing_defaults"):
            current_section = stripped.rstrip(":").strip()
            current_provider = None
            continue
        
        if current_section == "providers":
            if not stripped.startswith(" ") and stripped.endswith(":"):
                current_provider = stripped.rstrip(":").strip()
                if current_provider not in result["providers"]:
                    result["providers"][current_provider] = {}
                continue
            if current_provider and ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                # Strip trailing inline comment (e.g. "4096  # max tokens")
                if " #" in value:
                    value = value.split(" #")[0].strip()
                # Converte tipos
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                result["providers"][current_provider][key] = value
        
        elif current_section == "pairing_defaults":
            if ":" in stripped and not stripped.startswith("#"):
                key, _, value = stripped.partition(":")
                result["pairing_defaults"][key.strip()] = value.strip().strip("\"'")
    
    return result


def reload_from_yaml(path: Optional[str] = None) -> list[str]:
    """Recarrega providers.yaml e atualiza PROVIDER_REGISTRY.
    
    Para cada entrada no YAML:
    - Se já existe no registry: atualiza custo/roles in-place
    - Se é nova: tenta instanciar e registrar
    
    Returns:
        Lista de providers adicionados/atualizados
    """
    global _last_loaded
    
    yaml_path = Path(path) if path else PROVIDERS_YAML
    config = _parse_yaml_providers(yaml_path)
    providers_config = config.get("providers", {})
    pairing = config.get("pairing_defaults", {})
    
    changes = []
    
    for name, cfg in providers_config.items():
        if name in PROVIDER_REGISTRY:
            # Já existe — só loga
            changes.append(f"{name}: já registrado")
            logger.debug(f"Provider {name} já existe no registry")
        else:
            # Novo — tenta instanciar
            try:
                class_path = cfg.get("class", "")
                if not class_path:
                    logger.warning(f"Provider {name} sem 'class:', pulando")
                    continue
                
                # Tenta importar e instanciar
                module_path, _, class_name = class_path.rpartition(".")
                if module_path:
                    import importlib
                    try:
                        module = importlib.import_module(module_path)
                        cls = getattr(module, class_name)
                        
                        # Constrói kwargs
                        kwargs = {}
                        if "profile" in cfg:
                            kwargs["profile"] = cfg["profile"]
                        if "model" in cfg:
                            kwargs["model"] = cfg["model"]
                        
                        instance = cls(**kwargs)
                        register_provider(name, instance)
                        changes.append(f"{name}: registrado ({class_path})")
                        logger.info(f"Novo provider registrado via hot-reload: {name}")
                    except Exception as e:
                        logger.warning(f"Falha ao instanciar {class_path}: {e}")
                        changes.append(f"{name}: erro - {e}")
            except Exception as e:
                logger.warning(f"Falha ao processar {name}: {e}")
                changes.append(f"{name}: erro - {e}")
    
    # Atualiza pairing defaults no council
    if pairing:
        try:
            from core.council import DEFAULT_PAIRING
            for executor, reviewer in pairing.items():
                if executor not in PROVIDER_REGISTRY:
                    logger.warning(f"Pairing: executor {executor} não está no registry")
                    continue
                if reviewer not in PROVIDER_REGISTRY:
                    logger.warning(f"Pairing: reviewer {reviewer} não está no registry")
                    continue
                DEFAULT_PAIRING[executor] = reviewer
                changes.append(f"pairing: {executor} → {reviewer}")
            logger.info(f"Pairing defaults atualizados: {len(pairing)} pares")
        except Exception as e:
            logger.warning(f"Falha ao atualizar pairing: {e}")
    
    _last_loaded = config
    return changes


def get_pairing_defaults() -> dict:
    """Retorna o pareamento atual."""
    return dict(_last_loaded.get("pairing_defaults", {}))


def main():
    """CLI: reload e mostra resultado."""
    changes = reload_from_yaml()
    print("=== Hot-Reload de Providers ===")
    for c in changes:
        print(f"  {c}")
    print(f"\nRegistry atual: {list(PROVIDER_REGISTRY.keys())}")
    return 0


if __name__ == "__main__":
    main()
