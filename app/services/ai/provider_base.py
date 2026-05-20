"""Interfaces genericas para proveedores AI."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Contrato minimo para cualquier backend de generacion AI."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Devuelve la respuesta cruda del proveedor para un prompt."""
