from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .detalle_pedido import DetallePedido
from .pago import Pago
from .entrega import Entrega

if TYPE_CHECKING:
    from .usuario import Cliente
    from .comercio import Comercio
    from .producto import Producto
    from .metodo_pago import MetodoPago


class Pedido:
    def __init__(self, id_pedido: int, cliente: "Cliente", comercio: "Comercio") -> None:
        self.id_pedido = id_pedido
        self.fecha_hora = datetime.now()
        self.estado = "carrito"
        self.total = 0.0
        self.cliente = cliente
        self.comercio = comercio
        self.detalles: list[DetallePedido] = []
        self.pago: Optional[Pago] = None
        self.entrega: Optional[Entrega] = None

    def agregarProducto(self, producto: "Producto", cantidad: int = 1) -> DetallePedido:
        detalle = DetallePedido(producto, cantidad)
        self.detalles.append(detalle)
        self.calcularTotal()
        return detalle

    def eliminarProducto(self, producto: "Producto") -> None:
        self.detalles = [d for d in self.detalles if d.producto is not producto]
        self.calcularTotal()

    def calcularTotal(self) -> float:
        self.total = round(sum(d.calcularSubtotal() for d in self.detalles), 2)
        return self.total

    def cambiarEstado(self, nuevo_estado: str) -> None:
        self.estado = nuevo_estado

    def confirmarPedido(self, metodo_pago: Optional["MetodoPago"] = None) -> Pago:
        """Confirma el pedido, genera el Pago y la Entrega asociados."""
        if not self.detalles:
            raise ValueError("No se puede confirmar un pedido sin productos.")

        metodo = metodo_pago or self.cliente.metodo_pago_seleccionado
        if metodo is None:
            raise ValueError("El cliente debe seleccionar un método de pago.")

        self.cambiarEstado("confirmado")

        self.pago = Pago(id_pago=self.id_pedido, pedido=self, metodo_pago=metodo, importe=self.total)
        self.entrega = Entrega(id_entrega=self.id_pedido, pedido=self)
        return self.pago

    def cancelarPedido(self) -> None:
        self.cambiarEstado("cancelado")
        if self.pago:
            self.pago.actualizarEstado("cancelado")
        if self.entrega:
            self.entrega.actualizarEstado("cancelada")

    def __repr__(self) -> str:
        return f"Pedido(#{self.id_pedido}, {self.estado}, ${self.total:.2f})"
