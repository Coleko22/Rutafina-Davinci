import base64
import io
from functools import wraps

import mercadopago
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from cart.carrito import Carrito
from catalog import restaurantes
from users.forms import DireccionForm
from users.models import Cliente, Repartidor
from users.views import favoritos_de
from . import servicios
from .forms import CheckoutForm, PagoTarjetaForm
from .models import MetodoPago, Pago, Pedido
from .validators import detectar_tipo_tarjeta


def _cliente(request):
    cliente, _ = Cliente.objects.get_or_create(usuario=request.user)
    return cliente


def _qr_data_uri(texto):
    """Genera el QR en memoria y lo devuelve como data URI (no se guarda ningún archivo)."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"


# =============================================================================
# Checkout (mockup 04)
# =============================================================================

@login_required
def checkout_view(request):
    carrito = Carrito(request)
    if carrito.vacio:
        messages.error(request, 'Tu carrito está vacío. Elegí algo primero.')
        return redirect(reverse('home') + '#comercios')

    cliente = _cliente(request)
    direcciones = list(cliente.direcciones.all())

    if request.method == 'POST':
        form = CheckoutForm(request.POST, cliente=cliente)
        if form.is_valid():
            # El cupón 'primera compra' se vuelve a chequear acá (ahora sí hay usuario seguro)
            try:
                pedido = servicios.crear_pedido(
                    cliente, carrito, form.cleaned_data['direccion'],
                    form.cleaned_data['metodo'], form.cleaned_data.get('tarjeta'))
            except servicios.ErrorPedido as error:
                messages.error(request, str(error))
            else:
                carrito.vaciar()
                request.session.pop('checkout_direccion', None)
                if pedido.metodo_pago.tipo == MetodoPago.Tipo.BILLETERA:
                    return redirect('pago_billetera', pedido_id=pedido.id)
                messages.success(request, f'Pedido #{pedido.id} confirmado.')
                return redirect('pedido_detalle', pedido_id=pedido.id)
    else:
        elegida = request.session.get('checkout_direccion')
        principal = next((d for d in direcciones if d.id == elegida), None) or (direcciones[0] if direcciones else None)
        form = CheckoutForm(cliente=cliente, initial={
            'direccion': principal.id if principal else None,
            'metodo': MetodoPago.Tipo.TARJETA,
        })

    return render(request, 'orders/checkout.html', {
        'form': form,
        'carrito': carrito,
        'direcciones': direcciones,
        'metodos': [(valor, nombre) for valor, nombre in MetodoPago.Tipo.choices],
        'next_checkout': reverse('checkout'),
        'direccion_form': DireccionForm(),
    })


# =============================================================================
# Seguimiento / detalle del pedido (mockup 05)
# =============================================================================

def _pedido_del_cliente(request, pedido_id):
    return get_object_or_404(
        Pedido.objects.select_related('entrega__repartidor__usuario', 'pago__metodo_pago', 'metodo_pago')
        .prefetch_related('detalles'),
        id=pedido_id, cliente__usuario=request.user)


@login_required
def pedido_detalle_view(request, pedido_id):
    pedido = _pedido_del_cliente(request, pedido_id)
    return render(request, 'orders/pedido_detalle.html', {
        'pedido': pedido,
        'pasos': pedido.pasos(),
        'pago': getattr(pedido, 'pago', None),
        'repartidor': pedido.repartidor,
        # Mientras el pedido está en curso, la página se refresca sola cada 30 s
        'auto_refresh': pedido.activo,
    })


@login_required
@require_POST
def cancelar_pedido_view(request, pedido_id):
    pedido = _pedido_del_cliente(request, pedido_id)
    try:
        servicios.cancelar_pedido(pedido)
    except servicios.ErrorPedido as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Cancelamos el pedido #{pedido.id}. No se te cobra nada.')
    return redirect('pedido_detalle', pedido_id=pedido.id)


# =============================================================================
# Historial y favoritos (mockup 06)
# =============================================================================

@login_required
def historial_view(request):
    cliente = _cliente(request)
    pedidos = cliente.pedidos.prefetch_related('detalles').all()

    favoritos = []
    for fav in request.user.favoritos.all():
        restaurante = fav.restaurante
        if restaurante is None or (fav.item_codigo and fav.item is None):
            continue  # el comercio o producto ya no existe en el catálogo
        favoritos.append({'fav': fav, 'restaurante': restaurante, 'item': fav.item})

    return render(request, 'orders/historial.html', {
        'pedidos': pedidos,
        'favoritos': favoritos,
        'favoritos_claves': favoritos_de(request.user),
        'hoy': timezone.localdate(),
    })


@login_required
@require_POST
def repetir_pedido_view(request, pedido_id):
    pedido = _pedido_del_cliente(request, pedido_id)
    restaurante = restaurantes.obtener(pedido.restaurante_slug)
    if restaurante is None:
        messages.error(request, 'Ese comercio ya no está disponible.')
        return redirect('historial')
    carrito = Carrito(request)
    carrito.cargar(restaurante, servicios.cantidades_para_repetir(pedido))
    if carrito.vacio:
        messages.error(request, 'Los productos de ese pedido ya no están en la carta.')
    else:
        messages.success(request, f'Cargamos tu pedido de {restaurante.nombre} en el carrito.')
    return redirect(reverse('detalle_restaurante', args=[restaurante.slug]) + '#carrito')


# =============================================================================
# Billetera virtual (Mercado Pago)
# =============================================================================

@login_required
def pago_billetera_view(request, pedido_id):
    pedido = _pedido_del_cliente(request, pedido_id)
    pago = getattr(pedido, 'pago', None)
    if pago is None or pago.estado_pago != Pago.Estado.PENDIENTE:
        return redirect('pedido_detalle', pedido_id=pedido.id)

    init_point = None
    retorno = request.build_absolute_uri(reverse('pago_billetera_retorno', args=[pedido.id]))
    try:
        sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        respuesta = sdk.preference().create({
            "items": [{
                "title": f"Pedido #{pedido.id} en {pedido.restaurante_nombre} (RABIA)",
                "quantity": 1,
                "unit_price": float(pedido.total),
                "currency_id": "ARS",
            }],
            "external_reference": str(pedido.id),
            "back_urls": {"success": retorno, "failure": retorno, "pending": retorno},
        })
        datos = respuesta.get("response", {})
        init_point = datos.get("init_point") or datos.get("sandbox_init_point")
    except Exception as error:  # sin token o sin conexión: seguimos con el fallback
        print(f"Error Mercado Pago API: {error}")

    if not init_point:
        init_point = "https://www.mercadopago.com.ar"

    return render(request, 'orders/pago_billetera.html', {
        'pedido': pedido,
        'init_point': init_point,
        'qr_data_uri': _qr_data_uri(init_point),
        'puede_simular': settings.DEBUG,
    })


@login_required
def pago_billetera_retorno_view(request, pedido_id):
    """
    Mercado Pago vuelve acá (back_urls) con ?status=approved|pending|rejected.
    Nota: en producción el pago se confirma por webhook (notificación del servidor
    de MP), no confiando en el parámetro de la URL. Para el TP alcanza con esto.
    """
    pedido = _pedido_del_cliente(request, pedido_id)
    estado = request.GET.get('status') or request.GET.get('collection_status')
    simulado = request.method == 'POST' and settings.DEBUG and request.POST.get('simular')
    if estado == 'approved' or simulado:
        Pago.objects.filter(pedido=pedido, estado_pago=Pago.Estado.PENDIENTE).update(estado_pago=Pago.Estado.APROBADO)
        messages.success(request, f'Pago aprobado. Pedido #{pedido.id} confirmado.')
    elif estado == 'rejected':
        messages.error(request, 'Mercado Pago rechazó el pago. Probá de nuevo o cambiá el medio de pago.')
        return redirect('pago_billetera', pedido_id=pedido.id)
    return redirect('pedido_detalle', pedido_id=pedido.id)


# =============================================================================
# Panel del repartidor (mockup 08)
# =============================================================================

def solo_repartidores(vista):
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not request.user.es_repartidor:
            raise Http404('Esta sección es solo para repartidores.')
        repartidor, _ = Repartidor.objects.get_or_create(
            usuario=request.user, defaults={'vehiculo': 'Moto', 'patente': ''})
        return vista(request, repartidor, *args, **kwargs)
    return envoltura


@solo_repartidores
def panel_repartidor_view(request, repartidor):
    activo = servicios.pedido_activo(repartidor)
    ahora = timezone.now()
    disponibles = []
    for pedido in servicios.pedidos_disponibles():
        espera = int((ahora - pedido.fecha_hora).total_seconds() // 60)
        disponibles.append({'pedido': pedido, 'espera_min': espera})

    checklist = []
    if activo:
        orden = ['Asignado', 'Retirado', 'En camino', 'Entregado']
        actual = orden.index(activo.entrega.estado_entrega) if activo.entrega.estado_entrega in orden else 0
        nombres = ['Asignado', 'Retirado del local', 'En camino', 'Entregado']
        en_camino = activo.entrega.estado_entrega == 'En camino'
        for i, nombre in enumerate(nombres):
            # "En camino" es un paso que dura: mientras se viaja queda como actual ("ahora").
            # En los demás, el actual es el próximo paso a marcar.
            if i < actual or (i == actual and not en_camino):
                estado = 'hecho'
            elif (i == actual and en_camino) or (i == actual + 1 and not en_camino):
                estado = 'actual'
            else:
                estado = 'pendiente'
            if estado == 'actual' and en_camino:
                nombre = f'{nombre} · ahora'
            checklist.append({'nombre': nombre, 'estado': estado})

    return render(request, 'orders/repartidor_panel.html', {
        'repartidor': repartidor,
        'activo': activo,
        'checklist': checklist,
        'texto_boton': servicios.TEXTO_BOTON.get(activo.entrega.estado_entrega) if activo else '',
        'disponibles': disponibles,
        'resumen': servicios.resumen_del_dia(repartidor),
        'auto_refresh': True,
    })


@require_POST
@solo_repartidores
def repartidor_en_linea_view(request, repartidor):
    repartidor.disponibilidad = not repartidor.disponibilidad
    repartidor.save(update_fields=['disponibilidad'])
    messages.success(request, 'Estás en línea.' if repartidor.disponibilidad else 'Te desconectaste. No vas a recibir pedidos.')
    return redirect('panel_repartidor')


@require_POST
@solo_repartidores
def repartidor_tomar_view(request, repartidor, pedido_id):
    try:
        pedido = servicios.tomar_pedido(repartidor, pedido_id)
    except servicios.ErrorPedido as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Tomaste el pedido #{pedido.id}. Andá a {pedido.restaurante_nombre}.')
    return redirect('panel_repartidor')


@require_POST
@solo_repartidores
def repartidor_avanzar_view(request, repartidor):
    try:
        pedido = servicios.avanzar_pedido(repartidor)
    except servicios.ErrorPedido as error:
        messages.error(request, str(error))
    else:
        if pedido.estado == Pedido.Estado.ENTREGADO:
            messages.success(request, f'Pedido #{pedido.id} entregado. ¡A por el próximo!')
    return redirect('panel_repartidor')


# =============================================================================
# Medios de pago (páginas existentes del proyecto, con el nuevo diseño)
# =============================================================================

@login_required
def metodos_pago_view(request):
    metodos = MetodoPago.objects.filter(disponible=True)
    return render(request, 'orders/metodos_pago.html', {'metodos': metodos})


@login_required
def simulador_tarjeta_view(request):
    if request.method == 'POST':
        form = PagoTarjetaForm(request.POST)
        if form.is_valid():
            numero = form.cleaned_data['numero_tarjeta']
            tipo_detectado = detectar_tipo_tarjeta(numero)
            messages.success(request, f"¡Tarjeta {tipo_detectado} validada con éxito! Operación simulada aprobada.")
            return render(request, 'orders/tarjeta_exito.html', {
                'titular': form.cleaned_data['titular'],
                'tipo': tipo_detectado,
                'ultimos4': numero[-4:]
            })
    else:
        form = PagoTarjetaForm()

    return render(request, 'orders/simulador_tarjeta.html', {'form': form})


@login_required
def mercadopago_simulado_view(request):
    init_point = None
    try:
        sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        preference_response = sdk.preference().create({
            "items": [{"title": "Pedido en RABIA Delivery", "quantity": 1, "unit_price": 50.0, "currency_id": "ARS"}]
        })
        response_data = preference_response.get("response", {})
        init_point = response_data.get("init_point") or response_data.get("sandbox_init_point")
    except Exception as e:
        print(f"Error Mercado Pago API: {e}")

    # Fallback si MP no devuelve preferencia o si no hay conexión
    if not init_point:
        init_point = "https://www.mercadopago.com.ar"

    return render(request, 'orders/mercadopago_checkout.html', {
        'init_point': init_point,
        'qr_data_uri': _qr_data_uri(init_point),
        'monto': "50.00",
    })
