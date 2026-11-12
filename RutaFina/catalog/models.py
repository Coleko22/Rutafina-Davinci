import re
import unicodedata
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def normalizar_texto(texto):
    sin_tildes = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return sin_tildes.lower()


ETIQUETAS = {
    'sin_tacc': 'Sin TACC',
    'vegetariano': 'Vegetariano',
    'vegano': 'Vegano',
    'sin_lactosa': 'Sin lactosa',
}

SINONIMOS = {
    'sin_tacc': ('apto celiaco', 'apto celiacos', 'sin tacc', 'sin gluten', 'celiaco', 'celiacos', 'celiaca'),
    'vegetariano': ('vegetariano', 'vegetariana', 'vegetarianos', 'vegetarianas'),
    'vegano': ('vegano', 'vegana', 'veganos', 'veganas', 'vegan'),
    'sin_lactosa': ('sin lactosa', 'sin leche', 'deslactosado'),
}


def interpretar_busqueda(texto):
    resto = ' ' + re.sub(r'[^\w\s]', ' ', normalizar_texto(texto)) + ' '
    resto = re.sub(r'\s+', ' ', resto)
    etiquetas = []
    for clave, frases in SINONIMOS.items():
        for frase in frases:
            if f' {frase} ' in resto:
                resto = resto.replace(f' {frase} ', ' ')
                if clave not in etiquetas:
                    etiquetas.append(clave)
    return etiquetas, resto.split()


class Rubro(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=80)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Comercio(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comercio_gestionado',
    )
    rubro = models.ForeignKey(Rubro, on_delete=models.PROTECT, related_name='comercios')
    slug = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=150)
    iniciales = models.CharField(max_length=4)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('4.5'))
    cocina = models.CharField(max_length=80)
    tiempo_min = models.PositiveSmallIntegerField(default=20)
    tiempo_max = models.PositiveSmallIntegerField(default=35)
    costo_envio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    cierre = models.CharField(max_length=20, default='00 h')
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    acento = models.BooleanField(default=False, help_text='Iniciales en naranja en la tarjeta del home.')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def categorias(self):
        return list(self.categorias_menu.all())

    @property
    def items(self):
        return list(self.productos.filter(disponible=True).select_related('categoria'))

    @property
    def promo(self):
        return self.promociones.filter(activa=True).first()

    @property
    def badge(self):
        promo = self.promo
        return promo.badge if promo else ''

    def item(self, codigo):
        return self.productos.filter(codigo=codigo, disponible=True).select_related('categoria').first()

    def buscar(self, texto='', categoria=''):
        qs = self.productos.filter(disponible=True).select_related('categoria')
        if categoria:
            qs = qs.filter(categoria__slug=categoria)
        etiquetas, palabras = interpretar_busqueda(texto)
        for et in etiquetas:
            qs = qs.filter(**{et: True})
        items = list(qs)
        if palabras:
            items = [
                i for i in items
                if any(p in normalizar_texto(f'{i.nombre} {i.descripcion}') for p in palabras)
            ]
        return items


class CategoriaMenu(models.Model):
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name='categorias_menu')
    slug = models.SlugField(max_length=60)
    nombre = models.CharField(max_length=100)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']
        constraints = [
            models.UniqueConstraint(fields=['comercio', 'slug'], name='categoria_unica_por_comercio'),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.comercio.nombre})"


class Producto(models.Model):
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(
        CategoriaMenu,
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True,
    )
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    disponible = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    # Etiquetas alimentarias
    sin_tacc = models.BooleanField('Sin TACC', default=False)
    vegetariano = models.BooleanField(default=False)
    vegano = models.BooleanField(default=False)
    sin_lactosa = models.BooleanField('Sin lactosa', default=False)

    class Meta:
        ordering = ['categoria__orden', 'orden', 'id']
        constraints = [
            models.UniqueConstraint(fields=['comercio', 'codigo'], name='codigo_unico_por_comercio'),
        ]

    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.comercio.nombre})"

    @property
    def etiquetas(self):
        return tuple(k for k in ETIQUETAS if getattr(self, k))

    @property
    def etiquetas_legibles(self):
        return [ETIQUETAS[e] for e in self.etiquetas]


class PromocionComercio(models.Model):
    class Tipo(models.TextChoices):
        DOS_POR_UNO = '2x1', '2x1 en producto'
        PORCENTAJE = 'porcentaje', 'Porcentaje en el total'
        ENVIO_GRATIS = 'envio_gratis', 'Envío gratis con mínimo'

    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name='promociones')
    codigo = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    porcentaje = models.PositiveSmallIntegerField(default=0)
    minimo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    badge = models.CharField(max_length=30, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo} ({self.comercio.nombre})"

    @property
    def item_codigo(self):
        return self.producto.codigo if self.producto else ''


class Cupon(models.Model):
    class Tipo(models.TextChoices):
        PORCENTAJE = 'porcentaje', 'Porcentaje de descuento'
        ENVIO_GRATIS = 'envio_gratis', 'Envío gratis'

    codigo = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    porcentaje = models.PositiveSmallIntegerField(default=0)
    tope = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    minimo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    solo_primera_compra = models.BooleanField(default=False)
    descripcion = models.CharField(max_length=255, blank=True)

    # Datos para mostrar en tarjetas del home
    destacado_home = models.BooleanField(default=False)
    titulo_home = models.CharField(max_length=30, blank=True)
    subtitulo_home = models.CharField(max_length=80, blank=True)
    vence_texto = models.CharField(max_length=50, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo