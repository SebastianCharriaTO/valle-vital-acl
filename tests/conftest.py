from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.container import construir
from app.main import crear_app

AHORA = datetime(2026, 10, 26, 9, 30)  # reloj fijo => pruebas deterministas


@pytest.fixture
def container():
    return construir(Settings(motor_ia="llm_simulado", umbral_fallos=3, segundos_recuperacion=30), lambda: AHORA)


@pytest.fixture
def client(container):
    return TestClient(crear_app(container))
