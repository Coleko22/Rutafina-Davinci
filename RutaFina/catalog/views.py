from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from cart.carrito import Carrito
from users.views import favoritos_de
from . import promos, restaurantes
from .models import Comercio, Producto


def home_catalogo_view(request):
    """
    Home (mockup 01): hero, promos vigentes, chips de categorías y grilla de comercios.
    Filtros por querystring: ?categoria=<rubro>&orden=<rapidos|puntuados|envio>.
    """
    rubro = request.GET.get('categoria', '')
    if rubro not in {r.slug for r in restaurantes.rubros()}:
        rubro = ''
    orden = request.GET.get('orden', 'rapidos')
    if orden not in restaurantes.ORDENES:
        orden = 'rapidos'

    return render(request, 'catalog/home_catalogo.html', {
        'restaurantes': restaurantes.todos(rubro, orden),
        'rubros': restaurantes.rubros(),
        'rubro_activo': rubro,
        'orden': orden,
        'ordenes': [(clave, nombre) for clave, (nombre, _) in restaurantes.ORDENES.items()],
        'promos': promos.vigentes(),
        'favoritos': favoritos_de(request.user),
        # Comercios cargados desde el admin (modelo catalog.Comercio), si hay
        'comercios': Comercio.objects.filter(estado='Activo'),
    })


def buscar_view(request):
    """
    Buscador del header. Si todo lo encontrado es de un solo comercio, va directo
    a su carta con la búsqueda aplicada (como en el mockup 03).
    """
    texto = request.GET.get('q', '').strip()[:80]
    if not texto:
        return redirect('home')
    resultados = restaurantes.buscar_global(texto)
    if len(resultados) == 1:
        restaurante = resultados[0][0]
        return redirect(f"{reverse('detalle_restaurante', args=[restaurante.slug])}?{urlencode({'q': texto})}")
    return render(request, 'catalog/buscar.html', {
        'q': texto,
        'resultados': resultados,
        'favoritos': favoritos_de(request.user),
    })


def productos_por_categoria_view(request, categoria_nombre):
    """
    Muestra todos los productos disponibles que pertenecen a una categoría específica,
    indicando el comercio de cada uno (modelo catalog.Producto, cargado desde el admin).
    """
    productos = Producto.objects.filter(
        categoria__iexact=categoria_nombre,
        disponible=True,
        comercio__estado='Activo'
    ).select_related('comercio')

    return render(request, 'catalog/productos_categoria.html', {
        'categoria_nombre': categoria_nombre,
        'productos': productos,
    })


def detalle_comercio_view(request, comercio_id):
    """
    Muestra la información de un comercio puntual y toda su carta de productos disponibles
    (modelo catalog.Comercio, cargado desde el admin).
    """
    comercio = get_object_or_404(Comercio, pk=comercio_id, estado='Activo')
    productos = comercio.productos.filter(disponible=True)

    return render(request, 'catalog/detalle_comercio.html', {
        'comercio': comercio,
        'productos': productos,
    })


def detalle_restaurante_view(request, slug):
    """
    Página de un restaurante: cabecera, carta con buscador y filtro por categoría
    (?q=...&categoria=...) y el carrito lateral. Los datos salen de
    catalog/restaurantes.py (hardcodeados por ahora).
    """
    restaurante = restaurantes.obtener(slug)
    if restaurante is None:
        raise Http404('Ese restaurante no existe.')

    texto = request.GET.get('q', '').strip()[:80]
    categoria = request.GET.get('categoria', '')
    if categoria not in {c.slug for c in restaurante.categorias}:
        categoria = ''
    # Sin búsqueda ni categoría elegida arrancamos en la primera pestaña (Burgers).
    if not texto and not categoria:
        categoria = restaurante.categorias[0].slug

    cliente = getattr(request.user, 'perfil_cliente', None) if request.user.is_authenticated else None

    return render(request, 'catalog/restaurante.html', {
        'restaurante': restaurante,
        'items': restaurante.buscar(texto, categoria),
        'q': texto,
        'categoria_activa': categoria,
        'carrito': Carrito(request),
        'next_url': request.get_full_path(),
        'favoritos': favoritos_de(request.user),
        'restricciones': cliente.restricciones if cliente else [],
    })
