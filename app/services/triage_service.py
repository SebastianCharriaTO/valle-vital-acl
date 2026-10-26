"""Servicio de triage orientativo. Orquesta: estrategia primaria (IA) + Circuit Breaker + fallback a reglas."""
import itertools
from datetime import datetime
from typing import Callable

from app.domain.models import (Prioridad, RegistroTriage, ResultadoTriage, SolicitudTriage)
from app.ports.asistente_ia import AsistenteIAPort, ProveedorIAError
from app.ports.repositorio import RepositorioPort
from app.resilience.circuit_breaker import CircuitBreaker, CircuitoAbierto
from app.services.bitacora import Bitacora


class TriageService:
    def __init__(self, primario: AsistenteIAPort, fallback: AsistenteIAPort, breaker: CircuitBreaker,
                 repo: RepositorioPort[RegistroTriage], bitacora: Bitacora,
                 reloj: Callable[[], datetime]) -> None:
        self._primario, self._fallback, self._breaker = primario, fallback, breaker
        self._repo, self._bitacora, self._reloj = repo, bitacora, reloj
        self._seq = itertools.count(1)

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def evaluar(self, solicitud: SolicitudTriage) -> ResultadoTriage:
        """Prioridad SUGERIDA. Nunca propaga la falla del proveedor: degrada a reglas (RNF-02)."""
        if self._primario is self._fallback:  # configuracion MOTOR_IA=reglas
            return self._fallback.evaluar(solicitud)
        try:
            return self._breaker.llamar(lambda: self._primario.evaluar(solicitud))
        except (ProveedorIAError, CircuitoAbierto) as exc:
            self._bitacora.registrar("fallback", f"{type(exc).__name__}: {exc}", self._fallback.nombre)
            r = self._fallback.evaluar(solicitud)
            return r.model_copy(update={"explicacion": "[Modo degradado: reglas locales] " + r.explicacion})

    def registrar(self, paciente_id: str, solicitud: SolicitudTriage) -> RegistroTriage:
        resultado = self.evaluar(solicitud)
        reg = RegistroTriage(id=f"T{next(self._seq):04d}", paciente_id=paciente_id, solicitud=solicitud,
                             resultado=resultado, creado=self._reloj())
        self._repo.agregar(reg)
        self._bitacora.registrar(
            "triage", f"{reg.id} paciente={paciente_id} sugerida={resultado.prioridad.value} "
                      f"puntaje={resultado.puntaje}", resultado.motor)
        return reg

    def confirmar(self, triage_id: str, profesional_id: str, prioridad: Prioridad) -> RegistroTriage:
        """Human-in-the-loop (RF-03): el profesional confirma o corrige la prioridad."""
        reg = self._repo.obtener(triage_id)
        if reg is None:
            raise KeyError(triage_id)
        reg = reg.model_copy(update={"prioridad_final": prioridad, "confirmado_por": profesional_id})
        self._repo.actualizar(reg)
        self._bitacora.registrar("confirmacion", f"{triage_id} final={prioridad.value} por={profesional_id}")
        return reg

    def obtener(self, triage_id: str) -> RegistroTriage | None:
        return self._repo.obtener(triage_id)

    def listar(self) -> list[RegistroTriage]:
        return self._repo.listar()
