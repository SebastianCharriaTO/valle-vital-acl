from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app.api import routers
from app.container import Container, construir
from app.web.views import router as web_router

DESCRIPCION = (
    "Prototipo academico del **Asistente Clinico-Logistico Valle Vital (ACL)**. Entidad y datos FICTICIOS. "
    "El asistente **no diagnostica**: sugiere una prioridad y el profesional decide."
)


def crear_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title="ACL Valle Vital (prototipo academico)", version="1.0.0", description=DESCRIPCION,
                  docs_url=None)  # /docs se sirve abajo con Swagger UI local (sin depender de un CDN)
    app.state.container = container or construir()
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")

    @app.get("/docs", include_in_schema=False)
    def swagger():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title + " - Swagger UI",
                                   swagger_js_url="/static/swagger/swagger-ui-bundle.js",
                                   swagger_css_url="/static/swagger/swagger-ui.css")

    for r in (routers.triage, routers.citas, routers.farmacia, routers.admin, routers.salud):
        app.include_router(r)
    app.include_router(web_router)
    return app


app = crear_app()
