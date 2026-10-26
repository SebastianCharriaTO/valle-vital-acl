"""ADAPTADOR/ESTRATEGIA 2: proveedor de IA externo SIMULADO.
No llama a ningun servicio real ni usa claves. Imita un LLM remoto: reutiliza el criterio de
reglas y agrega una explicacion en lenguaje natural; puede 'caerse' para demostrar el Circuit Breaker.
Para integrar un LLM real bastaria otra clase que implemente AsistenteIAPort."""
from app.adapters.asistente_reglas import AsistenteReglasAdapter
from app.domain.models import ResultadoTriage, SolicitudTriage
from app.ports.asistente_ia import AsistenteIAPort, ProveedorIAError


class AsistenteLLMSimuladoAdapter(AsistenteIAPort):
    nombre = "llm_simulado"

    def __init__(self) -> None:
        self.falla = False  # interruptor de demostracion (simula caida del proveedor)
        self._base = AsistenteReglasAdapter()

    def evaluar(self, solicitud: SolicitudTriage) -> ResultadoTriage:
        if self.falla:
            raise ProveedorIAError("Proveedor de IA no disponible (simulado): tiempo de espera agotado")
        r = self._base.evaluar(solicitud)
        return r.model_copy(update={
            "motor": self.nombre,
            "explicacion": "Analisis del asistente: " + r.explicacion
                           + " Se recomienda valoracion presencial segun la prioridad sugerida.",
        })
