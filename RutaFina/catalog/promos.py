from dataclasses import dataclass

from .models import Cupon


@dataclass(frozen=True)
class PromoHome:
    """Tarjeta de 'Promos vigentes' del home."""
    titulo: str
    subtitulo: str
    descripcion: str
    codigo: str
    vence: str


def cupon(codigo):
    clave = (codigo or '').strip().upper()
    if not clave:
        return None
    return Cupon.objects.filter(codigo=clave, activo=True).first()


def vigentes():
    """Tarjetas destacadas en el home leídas desde catalog.Cupon."""
    destacados = Cupon.objects.filter(activo=True, destacado_home=True).order_by('id')
    return [
        PromoHome(
            titulo=c.titulo_home,
            subtitulo=c.subtitulo_home,
            descripcion=c.descripcion,
            codigo=c.codigo,
            vence=c.vence_texto,
        )
        for c in destacados
    ]