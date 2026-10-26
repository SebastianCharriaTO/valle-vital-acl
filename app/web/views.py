"""Vistas HTML (Jinja2). Consumen los mismos servicios que la API REST."""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.adapters.asistente_reglas import BANDERAS_ROJAS, PESOS
from app.api.deps import get_container
from app.container import Container
from app.domain.models import EstadoCita, EstadoSugerencia, Prioridad, SolicitudTriage
from app.services.cita_service import SinDisponibilidad

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
SINTOMAS = sorted(PESOS) + sorted(BANDERAS_ROJAS)


def _ctx(c: Container, **extra):
    return {"circuito": c.triage.breaker.estado.value, "motor": c.settings.motor_ia, **extra}


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, c: Container = Depends(get_container)):
    citas = c.citas.listar()
    return templates.TemplateResponse(request, "inicio.html", _ctx(
        c, citas=citas[:8], total_citas=len(citas),
        pendientes=[t for t in c.triage.listar() if t.resultado.requiere_confirmacion and not t.prioridad_final],
        bajo_minimo=c.farmacia.bajo_minimo(), meds={m.id: m.nombre for m in c.medicamentos.listar()},
        pacientes={p.id: p.nombre for p in c.pacientes.listar()},
        sedes={s.id: s.nombre for s in c.sedes.listar()}))


@router.get("/solicitar-cita", response_class=HTMLResponse)
def form_cita(request: Request, c: Container = Depends(get_container)):
    return templates.TemplateResponse(request, "solicitar_cita.html", _ctx(
        c, sintomas=SINTOMAS, pacientes=c.pacientes.listar(), sedes=c.sedes.listar(),
        especialidades=sorted({p.especialidad for p in c.profesionales.listar()}), resultado=None))


@router.post("/solicitar-cita", response_class=HTMLResponse)
def enviar_cita(request: Request, paciente_id: str = Form(...), sede_id: str = Form(...),
                especialidad: str = Form(...), edad: int = Form(...), dias_evolucion: int = Form(1),
                temperatura_c: str = Form(""), sintomas: list[str] = Form(default=[]),
                otros: str = Form(""), c: Container = Depends(get_container)):
    lista = list(sintomas) + [s.strip() for s in otros.split(",") if s.strip()]
    error = None
    reg = cita = None
    if not lista:
        error = "Seleccione o escriba al menos un sintoma."
    else:
        sol = SolicitudTriage(sintomas=lista, edad=edad, dias_evolucion=dias_evolucion,
                              temperatura_c=float(temperatura_c) if temperatura_c else None)
        reg = c.triage.registrar(paciente_id, sol)
        try:
            cita = c.citas.asignar(paciente_id, sede_id, especialidad, reg.resultado.prioridad, reg.id)
        except SinDisponibilidad as exc:
            error = str(exc)
    return templates.TemplateResponse(request, "solicitar_cita.html", _ctx(
        c, sintomas=SINTOMAS, pacientes=c.pacientes.listar(), sedes=c.sedes.listar(),
        especialidades=sorted({p.especialidad for p in c.profesionales.listar()}),
        resultado={"triage": reg, "cita": cita, "error": error}))


@router.get("/profesional", response_class=HTMLResponse)
def profesional(request: Request, c: Container = Depends(get_container)):
    return templates.TemplateResponse(request, "profesional.html", _ctx(
        c, registros=c.triage.listar(), profesionales=c.profesionales.listar(),
        prioridades=[p.value for p in Prioridad],
        pacientes={p.id: p.nombre for p in c.pacientes.listar()}))


@router.post("/profesional/confirmar")
def confirmar(triage_id: str = Form(...), profesional_id: str = Form(...), prioridad: str = Form(...),
              c: Container = Depends(get_container)):
    c.triage.confirmar(triage_id, profesional_id, Prioridad(prioridad))
    for cita in c.citas.listar():
        if cita.triage_id == triage_id and cita.estado is not EstadoCita.CANCELADA:
            c.citas.ajustar_prioridad(cita.id, Prioridad(prioridad))
            c.citas.confirmar(cita.id)
    return RedirectResponse("/profesional", status_code=303)


@router.get("/farmacia", response_class=HTMLResponse)
def vista_farmacia(request: Request, c: Container = Depends(get_container)):
    return templates.TemplateResponse(request, "farmacia.html", _ctx(
        c, inventario=c.farmacia.inventario(), sugerencias=c.farmacia.listar_sugerencias(),
        meds={m.id: m.nombre for m in c.medicamentos.listar()},
        sedes={s.id: s.nombre for s in c.sedes.listar()}, PEND=EstadoSugerencia.PENDIENTE))


@router.post("/farmacia/generar")
def generar(c: Container = Depends(get_container)):
    c.farmacia.generar_sugerencias()
    return RedirectResponse("/farmacia", status_code=303)


@router.post("/farmacia/resolver")
def resolver(sugerencia_id: str = Form(...), accion: str = Form(...), c: Container = Depends(get_container)):
    c.farmacia.resolver(sugerencia_id, accion == "aprobar")
    return RedirectResponse("/farmacia", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
def vista_admin(request: Request, c: Container = Depends(get_container)):
    return templates.TemplateResponse(request, "admin.html", _ctx(
        c, falla=c.proveedor_ia.falla, fallos=c.triage.breaker.fallos, bitacora=c.bitacora.listar(15)))


@router.post("/admin/falla")
def alternar_falla(falla: str = Form(...), c: Container = Depends(get_container)):
    c.proveedor_ia.falla = falla == "1"
    c.bitacora.registrar("admin", f"proveedor_ia.falla={c.proveedor_ia.falla}")
    return RedirectResponse("/admin", status_code=303)
