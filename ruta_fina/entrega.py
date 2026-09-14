from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .pedido import Pedido
    from .usuario import Repartidor


class Entrega:
    def __init__(self, id_entrega: int, pedido: "Pedido") -> None:
        self.id_entrega = id_entrega
        self.fecha_asignacion: Optional[datetime] = None
        self.fecha_entrega: Optional[datetime] = None
        self.estado_entrega = "sin asignar"
        self.pedido = pedido
        self.repartidor: Optional["Repartidor"] = None

    def asignarRepartidor(self, repartidor: "Repartidor") -> None:
        self.repartidor = repartidor
        self.fecha_asignacion = datetime.now()
        self.estado_entrega = "asignada"

    def actualizarEstado(self, nuevo_estado: str) -> None:
        self.estado_entrega = nuevo_estado

    def confirmarEntrega(self) -> None:
        if self.repartidor is None:
            raise ValueError("No se puede confirmar una entrega sin repartidor asignado.")
        self.fecha_entrega = datetime.now()
        self.actualizarEstado("entregado")
        self.repartidor.disponibilidad = True

    def __repr__(self) -> str:
        return f"Entrega(#{self.id_entrega}, {self.estado_entrega})"
