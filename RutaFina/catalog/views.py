from django.shortcuts import render, get_object_or_404
from .models import Comercio, Producto

def home_catalogo_view(request):
    """
    Página principal del catálogo:
    Muestra los comercios activos y la lista de categorías existentes en los productos.
    """
    comercios = Comercio.objects.filter(estado='Activo')
    
    # Obtenemos las categorías únicas que tienen productos disponibles actualmente
    categorias = (
        Producto.objects.filter(disponible=True)
        .values_list('categoria', flat=True)
        .distinct()
        .order_by('categoria')
    )

    return render(request, 'catalog/home_catalogo.html', {
        'comercios': comercios,
        'categorias': categorias,
    })


def productos_por_categoria_view(request, categoria_nombre):
    """
    Muestra todos los productos disponibles que pertenecen a una categoría específica,
    indicando el comercio de cada uno.
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
    Muestra la información de un comercio puntual y toda su carta de productos disponibles.
    """
    comercio = get_object_or_404(Comercio, pk=comercio_id, estado='Activo')
    productos = comercio.productos.filter(disponible=True)

    return render(request, 'catalog/detalle_comercio.html', {
        'comercio': comercio,
        'productos': productos,
    })