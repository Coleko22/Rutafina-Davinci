"""
Lógica de negocio de pedidos, separada de las vistas para poder testearla
y reutilizarla (checkout, repetir pedido, panel del repartidor, comando seed_demo).
"""
import hashlib
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from . import avisos
from .models import DetallePedido, Entrega, MetodoPago, Pago, Pedido


class ErrorPedido(Exception):
    """Algo impide hacer la operación; el mensaje es apto para mostrar al usuario."""


# --- Distancia y pago al repartidor ---------------------------------------
# No hay mapas reales todavía: la distancia se estima de forma determinística a
# partir de las dos direcciones (siempre da lo mismo para el mismo par).

def estimar_km(origen, destino):
    huella = hashlib.sha256(f'{origen}|{destino}'.lower().encode()).digest()
    return Decimal(8 + huella[0] % 28) / 10  # entre 0,8 y 3,5 km


def calcular_pago_repartidor(km):
    monto = Decimal('1500') + Decimal('800') * km
    return (monto / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * 100


# --- Checkout ----------------------------------------------------------------

@transaction.atomic
def crear_pedido(cliente, carrito, direccion, metodo_tipo, tarjeta=None):
    """
    Convierte el carrito en un Pedido con sus detalles, Pago y Entrega.
    `tarjeta` es {'ultimos4', 'emisor'} cuando se paga con tarjeta (ya validada).
    No vacía el carrito: eso lo hace la vista después de confirmar.
    """
    restaurante = carrito.restaurante
    if restaurante is None or carrito.vacio:
        raise ErrorPedido('Tu carrito está vacío.')
    if direccion is None or direccion.cliente_id != cliente.id:
        raise ErrorPedido('Elegí una dirección de entrega.')
    metodo = MetodoPago.objects.filter(tipo=metodo_tipo, disponible=True).first()
    if metodo is None:
        raise ErrorPedido('Ese medio de pago no está disponible.')

    pedido = Pedido(
        cliente=cliente,
        restaurante_slug=restaurante.slug,
        restaurante_nombre=restaurante.nombre,
        restaurante_iniciales=restaurante.iniciales,
        restaurante_direccion=restaurante.direccion,
        metodo_pago=metodo,
        promo_codigo=carrito.promo.codigo if carrito.promo else '',
        cupon_codigo=carrito.cupon.codigo if carrito.cupon and carrito.descuento_cupon else '',
        direccion=direccion,
        direccion_texto=direccion.completa,
        direccion_referencia=direccion.referencia,
        subtotal=carrito.subtotal,
        envio=carrito.envio,
        descuento_promo=carrito.descuento_promo,
        descuento_cupon=carrito.descuento - carrito.descuento_promo,
        total=carrito.total,
    )
    pedido.save()  # fecha_hora se completa acá
    pedido.calcular_eta(restaurante.tiempo_max)
    pedido.save(update_fields=['eta'])

    DetallePedido.objects.bulk_create([
        DetallePedido(
            pedido=pedido, item_codigo=linea.item.codigo, nombre=linea.item.nombre,
            cantidad=linea.cantidad, precio_unitario=linea.item.precio, subtotal=linea.subtotal,
        )
        for linea in carrito.lineas
    ])

    if metodo_tipo == MetodoPago.Tipo.TARJETA:
        estado_pago = Pago.Estado.APROBADO
    elif metodo_tipo == MetodoPago.Tipo.EFECTIVO:
        estado_pago = Pago.Estado.A_COBRAR
    else:
        estado_pago = Pago.Estado.PENDIENTE  # billetera: se aprueba al volver de Mercado Pago
    Pago.objects.create(
        pedido=pedido, metodo_pago=metodo, importe=pedido.total, estado_pago=estado_pago,
        ultimos4=(tarjeta or {}).get('ultimos4', ''), emisor=(tarjeta or {}).get('emisor', ''),
    )

    km = estimar_km(restaurante.direccion, pedido.direccion_texto)
    Entrega.objects.create(pedido=pedido, distancia_km=km, pago_repartidor=calcular_pago_repartidor(km))
    return pedido


def cancelar_pedido(pedido):
    if not pedido.cancelable:
        raise ErrorPedido('Este pedido ya no se puede cancelar: el repartidor ya lo tomó.')
    with transaction.atomic():
        pedido.cambiar_estado(Pedido.Estado.CANCELADO)
        Entrega.objects.filter(pedido=pedido).update(estado_entrega=Entrega.Estado.CANCELADO)
        Pago.objects.filter(pedido=pedido).update(estado_pago=Pago.Estado.CANCELADO)


def cantidades_para_repetir(pedido):
    """{codigo: cantidad} del pedido, para volver a cargarlo en el carrito."""
    cantidades = {}
    for detalle in pedido.detalles.all():
        if detalle.item_codigo:
            cantidades[detalle.item_codigo] = cantidades.get(detalle.item_codigo, 0) + detalle.cantidad
    return cantidades


# --- Repartidor ---------------------------------------------------------------

def pedidos_disponibles():
    """
    Pedidos confirmados o en preparación que todavía no tienen repartidor.
    No se ofrecen los que pagan con billetera y todavía no volvieron de Mercado Pago
    (pago pendiente): si el cliente no termina de pagar, nadie sale a buscarlo.
    """
    return (Pedido.objects
            .filter(estado__in=[Pedido.Estado.CONFIRMADO, Pedido.Estado.PREPARACION],
                    entrega__repartidor__isnull=True)
            .exclude(pago__estado_pago=Pago.Estado.PENDIENTE)
            .select_related('entrega', 'metodo_pago')
            .prefetch_related('detalles')
            .order_by('fecha_hora'))


def pedido_activo(repartidor):
    return (Pedido.objects
            .filter(entrega__repartidor=repartidor, estado__in=Pedido.ACTIVOS)
            .select_related('entrega', 'cliente__usuario', 'metodo_pago')
            .first())


@transaction.atomic
def tomar_pedido(repartidor, pedido_id):
    if not repartidor.disponibilidad:
        raise ErrorPedido('Ponete en línea para tomar pedidos.')
    if pedido_activo(repartidor) is not None:
        raise ErrorPedido('Terminá el pedido activo antes de tomar otro.')
    # select_for_update evita que dos repartidores tomen el mismo pedido a la vez
    entrega = (Entrega.objects.select_for_update().select_related('pedido')
               .filter(pedido_id=pedido_id).first())
    if entrega is None or entrega.repartidor_id or entrega.pedido.estado not in (
            Pedido.Estado.CONFIRMADO, Pedido.Estado.PREPARACION):
        raise ErrorPedido('Ese pedido ya no está disponible.')
    if Pago.objects.filter(pedido_id=pedido_id, estado_pago=Pago.Estado.PENDIENTE).exists():
        raise ErrorPedido('Ese pedido todavía no está pago. Esperá a que el cliente termine de pagar.')
    entrega.repartidor = repartidor
    entrega.fecha_asignacion = timezone.now()
    entrega.estado_entrega = Entrega.Estado.ASIGNADO
    entrega.save()
    # Todavía no hay panel de comercio: asumimos que el local empieza a prepararlo
    # en cuanto hay repartidor asignado.
    if entrega.pedido.estado == Pedido.Estado.CONFIRMADO:
        entrega.pedido.cambiar_estado(Pedido.Estado.PREPARACION)
    return entrega.pedido


# Siguiente paso del repartidor: estado actual de la entrega -> (nuevo estado entrega, nuevo estado pedido)
SIGUIENTE_PASO = {
    Entrega.Estado.ASIGNADO: (Entrega.Estado.RETIRADO, Pedido.Estado.RETIRADO),
    Entrega.Estado.RETIRADO: (Entrega.Estado.EN_CAMINO, Pedido.Estado.EN_CAMINO),
    Entrega.Estado.EN_CAMINO: (Entrega.Estado.ENTREGADO, Pedido.Estado.ENTREGADO),
}
TEXTO_BOTON = {
    Entrega.Estado.ASIGNADO: 'Marcar retirado',
    Entrega.Estado.RETIRADO: 'Salgo en camino',
    Entrega.Estado.EN_CAMINO: 'Marcar entregado',
}


@transaction.atomic
def avanzar_pedido(repartidor):
    pedido = pedido_activo(repartidor)
    if pedido is None:
        raise ErrorPedido('No tenés ningún pedido activo.')
    entrega = pedido.entrega
    if entrega.estado_entrega not in SIGUIENTE_PASO:
        raise ErrorPedido('Este pedido no se puede avanzar.')
    nuevo_entrega, nuevo_pedido = SIGUIENTE_PASO[entrega.estado_entrega]
    entrega.estado_entrega = nuevo_entrega
    if nuevo_entrega == Entrega.Estado.ENTREGADO:
        entrega.fecha_entrega = timezone.now()
        # El efectivo se cobra en la puerta
        Pago.objects.filter(pedido=pedido, estado_pago=Pago.Estado.A_COBRAR).update(
            estado_pago=Pago.Estado.APROBADO)
    entrega.save()
    pedido.cambiar_estado(nuevo_pedido)
    if nuevo_pedido == Pedido.Estado.EN_CAMINO:
        # Se manda recién cuando se confirma la transacción (si algo falla, no avisamos de más)
        transaction.on_commit(lambda: avisos.avisar_pedido_en_camino(pedido))
    return pedido


def resumen_del_dia(repartidor):
    """Tarjetas 'Hoy / Ganado / Km' del panel."""
    hoy = timezone.localdate()
    entregas = Entrega.objects.filter(
        repartidor=repartidor, estado_entrega=Entrega.Estado.ENTREGADO, fecha_entrega__date=hoy)
    pedidos = entregas.count()
    ganado = sum((e.pago_repartidor for e in entregas), Decimal('0'))
    km = sum((e.distancia_km for e in entregas), Decimal('0'))
    return {'pedidos': pedidos, 'ganado': ganado, 'km': km}
