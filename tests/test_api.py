def cuerpo(sint, edad=40, **kw):
    return {"paciente_id": "PAC-001", "sede_id": "S1", "especialidad": "Medicina general",
            "solicitud": {"sintomas": sint, "edad": edad, **kw}}


def test_health(client):
    assert client.get("/health").json() == {"estado": "ok"}


def test_ready_cambia_a_degradado_con_circuito_abierto(client):
    assert client.get("/health/ready").json()["estado"] == "ok"
    client.post("/api/admin/proveedor-ia/falla", json={"falla": True})
    for _ in range(3):
        client.post("/api/triage", json={"paciente_id": "PAC-001", "solicitud": {"sintomas": ["tos"], "edad": 30}})
    r = client.get("/health/ready").json()
    assert r["estado"] == "degradado" and r["circuito_ia"] == "abierto"


def test_solicitar_cita_201_y_estructura(client):
    r = client.post("/api/citas", json=cuerpo(["fiebre", "tos"], temperatura_c=38.5))
    assert r.status_code == 201
    j = r.json()
    assert j["cita"]["estado"] == "confirmada" and j["triage"]["resultado"]["motor"] == "llm_simulado"


def test_urgente_pendiente_y_confirmacion_humana(client):
    j = client.post("/api/citas", json=cuerpo(["dolor de pecho"])).json()
    assert j["cita"]["estado"] == "pendiente_confirmacion"
    tid = j["triage"]["id"]
    r = client.post(f"/api/triage/{tid}/confirmar", json={"profesional_id": "P1", "prioridad": "urgente"})
    assert r.status_code == 200 and r.json()["confirmado_por"] == "P1"
    assert client.get("/api/citas").json()[0]["estado"] == "confirmada"


def test_paciente_inexistente_404(client):
    b = cuerpo(["tos"]); b["paciente_id"] = "NOEXISTE"
    assert client.post("/api/citas", json=b).status_code == 404


def test_validacion_422_sin_sintomas(client):
    assert client.post("/api/citas", json=cuerpo([])).status_code == 422


def test_inventario_y_sugerencias(client):
    assert len(client.get("/api/inventario").json()) == 12
    s = client.post("/api/farmacia/sugerencias").json()
    assert len(s) >= 3
    r = client.post(f"/api/farmacia/sugerencias/{s[0]['id']}/aprobar")
    assert r.status_code == 200 and r.json()["estado"] == "aprobada"


def test_vistas_html(client):
    for u in ["/", "/solicitar-cita", "/profesional", "/farmacia", "/admin"]:
        assert client.get(u).status_code == 200


def test_formulario_web_end_to_end(client):
    r = client.post("/solicitar-cita", data={"paciente_id": "PAC-002", "sede_id": "S1", "especialidad": "Medicina general",
                                             "edad": 71, "dias_evolucion": 8, "temperatura_c": "39.4",
                                             "sintomas": ["fiebre", "tos", "fatiga"]})
    assert r.status_code == 200 and "Prioridad sugerida" in r.text and "ALTA" in r.text


def test_openapi_documenta_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/triage" in paths and "/api/citas" in paths and "/health" in paths
