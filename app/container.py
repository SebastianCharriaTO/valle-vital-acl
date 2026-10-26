"""Raiz de composicion: aqui (y solo aqui) se eligen los adaptadores concretos."""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from app.adapters.asistente_llm import AsistenteLLMSimuladoAdapter
from app.adapters.asistente_reglas import AsistenteReglasAdapter
from app.adapters.repo_memoria import RepositorioMemoria
from app.config import Settings
from app.domain.models import (Cita, EntradaBitacora, Franja, InventarioSede, Medicamento, Paciente,
                               Profesional, RegistroTriage, Sede, SugerenciaTraslado)
from app.resilience.circuit_breaker import CircuitBreaker
from app.services.bitacora import Bitacora
from app.services.cita_service import CitaService
from app.services.farmacia_service import FarmaciaService
from app.services.triage_service import TriageService

SEED = Path(__file__).parent / "data" / "seed.json"
HORAS = (8, 9, 10, 11, 14, 15, 16)


@dataclass
class Container:
    settings: Settings
    triage: TriageService
    citas: CitaService
    farmacia: FarmaciaService
    bitacora: Bitacora
    proveedor_ia: AsistenteLLMSimuladoAdapter
    sedes: RepositorioMemoria
    profesionales: RepositorioMemoria
    pacientes: RepositorioMemoria
    medicamentos: RepositorioMemoria


def construir(settings: Settings | None = None,
              reloj: Callable[[], datetime] = datetime.now) -> Container:
    settings = settings or Settings.desde_entorno()
    datos = json.loads(SEED.read_text(encoding="utf-8"))

    def repo(modelo, filas, clave=None):
        r = RepositorioMemoria()
        for f in filas:
            if clave:
                f = {**f, "id": clave(f)}
            r.agregar(modelo(**f))
        return r

    sedes = repo(Sede, datos["sedes"])
    profs = repo(Profesional, datos["profesionales"])
    pacs = repo(Paciente, datos["pacientes"])
    meds = repo(Medicamento, datos["medicamentos"])
    inv = repo(InventarioSede, datos["inventario"], lambda f: f"{f['sede_id']}:{f['medicamento_id']}")

    franjas = RepositorioMemoria()
    base = reloj().replace(minute=0, second=0, microsecond=0)
    for p in datos["profesionales"]:
        for d in range(0, 7):
            for h in HORAS:
                ini = (base + timedelta(days=d)).replace(hour=h)
                franjas.agregar(Franja(id=f"{p['id']}@{ini:%Y%m%d%H}", profesional_id=p["id"], inicio=ini))

    bitacora = Bitacora(RepositorioMemoria(), reloj)
    reglas = AsistenteReglasAdapter()
    llm = AsistenteLLMSimuladoAdapter()
    primario = reglas if settings.motor_ia == "reglas" else llm
    breaker = CircuitBreaker(settings.umbral_fallos, settings.segundos_recuperacion)
    triage = TriageService(primario, reglas, breaker, RepositorioMemoria(), bitacora, reloj)
    citas = CitaService(RepositorioMemoria(), franjas, profs, bitacora, reloj)
    farmacia = FarmaciaService(inv, RepositorioMemoria(), bitacora)
    return Container(settings, triage, citas, farmacia, bitacora, llm, sedes, profs, pacs, meds)
