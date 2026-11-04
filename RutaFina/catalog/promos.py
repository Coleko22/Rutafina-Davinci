"""
Promos vigentes que se muestran en el home y cupones que se pueden cargar en el checkout.

Hay dos tipos de descuento en el sitio:
  1. La promo automática de cada restaurante (restaurantes.Promo): se aplica sola.
  2. Los cupones de este archivo: el usuario los escribe en el checkout.

Igual que restaurantes.py, es una fuente de datos temporal: cuando haya un modelo
(orders.Promocion) alcanza con cambiar `vigentes()` y `cupon()` por consultas al ORM.
"""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone


@dataclass(frozen=True)
class PromoHome:
    """Tarjeta de 'Promos vigentes' del home."""
    titulo: str        # '2x1', '-40%', '$0'
    subtitulo: str
    descripcion: str
    codigo: str
    vence: str


@dataclass(frozen=True)
class Cupon:
    codigo: str
    tipo: str                       # 'porcentaje' | 'envio_gratis'
    porcentaje: int = 0
    tope: Decimal = Decimal('0')    # descuento máximo (0 = sin tope)
    minimo: Decimal = Decimal('0')  # subtotal mínimo para que aplique
    solo_primera_compra: bool = False
    descripcion: str = ''


CUPONES = {c.codigo: c for c in (
    Cupon('ENOJADO40', 'porcentaje', porcentaje=40, tope=Decimal('5000'), solo_primera_compra=True,
          descripcion='40% en tu primera compra (tope $5.000)'),
    Cupon('SINENVIO', 'envio_gratis', minimo=Decimal('15000'),
          descripcion='Envío gratis en pedidos desde $15.000'),
)}


def cupon(codigo):
    return CUPONES.get((codigo or '').strip().upper())


def _fin_de_mes(hoy):
    siguiente = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1)
    return siguiente - timedelta(days=1)


def vigentes():
    """Las tres tarjetas del home. Las fechas se calculan para que siempre estén vigentes."""
    hoy = timezone.localdate()
    fin_mes = _fin_de_mes(hoy)
    en_dos_semanas = hoy + timedelta(days=14)
    return [
        PromoHome('2x1', 'Burgers dobles', 'En la Doble Furia de Furia Burger. Se aplica sola en el carrito.',
                  'FURIA2X1', f'Vence {en_dos_semanas:%d/%m}'),
        PromoHome('-40%', 'Tu primera compra', 'Tope de descuento de $5.000. Una vez por cuenta.',
                  'ENOJADO40', f'Vence {fin_mes:%d/%m}'),
        PromoHome('$0', 'Envío gratis', 'En pedidos mayores a $15.000 en tu zona.',
                  'SINENVIO', 'Hoy hasta 23 h'),
    ]
