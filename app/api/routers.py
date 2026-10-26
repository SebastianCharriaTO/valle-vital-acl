"""Capa de presentacion (API REST). Solo traduce HTTP <-> servicios; no contiene reglas de negocio."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.container import Container
from app.domain.models import (Cita, EntradaBitacora, InventarioSede, Prioridad, RegistroTriage,
                               ResultadoTriage, SolicitudTriage, SugerenciaTraslado)
from app.services.cita_service import SinDisponibilidad

triage = APIRouter(prefix="/api/triage", tags=["Triage orientativo"])
citas = APIRouter(prefix="/api/citas", tags=["Citas"])
farmacia = APIRouter(prefix="/api", tags=["Farmacia y distribucion"])
admin = APIRouter(prefix="/api/admin", tags=["Administracion"])
salud = APIRouter(tags=["Operacion"])


class TriageEntrada(BaseModel):
    paciente_id: str = Field(examples=["PAC-001"])
    solicitud: SolicitudTriage


class ConfirmacionEntrada(BaseModel):
    profesional_id: str = Field(examples=["P1"])
    prioridad: Prioridad


class CitaEntrada(BaseModel):
    paciente_id: str = Field(examples=["PAC-001"])
    sede_id: str = Field(examples=["S1"])
    especialidad: str = Field(examples=["Medicina general"])
    solicitud: SolicitudTriage


class CitaSalida(BaseModel):
    cita: Cita
    triage: RegistroTriage


@triage.post("", response_model=RegistroTriage, summary="Prioridad sugerida (no es un diagnostico)")
def evaluar(e: TriageEntrada, c: Container = Depends(get_container)):
    if c.pacientes.obtener(e.paciente_id) is None:
        raise HTTPException(404, "Paciente no encontrado (solo existen pacientes sinteticos)")
    return c.triage.registrar(e.paciente_id, e.solicitud)


@triage.get("", response_model=list[RegistroTriage])
def listar_triage(c: Container = Depends(get_container)):
    return c.triage.listar()


@triage.post("/{triage_id}/confirmar", response_model=RegistroTriage,
             summary="El profesional confirma o corrige la prioridad (human-in-the-loop)")
def confirmar_triage(triage_id: str, e: ConfirmacionEntrada, c: Container = Depends(get_container)):
    if c.profesionales.obtener(e.profesional_id) is None:
        raise HTTPException(404, "Profesional no encontrado")
    try:
        reg = c.triage.confirmar(triage_id, e.profesional_id, e.prioridad)
    except KeyError:
        raise HTTPException(404, "Triage no encontrado")
    for cita in c.citas.listar():
        if cita.triage_id == triage_id:
            c.citas.ajustar_prioridad(cita.id, e.prioridad)
            c.citas.confirmar(cita.id)
    return reg


@citas.post("", response_model=CitaSalida, status_code=201,
            summary="Solicita cita: calcula prioridad sugerida y asigna franja")
def solicitar_cita(e: CitaEntrada, c: Container = Depends(get_container)):
    if c.pacientes.obtener(e.paciente_id) is None:
        raise HTTPException(404, "Paciente no encontrado (solo existen pacientes sinteticos)")
    if c.sedes.obtener(e.sede_id) is None:
        raise HTTPException(404, "Sede no encontrada")
    reg = c.triage.registrar(e.paciente_id, e.solicitud)
    try:
        cita = c.citas.asignar(e.paciente_id, e.sede_id, e.especialidad, reg.resultado.prioridad, reg.id)
    except SinDisponibilidad as exc:
        raise HTTPException(409, str(exc))
    return CitaSalida(cita=cita, triage=reg)


@citas.get("", response_model=list[Cita])
def listar_citas(c: Container = Depends(get_container)):
    return c.citas.listar()


@citas.post("/{cita_id}/cancelar", response_model=Cita)
def cancelar(cita_id: str, c: Container = Depends(get_container)):
    try:
        return c.citas.cancelar(cita_id)
    except KeyError:
        raise HTTPException(404, "Cita no encontrada")


@citas.post("/{cita_id}/reprogramar", response_model=Cita)
def reprogramar(cita_id: str, c: Container = Depends(get_container)):
    try:
        return c.citas.reprogramar(cita_id)
    except KeyError:
        raise HTTPException(404, "Cita no encontrada")
    except SinDisponibilidad as exc:
        raise HTTPException(409, str(exc))


@farmacia.get("/inventario", response_model=list[InventarioSede])
def inventario(sede_id: str | None = None, c: Container = Depends(get_container)):
    return c.farmacia.inventario(sede_id)


@farmacia.post("/farmacia/sugerencias", response_model=list[SugerenciaTraslado],
               summary="Genera sugerencias de traslado cuando el stock cae bajo el minimo")
def generar_sugerencias(c: Container = Depends(get_container)):
    return c.farmacia.generar_sugerencias()


@farmacia.get("/farmacia/sugerencias", response_model=list[SugerenciaTraslado])
def listar_sugerencias(c: Container = Depends(get_container)):
    return c.farmacia.listar_sugerencias()


@farmacia.post("/farmacia/sugerencias/{sid}/{accion}", response_model=SugerenciaTraslado,
               summary="Aprobar o rechazar (accion = aprobar | rechazar)")
def resolver(sid: str, accion: str, c: Container = Depends(get_container)):
    if accion not in ("aprobar", "rechazar"):
        raise HTTPException(422, "accion debe ser 'aprobar' o 'rechazar'")
    try:
        return c.farmacia.resolver(sid, accion == "aprobar")
    except KeyError:
        raise HTTPException(404, "Sugerencia no encontrada")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


class FallaEntrada(BaseModel):
    falla: bool


@admin.get("/estado")
def estado_admin(c: Container = Depends(get_container)):
    return {"motor_configurado": c.settings.motor_ia, "circuito": c.triage.breaker.estado.value,
            "fallos_consecutivos": c.triage.breaker.fallos, "proveedor_ia_con_falla": c.proveedor_ia.falla}


@admin.post("/proveedor-ia/falla", summary="Simula la caida del proveedor de IA (demostracion)")
def simular_falla(e: FallaEntrada, c: Container = Depends(get_container)):
    c.proveedor_ia.falla = e.falla
    c.bitacora.registrar("admin", f"proveedor_ia.falla={e.falla}")
    return estado_admin(c)


@admin.get("/bitacora", response_model=list[EntradaBitacora])
def bitacora(n: int = 50, c: Container = Depends(get_container)):
    return c.bitacora.listar(n)


@salud.get("/health", summary="Liveness (superficial)")
def health():
    return {"estado": "ok"}


@salud.get("/health/ready", summary="Readiness (profunda): dependencias y circuito")
def ready(c: Container = Depends(get_container)):
    circ = c.triage.breaker.estado.value
    ok_datos = len(c.sedes.listar()) > 0
    estado = "ok" if (circ == "cerrado" and ok_datos) else "degradado"
    return {"estado": estado, "circuito_ia": circ, "repositorio": "ok" if ok_datos else "vacio",
            "motor_configurado": c.settings.motor_ia}
