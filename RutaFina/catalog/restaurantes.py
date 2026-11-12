from .models import ETIQUETAS, SINONIMOS, Comercio, Rubro, interpretar_busqueda, normalizar_texto

ORDENES = {
    'rapidos': ('Más rápidos', ('tiempo_min', 'tiempo_max', 'nombre')),
    'puntuados': ('Mejor puntuados', ('-rating', 'nombre')),
    'envio': ('Envío más barato', ('costo_envio', 'nombre')),
}


def _queryset_base():
    return (
        Comercio.objects
        .filter(activo=True)
        .select_related('rubro')
        .prefetch_related('categorias_menu', 'productos__categoria', 'promociones__producto')
    )


def todos(rubro='', orden=''):
    """Comercios activos de la BD, opcionalmente filtrados por rubro y ordenados."""
    qs = _queryset_base()
    if rubro:
        qs = qs.filter(rubro__slug=rubro)
    if orden in ORDENES:
        qs = qs.order_by(*ORDENES[orden][1])
    return list(qs)


def obtener(slug):
    """El comercio con ese slug en la BD, o None si no existe."""
    if not slug:
        return None
    return _queryset_base().filter(slug=slug).first()


def rubros():
    return list(Rubro.objects.all())


def buscar_global(texto):
    """
    Búsqueda del header sobre la base de datos: [(comercio, [productos que coinciden])].
    """
    etiquetas, palabras = interpretar_busqueda(texto)
    if not etiquetas and not palabras:
        return []
    resultados = []
    for comercio in _queryset_base():
        items = comercio.buscar(texto)
        propio = normalizar_texto(f'{comercio.nombre} {comercio.cocina}')
        coincide_nombre = not etiquetas and any(p in propio for p in palabras)
        if items or coincide_nombre:
            resultados.append((comercio, items))
    return resultados