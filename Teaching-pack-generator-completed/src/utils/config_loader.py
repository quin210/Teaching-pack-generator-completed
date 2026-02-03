from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml


def load_config(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def get_config_value(config: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    cur: Any = config
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def resolve_value(arg_value: Any, config: Dict[str, Any], keys: Iterable[str], default: Any) -> Any:
    if arg_value is not None:
        return arg_value
    cfg_value = get_config_value(config, keys, default=None)
    return default if cfg_value is None else cfg_value
