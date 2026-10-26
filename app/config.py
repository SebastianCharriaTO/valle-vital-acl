"""Configuracion central. Todo se controla por variables de entorno (patron de nube: config fuera del codigo)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    motor_ia: str = "llm_simulado"      # "reglas" | "llm_simulado"
    umbral_fallos: int = 3              # fallos consecutivos para abrir el circuito
    segundos_recuperacion: float = 30.0  # tiempo en estado abierto antes de probar (semiabierto)

    @staticmethod
    def desde_entorno() -> "Settings":
        return Settings(
            motor_ia=os.getenv("MOTOR_IA", "llm_simulado"),
            umbral_fallos=int(os.getenv("CB_UMBRAL_FALLOS", "3")),
            segundos_recuperacion=float(os.getenv("CB_SEGUNDOS_RECUPERACION", "30")),
        )
