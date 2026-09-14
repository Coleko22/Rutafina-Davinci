# Ruta Fina — Modelo de clases en Python

Implementación en Python de las clases del diagrama UML `UML_Ruta_Fina.drawio`
(app de delivery: clientes, comercios, productos, pedidos, pagos y entregas).

## Estructura

```
ruta_fina/
├── main.py                     # Demo con el flujo completo
└── ruta_fina/
    ├── __init__.py
    ├── usuario.py               # Usuario (base), Cliente, Repartidor
    ├── direccion.py             # Direccion
    ├── comercio.py               # Comercio
    ├── producto.py               # Producto
    ├── detalle_pedido.py         # DetallePedido
    ├── metodo_pago.py            # MetodoPago
    ├── promocion.py              # Promocion
    ├── pago.py                   # Pago
    ├── entrega.py                 # Entrega
    └── pedido.py                  # Pedido
```

## Relaciones implementadas

- **Herencia**: `Cliente` y `Repartidor` extienden `Usuario`.
- **Composición**: `Pedido` crea y contiene sus `DetallePedido`.
- **Asociaciones**: `Cliente` ↔ `Direccion`/`Pedido`, `Comercio` ↔ `Producto`/`Pedido`,
  `Pedido` ↔ `Pago`/`Entrega`, `MetodoPago` ↔ `Promocion`, `Entrega` ↔ `Repartidor`.

## Cómo correr el demo

```bash
python3 main.py
```

Simula: login de un cliente, búsqueda de productos, armado de un pedido,
aplicación de una promoción, selección de método de pago, procesamiento
del pago, aceptación del pedido por el comercio y entrega por un repartidor.

No requiere dependencias externas (solo la librería estándar de Python 3).
