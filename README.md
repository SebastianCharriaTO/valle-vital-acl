# ACL Valle Vital (prototipo académico)

Prototipo del **Asistente Clínico-Logístico Valle Vital (ACL)**, entregable de la actividad
*AA2 U1 · Orquestando Códigos: La Sinfonía de los Sistemas* (Arquitectura de software 20262 - N6 Gr A,
Tecnológica del Oriente).

> **Aviso.** La entidad "Red Integrada de Salud Valle Vital S.A.S." y todos los datos (pacientes, médicos,
> inventarios) son **ficticios**. El asistente **no diagnostica ni es dispositivo médico**: sugiere una
> prioridad orientativa y el profesional de la salud decide.

- Repositorio: https://github.com/SebastianCharriaTO/valle-vital-acl
- Despliegue en Render: `[COMPLETAR: URL del despliegue en Render]` (plan gratuito: tarda ≈1 min en despertar)
- Video: `[COMPLETAR: enlace del video]`
- Integrantes: Sebastián Charria Muñoz (líder, desarrollador) y Esteban Charria Muñoz (analista, desarrollador)

## Qué hace

1. **Orientación de prioridad** (baja / media / alta / urgente) a partir de síntomas, edad y temperatura.
2. **Asignación de citas** por sede, especialidad y prioridad; las prioridades alta/urgente quedan
   `pendiente_confirmacion` hasta que un profesional las confirma (human-in-the-loop).
3. **Sugerencias de traslado de medicamentos** entre sedes cuando el stock cae bajo el mínimo.
4. **Operación en la nube**: `/health`, `/health/ready`, bitácora de recomendaciones y simulación de la caída del proveedor de IA.

## Arquitectura y patrones

Estilo en capas con **puertos y adaptadores (hexagonal)** como patrón principal:

| Patrón | Dónde está |
|---|---|
| Puertos y adaptadores | `app/ports/` (contratos) y `app/adapters/` (implementaciones) |
| Strategy | `AsistenteIAPort` con `AsistenteReglasAdapter` y `AsistenteLLMSimuladoAdapter`; se elige con `MOTOR_IA` |
| Circuit Breaker + fallback | `app/resilience/circuit_breaker.py` usado en `app/services/triage_service.py` |
| Repository | `app/ports/repositorio.py` + `app/adapters/repo_memoria.py` |
| Capas | `api` / `web` → `services` → `domain` + `ports` ← `adapters` |
| Health Endpoint Monitoring | `GET /health` y `GET /health/ready` |

La raíz de composición es `app/container.py` (único lugar que conoce los adaptadores concretos).
Diagramas UML (PlantUML) en `docs/uml/`; capturas reales de la ejecución local en `docs/capturas/`.

## Ejecutar localmente

Requiere Python 3.12 o 3.13.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --port 8000
```

- Vistas: http://127.0.0.1:8000/ · Swagger UI: http://127.0.0.1:8000/docs · OpenAPI: `/openapi.json`
- Pruebas: `python -m pytest -v` (35 pruebas).

Variables de entorno (opcionales): `MOTOR_IA` (`llm_simulado` por defecto | `reglas`), `CB_UMBRAL_FALLOS` (3),
`CB_SEGUNDOS_RECUPERACION` (30).

## Demostración de resiliencia

1. En `/admin` pulse **Simular caída del proveedor**.
2. Solicite 3 citas en `/solicitar-cita`: el sistema responde con reglas locales ("modo degradado").
3. El circuito pasa a **abierto** y `/health/ready` devuelve `degradado`. Tras 30 s pasa a *semiabierto* y, si el proveedor se restablece, vuelve a *cerrado*.

## Despliegue en Render

1. Suba el repositorio a GitHub.
2. En Render: *New → Web Service* (o *Blueprint* con `render.yaml`) y conecte el repositorio.
3. Build: `pip install -r requirements.txt` · Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Variable `PYTHON_VERSION=3.13.5` (o use `.python-version`). Health check path: `/health`.

Limitaciones del plan gratuito: el servicio se duerme tras 15 min sin tráfico y el disco es efímero; por eso el
prototipo guarda los datos en memoria (se reinician con cada arranque).

## Estructura

```
app/        main.py · container.py · config.py
  api/      routers REST        web/   vistas Jinja2 + estáticos (Swagger UI local)
  services/ lógica de aplicación  domain/ modelos   ports/ interfaces   adapters/ implementaciones   resilience/
tests/      pytest (reglas, circuit breaker, servicios, API y vistas)
docs/       uml/ (.puml y .png) · capturas/
```

## Limitaciones

Sin base de datos (datos sintéticos en memoria); IA simulada por reglas (no usa un LLM real); sin autenticación;
no integra historia clínica electrónica (Ley 2015 de 2020) — solo como trabajo futuro mediante un adaptador/ACL.
