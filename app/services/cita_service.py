"""Asignacion de citas segun disponibilidad y prioridad (RF-04)."""
import itertools
from datetime import datetime, timedelta
from typing import Callable

from app.domain.models import Cita, EstadoCita, Franja, Prioridad, Profesional
from app.ports.repositorio import RepositorioPort
from app.services.bitacora import Bitacora

# Dias minimos de espera por prioridad: la urgencia accede a la primera franja libre.
ESPERA_MIN_DIAS = {Prioridad.URGENTE: 0, Prioridad.ALTA: 0, Prioridad.MEDIA: 1, Prioridad.BAJA: 2}


class SinDisponibilidad(Exception):
    pass


class CitaService:
    def __init__(self, citas: RepositorioPort[Cita], franjas: RepositorioPort[Franja],
                 profesionales: RepositorioPort[Profesional], bitacora: Bitacora,
                 reloj: Callable[[], datetime]) -> None:
        self._citas, self._franjas, self._profs = citas, franjas, profesionales
        self._bitacora, self._reloj, self._seq = bitacora, reloj, itertools.count(1)

    def asignar(self, paciente_id: str, sede_id: str, especialidad: str, prioridad: Prioridad,
                triage_id: str | None = None) -> Cita:
        profs = {p.id: p for p in self._profs.listar(
            lambda p: p.sede_id == sede_id and p.especialidad == especialidad)}
        desde = self._reloj() + timedelta(days=ESPERA_MIN_DIAS[prioridad])
        libres = sorted((f for f in self._franjas.listar(
            lambda f: not f.ocupada and f.profesional_id in profs and f.inicio >= desde)),
            key=lambda f: f.inicio)
        if not libres:
            raise SinDisponibilidad(f"Sin franjas libres en {sede_id} para {especialidad}")
        f = libres[0]
        self._franjas.actualizar(f.model_copy(update={"ocupada": True}))
        estado = EstadoCita.PENDIENTE_CONFIRMACION if prioridad.requiere_confirmacion else EstadoCita.CONFIRMADA
        cita = Cita(id=f"C{next(self._seq):04d}", paciente_id=paciente_id, profesional_id=f.profesional_id,
                    sede_id=sede_id, especialidad=especialidad, inicio=f.inicio, prioridad=prioridad,
                    estado=estado, triage_id=triage_id)
        self._citas.agregar(cita)
        self._bitacora.registrar("cita", f"{cita.id} {estado.value} {f.inicio:%Y-%m-%d %H:%M} prof={f.profesional_id}")
        return cita

    def _liberar(self, cita: Cita) -> None:
        for f in self._franjas.listar(lambda f: f.profesional_id == cita.profesional_id and f.inicio == cita.inicio):
            self._franjas.actualizar(f.model_copy(update={"ocupada": False}))

    def cancelar(self, cita_id: str) -> Cita:
        cita = self._citas.obtener(cita_id)
        if cita is None:
            raise KeyError(cita_id)
        self._liberar(cita)
        cita = cita.model_copy(update={"estado": EstadoCita.CANCELADA})
        self._citas.actualizar(cita)
        self._bitacora.registrar("cita", f"{cita.id} cancelada")
        return cita

    def reprogramar(self, cita_id: str) -> Cita:
        vieja = self.cancelar(cita_id)
        return self.asignar(vieja.paciente_id, vieja.sede_id, vieja.especialidad, vieja.prioridad, vieja.triage_id)

    def confirmar(self, cita_id: str) -> Cita:
        cita = self._citas.obtener(cita_id)
        if cita is None:
            raise KeyError(cita_id)
        cita = cita.model_copy(update={"estado": EstadoCita.CONFIRMADA})
        return self._citas.actualizar(cita)

    def ajustar_prioridad(self, cita_id: str, prioridad: Prioridad) -> Cita:
        cita = self._citas.obtener(cita_id)
        if cita is None:
            raise KeyError(cita_id)
        return self._citas.actualizar(cita.model_copy(update={"prioridad": prioridad}))

    def obtener(self, cita_id: str) -> Cita | None:
        return self._citas.obtener(cita_id)

    def listar(self) -> list[Cita]:
        return sorted(self._citas.listar(), key=lambda c: c.inicio)
