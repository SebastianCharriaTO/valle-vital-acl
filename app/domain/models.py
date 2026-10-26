"""Modelo de dominio. Todos los datos del prototipo son SINTETICOS (personas ficticias)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Prioridad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

    @property
    def requiere_confirmacion(self) -> bool:
        return self in (Prioridad.ALTA, Prioridad.URGENTE)


class Sede(BaseModel):
    id: str
    nombre: str
    municipio: str


class Profesional(BaseModel):
    id: str
    nombre: str
    especialidad: str
    sede_id: str


class Paciente(BaseModel):
    id: str
    nombre: str  # nombre FICTICIO
    edad: int = Field(ge=0, le=120)


class SolicitudTriage(BaseModel):
    sintomas: list[str] = Field(min_length=1, description="Sintomas del catalogo o texto libre")
    edad: int = Field(ge=0, le=120)
    dias_evolucion: int = Field(default=1, ge=0, le=365)
    temperatura_c: Optional[float] = Field(default=None, ge=30, le=45)


class ResultadoTriage(BaseModel):
    prioridad: Prioridad
    puntaje: int
    explicacion: str
    motor: str
    requiere_confirmacion: bool
    advertencia: str = (
        "Orientacion automatizada de caracter academico: no es un diagnostico. "
        "La decision clinica corresponde al profesional de la salud."
    )


class RegistroTriage(BaseModel):
    id: str
    paciente_id: str
    solicitud: SolicitudTriage
    resultado: ResultadoTriage
    prioridad_final: Optional[Prioridad] = None
    confirmado_por: Optional[str] = None
    creado: datetime


class EstadoCita(str, Enum):
    PENDIENTE_CONFIRMACION = "pendiente_confirmacion"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


class Cita(BaseModel):
    id: str
    paciente_id: str
    profesional_id: str
    sede_id: str
    especialidad: str
    inicio: datetime
    prioridad: Prioridad
    estado: EstadoCita
    triage_id: Optional[str] = None


class Franja(BaseModel):
    id: str
    profesional_id: str
    inicio: datetime
    ocupada: bool = False


class Medicamento(BaseModel):
    id: str
    nombre: str


class InventarioSede(BaseModel):
    id: str  # "<sede_id>:<medicamento_id>"
    sede_id: str
    medicamento_id: str
    stock: int = Field(ge=0)
    minimo: int = Field(ge=0)


class EstadoSugerencia(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class SugerenciaTraslado(BaseModel):
    id: str
    medicamento_id: str
    sede_destino_id: str
    sede_origen_id: Optional[str]  # None => reabastecer desde la central de farmacia
    cantidad: int
    motivo: str
    estado: EstadoSugerencia = EstadoSugerencia.PENDIENTE


class EntradaBitacora(BaseModel):
    id: str
    momento: datetime
    tipo: str
    detalle: str
    motor: Optional[str] = None
