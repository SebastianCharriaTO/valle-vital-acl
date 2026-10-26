"""PUERTO de persistencia: interfaz tipo coleccion (patron Repository, Fowler)."""
from abc import ABC, abstractmethod
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class RepositorioPort(ABC, Generic[T]):
    @abstractmethod
    def agregar(self, entidad: T) -> T: ...

    @abstractmethod
    def obtener(self, id: str) -> Optional[T]: ...

    @abstractmethod
    def listar(self, filtro: Optional[Callable[[T], bool]] = None) -> list[T]: ...

    @abstractmethod
    def actualizar(self, entidad: T) -> T: ...
