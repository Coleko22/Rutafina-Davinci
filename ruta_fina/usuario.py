from __future__ import annotations

import hashlib
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .direccion import Direccion
    from .comercio import Comercio
    from .metodo_pago import MetodoPago
    from .pedido import Pedido
    from .producto import Producto
    from .promocion import Promocion
    from .entrega import Entrega


class Usuario:

    def __init__(
        self,
        id_usuario: int,
        nombre: str,
        apellido: str,
        email: str,
        contrasena: str,
        telefono: str,
    ) -> None:
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self._contrasena_hash = self._hashear(contrasena)
        self.telefono = telefono
        self._sesion_activa = False

    @staticmethod
    def _hashear(contrasena: str) -> str:
        return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()

    def iniciarSesion(self, contrasena: str) -> bool:
        if self._hashear(contrasena) == self._contrasena_hash:
            self._sesion_activa = True
            return True
        return False

    def cerrarSesion(self) -> None:
        self._sesion_activa = False

    def actualizarDatos(self, **campos) -> None:
        for clave, valor in campos.items():
            if hasattr(self, clave):
                setattr(self, clave, valor)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.nombre} {self.apellido})"


class Cliente(Usuario):

    def __init__(
        self,
        id_usuario: int,
        nombre: str,
        apellido: str,
        email: str,
        contrasena: str,
        telefono: str,
        fecha_registro: Optional[date] = None,
    ) -> None:
        super().__init__(id_usuario, nombre, apellido, email, contrasena, telefono)
        self.fecha_registro = fecha_registro or date.today()
        self.direcciones: list["Direccion"] = []
        self.pedidos: list["Pedido"] = []
        self.metodo_pago_seleccionado: Optional["MetodoPago"] = None

    def buscarProducto(self, catalogo: list["Producto"], termino: str) -> list["Producto"]:
        termino = termino.lower()
        return [
            p
            for p in catalogo
            if p.disponible
            and (termino in p.nombre.lower() or termino in p.categoria.lower())
        ]

    def realizarPedido(self, comercio: "Comercio") -> "Pedido":
        from .pedido import Pedido

        nuevo_id = len(self.pedidos) + 1
        pedido = Pedido(id_pedido=nuevo_id, cliente=self, comercio=comercio)
        self.pedidos.append(pedido)
        comercio.pedidos.append(pedido)
        return pedido

    def agregarDireccion(self, direccion: "Direccion") -> None:
        self.direcciones.append(direccion)

    def seleccionarMetodoPago(self, metodo: "MetodoPago") -> None:
        if not metodo.verificarDisponibilidad():
            raise ValueError(f"El método de pago '{metodo.nombre}' no está disponible.")
        self.metodo_pago_seleccionado = metodo

    def verPromociones(self, promociones: list["Promocion"]) -> list["Promocion"]:
        return [p for p in promociones if p.estaVigente()]


class Repartidor(Usuario):

    def __init__(
        self,
        id_usuario: int,
        nombre: str,
        apellido: str,
        email: str,
        contrasena: str,
        telefono: str,
        vehiculo: str,
        patente: str,
        disponibilidad: bool = True,
    ) -> None:
        super().__init__(id_usuario, nombre, apellido, email, contrasena, telefono)
        self.vehiculo = vehiculo
        self.patente = patente
        self.disponibilidad = disponibilidad
        self.entregas_asignadas: list["Entrega"] = []

    def aceptarEntrega(self, entrega: "Entrega") -> None:
        if not self.disponibilidad:
            raise ValueError(f"{self} no está disponible para tomar entregas.")
        entrega.asignarRepartidor(self)
        self.entregas_asignadas.append(entrega)
        self.disponibilidad = False

    def actualizarEstadoEntrega(self, entrega: "Entrega", estado: str) -> None:
        if entrega not in self.entregas_asignadas:
            raise ValueError("Esta entrega no está asignada a este repartidor.")
        entrega.actualizarEstado(estado)

    def cambiarDisponibilidad(self) -> None:
        self.disponibilidad = not self.disponibilidad
