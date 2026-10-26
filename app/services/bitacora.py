"""Bitacora de recomendaciones (RF-09): trazabilidad de entradas, motor y resultado."""
import itertools
from datetime import datetime
from typing import Callable

from app.domain.models import EntradaBitacora
from app.ports.repositorio import RepositorioPort


class Bitacora:
    def __init__(self, repo: RepositorioPort[EntradaBitacora], reloj: Callable[[], datetime]) -> None:
        self._repo, self._reloj, self._seq = repo, reloj, itertools.count(1)

    def registrar(self, tipo: str, detalle: str, motor: str | None = None) -> EntradaBitacora:
        e = EntradaBitacora(id=f"B{next(self._seq):05d}", momento=self._reloj(), tipo=tipo,
                            detalle=detalle, motor=motor)
        return self._repo.agregar(e)

    def listar(self, n: int = 50) -> list[EntradaBitacora]:
        return list(reversed(self._repo.listar()))[:n]
