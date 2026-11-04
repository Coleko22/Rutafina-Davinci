from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from catalog import promos, restaurantes

CERO = Decimal('0')


def _redondear(monto):
    """Los descuentos se redondean a pesos enteros."""
    return monto.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Linea:
    """Un producto del carrito con su cantidad."""
    item: restaurantes.ItemMenu
    cantidad: int

    @property
    def subtotal(self):
        return self.item.precio * self.cantidad


class Carrito:
    """
    Carrito guardado en la sesión del usuario (funciona sin estar logueado).

    En la sesión solo se guarda el slug del restaurante y {codigo: cantidad};
    precios y nombres se leen siempre del catálogo, así que si cambian no
    quedan desactualizados. El carrito es de UN solo restaurante a la vez
    (igual que Pedido, que tiene un único comercio): al agregar algo de otro
    restaurante, el carrito anterior se descarta.

    El cupón (catalog/promos.py) se guarda aparte, en SESSION_CUPON, para que
    sobreviva si el carrito se vacía y se vuelve a llenar.
    """
    SESSION_KEY = 'carrito'
    SESSION_CUPON = 'cupon'
    MAX_POR_ITEM = 20

    def __init__(self, request):
        self._request = request
        self._session = request.session
        guardado = self._session.get(self.SESSION_KEY) or {}
        self.slug = guardado.get('restaurante')
        self._cantidades = dict(guardado.get('items', {}))

    # --- Modificaciones -------------------------------------------------

    def agregar(self, restaurante, item):
        if self.slug != restaurante.slug:
            self.slug = restaurante.slug
            self._cantidades = {}
        actual = self._cantidades.get(item.codigo, 0)
        self._cantidades[item.codigo] = min(actual + 1, self.MAX_POR_ITEM)
        self._guardar()

    def restar(self, codigo):
        actual = self._cantidades.get(codigo)
        if actual is None:
            return
        if actual <= 1:
            del self._cantidades[codigo]
        else:
            self._cantidades[codigo] = actual - 1
        self._guardar()

    def eliminar(self, codigo):
        if self._cantidades.pop(codigo, None) is not None:
            self._guardar()

    def cargar(self, restaurante, cantidades):
        """Reemplaza el carrito entero (lo usa 'Repetir pedido'). Ignora códigos inexistentes."""
        self.slug = restaurante.slug
        self._cantidades = {
            codigo: min(int(cantidad), self.MAX_POR_ITEM)
            for codigo, cantidad in cantidades.items()
            if restaurante.item(codigo) is not None and int(cantidad) > 0
        }
        self._guardar()

    def vaciar(self):
        self._cantidades = {}
        self._guardar()
        self.quitar_cupon()

    def aplicar_cupon(self, codigo):
        """Guarda el cupón si existe. Devuelve el Cupon o None."""
        encontrado = promos.cupon(codigo)
        if encontrado is not None:
            self._session[self.SESSION_CUPON] = encontrado.codigo
            self._session.modified = True
        return encontrado

    def quitar_cupon(self):
        if self._session.pop(self.SESSION_CUPON, None) is not None:
            self._session.modified = True

    def _guardar(self):
        if self._cantidades:
            self._session[self.SESSION_KEY] = {
                'restaurante': self.slug,
                'items': self._cantidades,
            }
        else:
            self.slug = None
            self._session.pop(self.SESSION_KEY, None)
        self._session.modified = True

    # --- Lectura --------------------------------------------------------

    @property
    def restaurante(self):
        return restaurantes.obtener(self.slug) if self.slug else None

    @property
    def lineas(self):
        """Líneas del carrito; ignora códigos que ya no existen en el catálogo."""
        restaurante = self.restaurante
        if restaurante is None:
            return []
        lineas = []
        for codigo, cantidad in self._cantidades.items():
            item = restaurante.item(codigo)
            if item is not None:
                lineas.append(Linea(item, cantidad))
        return lineas

    @property
    def vacio(self):
        return not self.lineas

    @property
    def cantidad_lineas(self):
        """Cantidad de productos distintos (lo que se muestra en 'Tu carrito (3)')."""
        return len(self.lineas)

    @property
    def cantidad_unidades(self):
        return sum(linea.cantidad for linea in self.lineas)

    @property
    def subtotal(self):
        return sum((linea.subtotal for linea in self.lineas), CERO)

    @property
    def envio(self):
        restaurante = self.restaurante
        if restaurante is None or self.vacio:
            return CERO
        return restaurante.costo_envio

    # --- Promo automática del restaurante -------------------------------

    def _promo_aplicada(self):
        """(promo, descuento) si la promo del restaurante corresponde, si no (None, 0)."""
        restaurante = self.restaurante
        promo = restaurante.promo if restaurante else None
        if promo is None or self.vacio:
            return None, CERO
        if promo.tipo == '2x1':
            for linea in self.lineas:
                gratis = linea.cantidad // 2
                if linea.item.codigo == promo.item_codigo and gratis:
                    return promo, linea.item.precio * gratis
        elif promo.tipo == 'porcentaje':
            return promo, _redondear(self.subtotal * promo.porcentaje / 100)
        elif promo.tipo == 'envio_gratis':
            if self.subtotal >= promo.minimo and self.envio:
                return promo, self.envio
        return None, CERO

    @property
    def promo(self):
        return self._promo_aplicada()[0]

    @property
    def descuento_promo(self):
        return self._promo_aplicada()[1]

    # --- Cupón ------------------------------------------------------------

    @property
    def cupon(self):
        """El cupón cargado (aunque todavía no aplique)."""
        return promos.cupon(self._session.get(self.SESSION_CUPON))

    def _es_primera_compra(self):
        usuario = getattr(self._request, 'user', None)
        if usuario is None or not usuario.is_authenticated:
            return True  # se vuelve a chequear al confirmar, que exige login
        from orders.models import Pedido  # import local: orders no depende de cart
        return not Pedido.objects.filter(cliente__usuario=usuario).exclude(
            estado=Pedido.Estado.CANCELADO).exists()

    def _cupon_aplicado(self):
        """(descuento, aviso). Si el cupón no aplica, descuento 0 y un aviso de por qué."""
        cupon = self.cupon
        if cupon is None or self.vacio:
            return CERO, ''
        if cupon.solo_primera_compra and not self._es_primera_compra():
            return CERO, 'Este código es solo para tu primera compra.'
        if self.subtotal < cupon.minimo:
            return CERO, f'Este código aplica desde un subtotal de ${cupon.minimo:,.0f}.'.replace(',', '.')
        if cupon.tipo == 'porcentaje':
            monto = _redondear(self.subtotal * cupon.porcentaje / 100)
            if cupon.tope:
                monto = min(monto, cupon.tope)
            return monto, ''
        if cupon.tipo == 'envio_gratis':
            # Si la promo del restaurante ya regala el envío, no se descuenta dos veces.
            promo = self.promo
            if promo is not None and promo.tipo == 'envio_gratis':
                return CERO, 'El envío ya es gratis con la promo del local.'
            return self.envio, ''
        return CERO, ''

    @property
    def descuento_cupon(self):
        return self._cupon_aplicado()[0]

    @property
    def aviso_cupon(self):
        return self._cupon_aplicado()[1]

    # --- Totales ----------------------------------------------------------

    @property
    def descuento(self):
        """Suma de todos los descuentos (promo del local + cupón), sin pasarse del total."""
        return min(self.descuento_promo + self.descuento_cupon, self.subtotal + self.envio)

    @property
    def total(self):
        return self.subtotal + self.envio - self.descuento
