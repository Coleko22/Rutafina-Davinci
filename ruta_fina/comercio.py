from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .producto import Producto
    from .pedido import Pedido


class Comercio:
    def __init__(
        self,
        id_comercio: int,
        nombre: str,
        direccion: str,
        telefono: str,
        email: str,
        estado: str = "activo",
    ) -> None:
        self.id_comercio = id_comercio
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email
        self.estado = estado
        self.productos: list["Producto"] = []
        self.pedidos: list["Pedido"] = []

    def agregarProducto(self, producto: "Producto") -> None:
        self.productos.append(producto)

    def modificarProducto(self, id_producto: int, **campos) -> None:
        producto = self._buscarProducto(id_producto)
        for clave, valor in campos.items():
            if hasattr(producto, clave):
                setattr(producto, clave, valor)

    def eliminarProducto(self, id_producto: int) -> None:
        producto = self._buscarProducto(id_producto)
        self.productos.remove(producto)

    def aceptarPedido(self, pedido: "Pedido") -> None:
        self.actualizarEstadoPedido(pedido, "aceptado")
        pedido.confirmarPedido()

    def rechazarPedido(self, pedido: "Pedido") -> None:
        self.actualizarEstadoPedido(pedido, "rechazado")

    def actualizarEstadoPedido(self, pedido: "Pedido", estado: str) -> None:
        if pedido not in self.pedidos:
            raise ValueError("Ese pedido no pertenece a este comercio.")
        pedido.cambiarEstado(estado)

    def _buscarProducto(self, id_producto: int) -> "Producto":
        for producto in self.productos:
            if producto.id_producto == id_producto:
                return producto
        raise ValueError(f"Producto con id {id_producto} no encontrado en {self.nombre}.")

    def __repr__(self) -> str:
        return f"Comercio({self.nombre})"
