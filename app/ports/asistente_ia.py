"""PUERTO (hexagonal): contrato que el dominio exige a cualquier motor de IA.
El dominio solo conoce esta interfaz (ocultamiento de informacion, Parnas)."""
from abc import ABC, abstractmethod

from app.domain.models import ResultadoTriage, SolicitudTriage


class ProveedorIAError(Exception):
    """Falla del proveedor externo (red, cuota, tiempo de espera...)."""


class AsistenteIAPort(ABC):
    nombre: str = "desconocido"

    @abstractmethod
    def evaluar(self, solicitud: SolicitudTriage) -> ResultadoTriage:
        """Devuelve una prioridad SUGERIDA. Puede lanzar ProveedorIAError."""
