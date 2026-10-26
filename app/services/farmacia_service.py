"""Inventario por sede y sugerencias de traslado/reabastecimiento (RF-05, RF-06, RF-07)."""
import itertools

from app.domain.models import EstadoSugerencia, InventarioSede, SugerenciaTraslado
from app.ports.repositorio import RepositorioPort
from app.services.bitacora import Bitacora

FACTOR_EXCEDENTE = 1.5  # una sede cede solo lo que supera 1.5 x su minimo


class FarmaciaService:
    def __init__(self, inventario: RepositorioPort[InventarioSede],
                 sugerencias: RepositorioPort[SugerenciaTraslado], bitacora: Bitacora) -> None:
        self._inv, self._sug, self._bitacora = inventario, sugerencias, bitacora
        self._seq = itertools.count(1)

    def inventario(self, sede_id: str | None = None) -> list[InventarioSede]:
        return self._inv.listar((lambda i: i.sede_id == sede_id) if sede_id else None)

    def bajo_minimo(self) -> list[InventarioSede]:
        return self._inv.listar(lambda i: i.stock < i.minimo)

    def generar_sugerencias(self) -> list[SugerenciaTraslado]:
        # Evita duplicar sugerencias pendientes para el mismo faltante.
        pendientes = {(s.medicamento_id, s.sede_destino_id)
                      for s in self._sug.listar(lambda s: s.estado is EstadoSugerencia.PENDIENTE)}
        nuevas: list[SugerenciaTraslado] = []
        for falta in self.bajo_minimo():
            if (falta.medicamento_id, falta.sede_id) in pendientes:
                continue
            necesario = falta.minimo * 2 - falta.stock  # objetivo: 2 x minimo
            donantes = sorted(
                (i for i in self._inv.listar(lambda i: i.medicamento_id == falta.medicamento_id
                                             and i.sede_id != falta.sede_id)
                 if i.stock - int(i.minimo * FACTOR_EXCEDENTE) > 0),
                key=lambda i: i.stock - i.minimo, reverse=True)
            if donantes:
                d = donantes[0]
                cant = min(necesario, d.stock - int(d.minimo * FACTOR_EXCEDENTE))
                origen, motivo = d.sede_id, (f"Stock {falta.stock} < minimo {falta.minimo}; "
                                             f"{d.sede_id} tiene excedente ({d.stock}, minimo {d.minimo}).")
            else:
                cant, origen, motivo = necesario, None, (
                    f"Stock {falta.stock} < minimo {falta.minimo}; ninguna sede tiene excedente: pedir a la central.")
            s = SugerenciaTraslado(id=f"S{next(self._seq):04d}", medicamento_id=falta.medicamento_id,
                                   sede_destino_id=falta.sede_id, sede_origen_id=origen,
                                   cantidad=cant, motivo=motivo)
            self._sug.agregar(s)
            self._bitacora.registrar("sugerencia", f"{s.id} {s.medicamento_id} {origen or 'central'}->{falta.sede_id} x{cant}")
            nuevas.append(s)
        return nuevas

    def listar_sugerencias(self) -> list[SugerenciaTraslado]:
        return self._sug.listar()

    def resolver(self, sugerencia_id: str, aprobar: bool) -> SugerenciaTraslado:
        s = self._sug.obtener(sugerencia_id)
        if s is None:
            raise KeyError(sugerencia_id)
        if s.estado is not EstadoSugerencia.PENDIENTE:
            raise ValueError("La sugerencia ya fue resuelta")
        if aprobar:
            destino = self._inv.obtener(f"{s.sede_destino_id}:{s.medicamento_id}")
            self._inv.actualizar(destino.model_copy(update={"stock": destino.stock + s.cantidad}))
            if s.sede_origen_id:
                o = self._inv.obtener(f"{s.sede_origen_id}:{s.medicamento_id}")
                self._inv.actualizar(o.model_copy(update={"stock": o.stock - s.cantidad}))
        s = s.model_copy(update={"estado": EstadoSugerencia.APROBADA if aprobar else EstadoSugerencia.RECHAZADA})
        self._sug.actualizar(s)
        self._bitacora.registrar("traslado", f"{s.id} {s.estado.value}")
        return s
