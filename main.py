"""
Demo del modelo Ruta Fina.

Simula el flujo completo: un cliente busca productos, arma un pedido,
paga y un repartidor lo entrega.

Ejecutar con:  python main.py
"""

from datetime import date

from ruta_fina import (
    Cliente,
    Repartidor,
    Direccion,
    Comercio,
    Producto,
    MetodoPago,
    Promocion,
)


def main() -> None:
    # --- Usuarios ---
    cliente = Cliente(
        id_usuario=1,
        nombre="Colo",
        apellido="Fernandez",
        email="colo@example.com",
        contrasena="1234",
        telefono="11-5555-0001",
    )

    repartidor = Repartidor(
        id_usuario=2,
        nombre="Juan",
        apellido="Perez",
        email="juan@example.com",
        contrasena="abcd",
        telefono="11-5555-0002",
        vehiculo="Moto",
        patente="AB123CD",
    )

    print(f"Login cliente OK: {cliente.iniciarSesion('1234')}")

    # --- Dirección ---
    direccion = Direccion(
        id_direccion=1,
        calle="Av. Corrientes",
        numero="1234",
        localidad="CABA",
        codigo_postal="C1043",
        alias="Casa",
    )
    cliente.agregarDireccion(direccion)

    # --- Comercio y catálogo ---
    comercio = Comercio(
        id_comercio=1,
        nombre="Pizzeria Ruta Fina",
        direccion="Av. Corrientes 4000",
        telefono="11-4444-0000",
        email="contacto@rutafina.com",
    )
    muzza = Producto(1, "Pizza Muzzarella", "Clásica de muzzarella", 6500.0, "Pizzas")
    napo = Producto(2, "Pizza Napolitana", "Con tomate y ajo", 7200.0, "Pizzas")
    comercio.agregarProducto(muzza)
    comercio.agregarProducto(napo)

    # --- Método de pago y promoción ---
    metodo = MetodoPago(1, "Tarjeta de crédito", "tarjeta")
    promo = Promocion(
        id_promocion=1,
        titulo="20% en pizzas",
        descripcion="Descuento de lanzamiento",
        porcentaje_descuento=20,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )
    metodo.agregarPromocion(promo)

    print("Promos vigentes:", cliente.verPromociones([promo]))

    # --- Búsqueda y armado de pedido ---
    encontrados = cliente.buscarProducto(comercio.productos, "pizza")
    print("Productos encontrados:", encontrados)

    pedido = cliente.realizarPedido(comercio)
    pedido.agregarProducto(muzza, cantidad=2)
    pedido.agregarProducto(napo, cantidad=1)
    print("Total antes de descuento:", pedido.calcularTotal())

    descuento = promo.calcularDescuento(pedido.total)
    pedido.total = round(pedido.total - descuento, 2)
    print(f"Descuento aplicado: ${descuento} -> Total final: ${pedido.total}")

    # --- Pago y confirmación ---
    cliente.seleccionarMetodoPago(metodo)
    pago = pedido.confirmarPedido()
    exito = pago.procesarPago()
    print(f"Pago procesado: {exito} -> estado: {pago.estado_pago}")

    # --- Comercio acepta el pedido ---
    comercio.aceptarPedido(pedido)

    # --- Entrega ---
    repartidor.aceptarEntrega(pedido.entrega)
    repartidor.actualizarEstadoEntrega(pedido.entrega, "en camino")
    pedido.entrega.confirmarEntrega()

    print("\n--- Resumen final ---")
    print(pedido)
    print(pedido.entrega)
    print(pago)
    print("Repartidor disponible de nuevo:", repartidor.disponibilidad)


if __name__ == "__main__":
    main()
