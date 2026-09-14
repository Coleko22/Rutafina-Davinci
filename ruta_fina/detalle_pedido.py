from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .producto import Producto


class DetallePedido:
    def __init__(self, producto: "Producto", cantidad: int) -> None:
        self.producto = producto
        self.cantidad = cantidad
        self.precio_unitario = producto.precio
        self.subtotal = self.calcularSubtotal()

    def calcularSubtotal(self) -> float:
        self.subtotal = round(self.precio_unitario * self.cantidad, 2)
        return self.subtotal

    def __repr__(self) -> str:
        return f"{self.cantidad}x {self.producto.nombre} = ${self.subtotal:.2f}"
