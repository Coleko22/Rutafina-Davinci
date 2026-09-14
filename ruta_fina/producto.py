from __future__ import annotations


class Producto:
    def __init__(
        self,
        id_producto: int,
        nombre: str,
        descripcion: str,
        precio: float,
        categoria: str,
        disponible: bool = True,
    ) -> None:
        self.id_producto = id_producto
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.disponible = disponible
        self.categoria = categoria

    def cambiarPrecio(self, nuevo_precio: float) -> None:
        if nuevo_precio < 0:
            raise ValueError("El precio no puede ser negativo.")
        self.precio = nuevo_precio

    def cambiarDisponibilidad(self) -> None:
        self.disponible = not self.disponible

    def __repr__(self) -> str:
        return f"Producto({self.nombre}, ${self.precio:.2f})"
