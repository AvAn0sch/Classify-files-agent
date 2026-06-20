"""Configuration loader: YAML parsing, env var resolution, validation."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from create_agent.config.models import AppConfig

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR_NAME} placeholders in a string value."""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        env_val = os.environ.get(var_name, "")
        if not env_val:
            print(
                f"Warning: environment variable '{var_name}' is not set, "
                f"used in config value '{value}'"
            )
        return env_val

    return _ENV_VAR_PATTERN.sub(_replace, value)


def _resolve_dict(obj: object) -> object:
    """Recursively resolve env vars in all string values within a dict/list."""
    if isinstance(obj, dict):
        return {k: _resolve_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_dict(item) for item in obj]
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    return obj


def _project_root() -> Path:
    """Return the project root directory (parent of the src/create_agent package)."""
    this_file = Path(__file__).resolve()
    # __file__ is at src/create_agent/config/loader.py
    # Go up 3 levels to reach the project root
    return this_file.parent.parent.parent.parent


def _find_config(config_path: str | None = None) -> Path:
    """Find config file: explicit path > ./config.yaml > project root > ~/.create-agent/."""
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # 1. Current working directory
    cwd_config = Path("config.yaml")
    if cwd_config.exists():
        return cwd_config

    # 2. Project root directory (where pyproject.toml lives)
    root_config = _project_root() / "config.yaml"
    if root_config.exists():
        return root_config

    # 3. User home directory
    home_config = Path.home() / ".create-agent" / "config.yaml"
    if home_config.exists():
        return home_config

    raise FileNotFoundError(
        "No config.yaml found. Place it in one of:\n"
        "  - Current directory\n"
        f"  - Project root: {_project_root()}\n"
        "  - ~/.create-agent/config.yaml\n"
        "Copy config.example.yaml to config.yaml and set your API keys."
    )


def load_config(config_path: str | None = None) -> AppConfig:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Optional explicit path to config file.

    Returns:
        Validated AppConfig instance.

    Raises:
        FileNotFoundError: If no config file can be found.
        pydantic.ValidationError: If config is invalid.
    """
    path = _find_config(config_path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Config file is empty: {path}")

    raw = _resolve_dict(raw)
    return AppConfig.model_validate(raw)
