"""Pomocné načítání akcí z číslovaných podadresářů."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def load_action_function(module_path: str, function_name: str) -> Any:
    """Načte funkci z modulu, jehož cesta nemusí být platný Python identifikátor."""
    module = import_module(module_path)
    return getattr(module, function_name)
