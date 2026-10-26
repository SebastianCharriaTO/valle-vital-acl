"""ADAPTADOR de persistencia en memoria. Reemplazable por SQL sin tocar los servicios.
Nota: en Render (plan gratuito) el disco es efimero, por eso no se usa archivo como BD."""
from typing import Callable, Optional

from app.ports.repositorio import RepositorioPort, T


class RepositorioMemoria(RepositorioPort[T]):
    def __init__(self) -> None:
        self._datos: dict[str, T] = {}

    def agregar(self, entidad: T) -> T:
        self._datos[entidad.id] = entidad  # type: ignore[attr-defined]
        return entidad

    def obtener(self, id: str) -> Optional[T]:
        return self._datos.get(id)

    def listar(self, filtro: Optional[Callable[[T], bool]] = None) -> list[T]:
        items = list(self._datos.values())
        return [i for i in items if filtro(i)] if filtro else items

    def actualizar(self, entidad: T) -> T:
        if entidad.id not in self._datos:  # type: ignore[attr-defined]
            raise KeyError(entidad.id)  # type: ignore[attr-defined]
        self._datos[entidad.id] = entidad  # type: ignore[attr-defined]
        return entidad
