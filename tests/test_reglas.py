import pytest

from app.adapters.asistente_reglas import AsistenteReglasAdapter
from app.domain.models import Prioridad, SolicitudTriage

A = AsistenteReglasAdapter()


def sol(sint, edad=30, dias=1, temp=None):
    return SolicitudTriage(sintomas=sint, edad=edad, dias_evolucion=dias, temperatura_c=temp)


@pytest.mark.parametrize("sintoma", ["dolor de pecho", "Dificultad para respirar", "convulsión", "perdida de conciencia"])
def test_bandera_roja_es_urgente(sintoma):
    r = A.evaluar(sol([sintoma]))
    assert r.prioridad is Prioridad.URGENTE and r.requiere_confirmacion


def test_sintoma_leve_es_baja():
    assert A.evaluar(sol(["congestion nasal"])).prioridad is Prioridad.BAJA


def test_fiebre_alta_en_adulto_mayor_sube_prioridad():
    r = A.evaluar(sol(["fiebre", "tos", "fatiga"], edad=72, dias=8, temp=39.4))
    assert r.prioridad is Prioridad.ALTA and "temperatura" in r.explicacion


def test_prioridad_media():
    assert A.evaluar(sol(["fiebre", "vomito"], temp=38.2)).prioridad is Prioridad.MEDIA


def test_media_y_baja_no_requieren_confirmacion():
    assert not A.evaluar(sol(["tos"])).requiere_confirmacion


def test_resultado_incluye_advertencia_no_diagnostico():
    assert "no es un diagnostico" in A.evaluar(sol(["tos"])).advertencia
