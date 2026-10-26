"""Patron Circuit Breaker (Microsoft, 2025): estados CERRADO -> ABIERTO -> SEMIABIERTO."""
import time
from enum import Enum
from typing import Callable, TypeVar

R = TypeVar("R")


class EstadoCircuito(str, Enum):
    CERRADO = "cerrado"
    ABIERTO = "abierto"
    SEMIABIERTO = "semiabierto"


class CircuitoAbierto(Exception):
    """El circuito esta abierto: la llamada ni siquiera se intenta."""


class CircuitBreaker:
    def __init__(self, umbral_fallos: int = 3, segundos_recuperacion: float = 30.0,
                 reloj: Callable[[], float] = time.monotonic,
                 excepciones: tuple[type[BaseException], ...] = (Exception,)) -> None:
        self.umbral = umbral_fallos
        self.recuperacion = segundos_recuperacion
        self._reloj = reloj
        self._excepciones = excepciones
        self._fallos = 0
        self._abierto_desde: float | None = None
        self._estado = EstadoCircuito.CERRADO

    @property
    def estado(self) -> EstadoCircuito:
        if self._estado is EstadoCircuito.ABIERTO and self._abierto_desde is not None \
                and self._reloj() - self._abierto_desde >= self.recuperacion:
            self._estado = EstadoCircuito.SEMIABIERTO
        return self._estado

    @property
    def fallos(self) -> int:
        return self._fallos

    def llamar(self, fn: Callable[[], R]) -> R:
        if self.estado is EstadoCircuito.ABIERTO:
            raise CircuitoAbierto("circuito abierto")
        try:
            resultado = fn()
        except self._excepciones:
            self._registrar_fallo()
            raise
        self._registrar_exito()
        return resultado

    def _registrar_fallo(self) -> None:
        self._fallos += 1
        if self._estado is EstadoCircuito.SEMIABIERTO or self._fallos >= self.umbral:
            self._estado = EstadoCircuito.ABIERTO
            self._abierto_desde = self._reloj()

    def _registrar_exito(self) -> None:
        self._fallos = 0
        self._abierto_desde = None
        self._estado = EstadoCircuito.CERRADO
