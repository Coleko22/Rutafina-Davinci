from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog import restaurantes
from .carrito import Carrito


def _destino(request, carrito):
    """
    A dónde volver después de modificar el carrito: el `next` del formulario
    (la página donde estaba el usuario, con su búsqueda/categoría) si es una
    URL propia; si no, el restaurante del carrito o el inicio.
    """
    destino = request.POST.get('next', '')
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    if carrito.slug:
        return reverse('detalle_restaurante', args=[carrito.slug])
    return reverse('home')


def _responder(request, carrito):
    """
    Con JavaScript (fetch) devuelve solo el panel del carrito para reemplazarlo
    sin recargar la página; sin JavaScript hace redirect clásico (POST/redirect/GET).
    """
    destino = _destino(request, carrito)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'cart/_carrito.html', {'carrito': carrito, 'next_url': destino})
    return redirect(destino)


@require_POST
def agregar(request, slug, codigo):
    restaurante = restaurantes.obtener(slug)
    item = restaurante.item(codigo) if restaurante else None
    if item is None:
        raise Http404('Ese producto no existe.')
    carrito = Carrito(request)
    carrito.agregar(restaurante, item)
    return _responder(request, carrito)


@require_POST
def restar(request, codigo):
    carrito = Carrito(request)
    carrito.restar(codigo)
    return _responder(request, carrito)


@require_POST
def eliminar(request, codigo):
    carrito = Carrito(request)
    carrito.eliminar(codigo)
    return _responder(request, carrito)


@require_POST
def aplicar_cupon(request):
    """Formulario 'Código de descuento' del checkout (catalog/promos.py)."""
    carrito = Carrito(request)
    codigo = request.POST.get('codigo', '')
    if request.POST.get('quitar'):
        carrito.quitar_cupon()
        messages.success(request, 'Quitamos el código.')
    elif carrito.aplicar_cupon(codigo):
        aviso = carrito.aviso_cupon
        if aviso:
            messages.error(request, aviso)
        else:
            messages.success(request, f'Código {carrito.cupon.codigo} aplicado.')
    else:
        messages.error(request, 'Ese código no existe o ya venció.')
    return redirect(_destino(request, carrito))
