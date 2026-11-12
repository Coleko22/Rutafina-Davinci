from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from catalog.models import Comercio, Producto
from users.models import Cliente, Direccion, Repartidor


class MetodoPago(models.Model):
    class Tipo(models.TextChoices):
        TARJETA = 'Tarjeta', 'Tarjeta'
        BILLETERA = 'MercadoPago', 'Billetera virtual'
        EFECTIVO = 'Efectivo', 'Efectivo'

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)  # Ej: Tarjeta, Efectivo, MercadoPago
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=50, default='Vigente')

    def __str__(self):
        return f"{self.titulo} ({self.porcentaje_descuento}%)"


class Pedido(models.Model):
    """
    Un pedido confirmado. Como los restaurantes todavía están en
    catalog/restaurantes.py, el pedido guarda una "foto" (snapshot) del
    restaurante, los precios y la dirección al momento de confirmar: así el
    historial no cambia aunque después cambie la carta o se borre la dirección.
    """

    class Estado(models.TextChoices):
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        PREPARACION = 'PREPARACION', 'En preparación'
        RETIRADO = 'RETIRADO', 'Retirado'
        EN_CAMINO = 'EN_CAMINO', 'En camino'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    # Orden de la barra de progreso. Cada estado guarda su hora en el campo indicado.
    FLUJO = (
        (Estado.CONFIRMADO, 'fecha_hora'),
        (Estado.PREPARACION, 'preparacion_en'),
        (Estado.RETIRADO, 'retirado_en'),
        (Estado.EN_CAMINO, 'en_camino_en'),
        (Estado.ENTREGADO, 'entregado_en'),
    )
    ACTIVOS = (Estado.CONFIRMADO, Estado.PREPARACION, Estado.RETIRADO, Estado.EN_CAMINO)

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    # Para cuando los comercios estén en la base. Hoy queda vacío.
    comercio = models.ForeignKey(Comercio, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    restaurante_slug = models.SlugField(max_length=80, blank=True)
    restaurante_nombre = models.CharField(max_length=150, blank=True)
    restaurante_iniciales = models.CharField(max_length=4, blank=True)
    restaurante_direccion = models.CharField(max_length=255, blank=True)

    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, related_name='pedidos')
    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    cupon = models.ForeignKey('catalog.Cupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    
    promo_codigo = models.CharField(max_length=30, blank=True)
    cupon_codigo = models.CharField(max_length=30, blank=True)

    direccion = models.ForeignKey(Direccion, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    direccion_texto = models.CharField(max_length=255, blank=True)
    direccion_referencia = models.CharField(max_length=255, blank=True)

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.CONFIRMADO)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    preparacion_en = models.DateTimeField(null=True, blank=True)
    retirado_en = models.DateTimeField(null=True, blank=True)
    en_camino_en = models.DateTimeField(null=True, blank=True)
    entregado_en = models.DateTimeField(null=True, blank=True)
    cancelado_en = models.DateTimeField(null=True, blank=True)
    eta = models.DateTimeField('Llega aprox.', null=True, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    envio = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    descuento_promo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    descuento_cupon = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente} ({self.estado})"

    # --- Lectura ----------------------------------------------------------

    @property
    def cantidad_productos(self):
        return sum(d.cantidad for d in self.detalles.all())

    @property
    def activo(self):
        return self.estado in self.ACTIVOS

    @property
    def cancelable(self):
        """El cliente puede cancelar mientras ningún repartidor lo haya tomado."""
        return self.estado == self.Estado.CONFIRMADO and not self.tiene_repartidor

    @property
    def tiene_repartidor(self):
        entrega = getattr(self, 'entrega', None)
        return bool(entrega and entrega.repartidor_id)

    @property
    def repartidor(self):
        entrega = getattr(self, 'entrega', None)
        return entrega.repartidor if entrega else None

    def pasos(self):
        """
        Pasos de la barra de seguimiento: [{'nombre', 'hora', 'estado'}] donde
        estado es 'hecho', 'actual' o 'pendiente'.
        """
        orden = [estado for estado, _ in self.FLUJO]
        indice_actual = orden.index(self.estado) if self.estado in orden else -1
        pasos = []
        for i, (estado, campo) in enumerate(self.FLUJO):
            hora = getattr(self, campo)
            if self.estado == self.Estado.ENTREGADO or i < indice_actual:
                situacion = 'hecho'
            elif i == indice_actual:
                situacion = 'actual'
            else:
                situacion = 'pendiente'
            pasos.append({'nombre': estado.label, 'hora': hora, 'estado': situacion, 'clave': estado.value})
        return pasos

    # Recorrido dibujado en el mapa del seguimiento (coordenadas del viewBox 0 0 1100 420):
    # del local (abajo a la izquierda) a tu casa (arriba a la derecha).
    RUTA_MAPA = ((85, 345), (275, 345), (360, 230), (580, 230), (660, 128), (990, 128))

    @property
    def progreso(self):
        """De 0 a 1: qué parte del recorrido hizo el repartidor."""
        return {
            self.Estado.RETIRADO: 0.19,
            self.Estado.EN_CAMINO: 0.55,
            self.Estado.ENTREGADO: 1.0,
        }.get(self.estado, 0.0)

    def mapa(self):
        """Datos para el SVG: puntos de la ruta, posición del repartidor y largo del tramo hecho."""
        tramos = list(zip(self.RUTA_MAPA, self.RUTA_MAPA[1:]))
        largos = [((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5 for (x1, y1), (x2, y2) in tramos]
        objetivo = sum(largos) * self.progreso
        x, y = self.RUTA_MAPA[0]
        for ((x1, y1), (x2, y2)), largo in zip(tramos, largos):
            if objetivo <= largo:
                t = objetivo / largo if largo else 0
                x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                break
            objetivo -= largo
            x, y = x2, y2
        return {
            'puntos': ' '.join(f'{px},{py}' for px, py in self.RUTA_MAPA),
            'x': round(x), 'y': round(y),
            'hecho': round(self.progreso * 1000),
        }

    # --- Cambios de estado --------------------------------------------------

    def cambiar_estado(self, nuevo):
        """Pasa a `nuevo` y anota la hora. Rellena las horas de pasos salteados."""
        ahora = timezone.now()
        orden = [estado for estado, _ in self.FLUJO]
        if nuevo == self.Estado.CANCELADO:
            self.cancelado_en = ahora
        elif nuevo in orden:
            for estado, campo in self.FLUJO[: orden.index(nuevo) + 1]:
                if getattr(self, campo) is None:
                    setattr(self, campo, ahora)
        self.estado = nuevo
        self.save()

    def calcular_eta(self, minutos):
        self.eta = (self.fecha_hora or timezone.now()) + timedelta(minutes=minutos)


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    # Para cuando los productos estén en la base. Hoy se usa el snapshot de abajo.
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    item_codigo = models.CharField(max_length=20, blank=True)
    nombre = models.CharField(max_length=150, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.nombre or self.producto} en Pedido #{self.pedido_id}"


class Entrega(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'Pendiente', 'Esperando repartidor'
        ASIGNADO = 'Asignado', 'Asignado'
        RETIRADO = 'Retirado', 'Retirado del local'
        EN_CAMINO = 'En camino', 'En camino'
        ENTREGADO = 'Entregado', 'Entregado'
        CANCELADO = 'Cancelado', 'Cancelado'

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='entrega')
    repartidor = models.ForeignKey(Repartidor, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado_entrega = models.CharField(max_length=50, choices=Estado.choices, default=Estado.PENDIENTE)
    distancia_km = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    pago_repartidor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))

    def __str__(self):
        return f"Entrega de Pedido #{self.pedido_id} ({self.estado_entrega})"


class Pago(models.Model):
    class Estado(models.TextChoices):
        APROBADO = 'Aprobado', 'Aprobado'
        PENDIENTE = 'Pendiente', 'Pendiente'
        A_COBRAR = 'A cobrar', 'A cobrar en la entrega'
        CANCELADO = 'Cancelado', 'Cancelado'

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='pago')
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pago = models.CharField(max_length=50, choices=Estado.choices, default=Estado.APROBADO)
    ultimos4 = models.CharField('Últimos 4 dígitos', max_length=4, blank=True)
    emisor = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Pago #{self.id} - ${self.importe} ({self.estado_pago})"

    @property
    def descripcion(self):
        """'Tarjeta terminada en 4521' / 'Billetera virtual' / 'Efectivo'."""
        if self.ultimos4:
            return f"Tarjeta terminada en {self.ultimos4}"
        return self.metodo_pago.nombre
