from app.domain.models import EstadoCita, EstadoSugerencia, Prioridad, SolicitudTriage
from app.services.cita_service import SinDisponibilidad
import pytest

LEVE = SolicitudTriage(sintomas=["tos"], edad=30)
ROJA = SolicitudTriage(sintomas=["dolor de pecho"], edad=60)


def test_fallback_a_reglas_cuando_proveedor_cae(container):
    container.proveedor_ia.falla = True
    r = container.triage.evaluar(LEVE)
    assert r.motor == "reglas" and "Modo degradado" in r.explicacion


def test_circuito_se_abre_y_no_vuelve_a_llamar_al_proveedor(container):
    container.proveedor_ia.falla = True
    for _ in range(3):
        container.triage.evaluar(LEVE)
    assert container.triage.breaker.estado.value == "abierto"
    container.proveedor_ia.falla = False  # aunque se recupere, el circuito sigue abierto hasta el timeout
    assert container.triage.evaluar(LEVE).motor == "reglas"


def test_proveedor_sano_usa_motor_llm(container):
    assert container.triage.evaluar(LEVE).motor == "llm_simulado"


def test_urgente_queda_pendiente_de_confirmacion_y_confirmar_la_libera(container):
    reg = container.triage.registrar("PAC-001", ROJA)
    cita = container.citas.asignar("PAC-001", "S1", "Medicina general", reg.resultado.prioridad, reg.id)
    assert cita.estado is EstadoCita.PENDIENTE_CONFIRMACION
    r2 = container.triage.confirmar(reg.id, "P1", Prioridad.URGENTE)
    assert r2.confirmado_por == "P1"


def test_urgente_obtiene_franja_mas_temprana_que_baja(container):
    u = container.citas.asignar("PAC-001", "S1", "Medicina general", Prioridad.URGENTE)
    b = container.citas.asignar("PAC-002", "S1", "Medicina general", Prioridad.BAJA)
    assert u.inicio < b.inicio


def test_no_hay_doble_reserva(container):
    a = container.citas.asignar("PAC-001", "S1", "Medicina general", Prioridad.MEDIA)
    b = container.citas.asignar("PAC-002", "S1", "Medicina general", Prioridad.MEDIA)
    assert a.inicio != b.inicio


def test_cancelar_libera_la_franja(container):
    a = container.citas.asignar("PAC-001", "S1", "Medicina general", Prioridad.MEDIA)
    container.citas.cancelar(a.id)
    b = container.citas.asignar("PAC-002", "S1", "Medicina general", Prioridad.MEDIA)
    assert b.inicio == a.inicio


def test_sin_disponibilidad_para_especialidad_inexistente(container):
    with pytest.raises(SinDisponibilidad):
        container.citas.asignar("PAC-001", "S3", "Pediatria", Prioridad.BAJA)


def test_sugerencias_traslado_desde_sede_con_excedente(container):
    sug = container.farmacia.generar_sugerencias()
    s = next(x for x in sug if x.medicamento_id == "M1" and x.sede_destino_id == "S2")
    assert s.sede_origen_id == "S1" and s.cantidad > 0


def test_sugerencia_sin_excedente_pide_a_central(container):
    sug = container.farmacia.generar_sugerencias()
    s = next(x for x in sug if x.medicamento_id == "M4" and x.sede_destino_id == "S1")
    assert s.sede_origen_id is None


def test_aprobar_mueve_stock_y_no_duplica(container):
    s = next(x for x in container.farmacia.generar_sugerencias() if x.medicamento_id == "M1")
    antes_d = container.farmacia._inv.obtener(f"{s.sede_destino_id}:M1").stock
    container.farmacia.resolver(s.id, True)
    assert container.farmacia._inv.obtener(f"{s.sede_destino_id}:M1").stock == antes_d + s.cantidad
    assert container.farmacia.listar_sugerencias()[0].estado is EstadoSugerencia.APROBADA
    with pytest.raises(ValueError):
        container.farmacia.resolver(s.id, True)


def test_bitacora_registra_triage(container):
    container.triage.registrar("PAC-001", LEVE)
    assert any(b.tipo == "triage" for b in container.bitacora.listar())
