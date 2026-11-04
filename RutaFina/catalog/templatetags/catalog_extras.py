from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """Formato monetario argentino: 19600 -> '$ 19.600', 1250.5 -> '$ 1.250,50'."""
    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    texto = f'{abs(valor):,.2f}'  # '19,600.00'
    texto = texto.replace(',', '_').replace('.', ',').replace('_', '.')  # '19.600,00'
    if texto.endswith(',00'):
        texto = texto[:-3]
    signo = '-' if valor < 0 else ''
    return f'{signo}$ {texto}'


@register.filter
def iniciales(texto):
    """'Martín Rodríguez' -> 'MR'."""
    partes = str(texto or '').split()
    return ''.join(p[0] for p in partes[:2]).upper()


@register.filter
def ultimos(valor, n=4):
    texto = str(valor or '')
    return texto[-int(n):]


@register.filter
def interseca(etiquetas, restricciones):
    """Etiquetas legibles del ítem que coinciden con las restricciones del usuario."""
    from catalog.restaurantes import ETIQUETAS
    return [ETIQUETAS[e] for e in etiquetas if e in (restricciones or [])]


@register.filter
def en(valor, conjunto):
    """{{ clave|en:favoritos }} -> True si la clave está en el conjunto."""
    return valor in (conjunto or ())
