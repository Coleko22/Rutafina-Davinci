from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .pedido import Pedido
    from .metodo_pago import MetodoPago


class Pago:
    def __init__(
        self,
        id_pago: int,
        pedido: "Pedido",
        metodo_pago: "MetodoPago",
        importe: float,
    ) -> None:
        self.id_pago = id_pago
        self.fecha: Optional[datetime] = None
        self.importe = importe
        self.estado_pago = "pendiente"
        self.pedido = pedido
        self.metodo_pago = metodo_pago

    def procesarPago(self) -> bool:
        """Simula el procesamiento del pago con el método elegido."""
        if not self.metodo_pago.verificarDisponibilidad():
            self.actualizarEstado("rechazado")
            return False
        self.fecha = datetime.now()
        self.actualizarEstado("aprobado")
        return True

    def actualizarEstado(self, nuevo_estado: str) -> None:
        self.estado_pago = nuevo_estado

    def __repr__(self) -> str:
        return f"Pago(${self.importe:.2f}, {self.estado_pago})"
