from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .promocion import Promocion


class MetodoPago:
    def __init__(
        self,
        id_metodo_pago: int,
        nombre: str,
        tipo: str,
        disponible: bool = True,
    ) -> None:
        self.id_metodo_pago = id_metodo_pago
        self.nombre = nombre
        self.tipo = tipo
        self.disponible = disponible
        self.promociones: list["Promocion"] = []

    def verificarDisponibilidad(self) -> bool:
        return self.disponible

    def agregarPromocion(self, promocion: "Promocion") -> None:
        self.promociones.append(promocion)

    def __repr__(self) -> str:
        return f"MetodoPago({self.nombre} - {self.tipo})"
