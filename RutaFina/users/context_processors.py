"""
Context processor: variables que el header y el layout necesitan en TODAS las páginas.
Está registrado en settings.TEMPLATES['OPTIONS']['context_processors'].
"""
from django.utils.functional import SimpleLazyObject

from . import tono as tonos
from .models import Cliente


def _cliente(request):
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return None
    try:
        return usuario.perfil_cliente
    except Cliente.DoesNotExist:
        return None


def rabia(request):
    cliente = _cliente(request)
    tono = cliente.tono if cliente else tonos.DEFAULT

    def carrito():
        # Import local para no crear dependencia circular users -> cart -> orders -> users
        from cart.carrito import Carrito
        return Carrito(request)

    return {
        'cliente_actual': cliente,
        'tono': tono,
        'copy': tonos.textos(tono),
        'modo_oscuro': bool(cliente and cliente.modo_oscuro),
        # Lazy: solo se calcula si el template lo usa
        'carrito_header': SimpleLazyObject(carrito),
        'direcciones_header': SimpleLazyObject(lambda: list(cliente.direcciones.all()) if cliente else []),
    }
