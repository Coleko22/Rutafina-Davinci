"""
Fuente de datos TEMPORAL (hardcodeada) de los restaurantes y sus cartas.

Todo lo que muestran el home, las páginas de restaurante y el carrito sale de acá.
Las vistas y el carrito solo usan las funciones públicas de este módulo
(`todos`, `obtener`, `rubros`, `buscar_global`) y los métodos de las dataclasses,
nunca acceden a los datos directamente. Cuando los restaurantes pasen a la base
de datos (catalog.Comercio / catalog.Producto) alcanza con reemplazar este
archivo por consultas al ORM que devuelvan objetos con los mismos atributos.

Para sumar un restaurante nuevo: definir otro `Restaurante(...)` más abajo y
agregarlo a la tupla de `RESTAURANTES`.
"""
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal


def _normalizar(texto):
    """Minúsculas y sin tildes, para que 'volcan' encuentre 'Volcán'."""
    sin_tildes = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return sin_tildes.lower()


# Etiquetas alimentarias de los productos. Coinciden con las restricciones
# que el usuario marca en su perfil (users.Cliente).
ETIQUETAS = {
    'sin_tacc': 'Sin TACC',
    'vegetariano': 'Vegetariano',
    'vegano': 'Vegano',
    'sin_lactosa': 'Sin lactosa',
}


@dataclass(frozen=True)
class Categoria:
    slug: str
    nombre: str


@dataclass(frozen=True)
class ItemMenu:
    """Equivalente a catalog.Producto."""
    codigo: str          # único dentro del restaurante (ej: 'B1')
    nombre: str
    descripcion: str
    precio: Decimal
    categoria: str       # slug de una Categoria del restaurante
    etiquetas: tuple = ()  # claves de ETIQUETAS

    @property
    def etiquetas_legibles(self):
        return [ETIQUETAS[e] for e in self.etiquetas if e in ETIQUETAS]


@dataclass(frozen=True)
class Promo:
    """
    Promoción automática del restaurante (se aplica sola en el carrito).
      - '2x1':          cada dos unidades de `item_codigo`, una es gratis.
      - 'porcentaje':   `porcentaje` % de descuento sobre el subtotal.
      - 'envio_gratis': envío $0 si el subtotal llega a `minimo`.
    `badge` es el texto corto que se muestra en la tarjeta del home.
    """
    codigo: str
    tipo: str
    item_codigo: str = ''
    porcentaje: int = 0
    minimo: Decimal = Decimal('0')
    badge: str = ''


@dataclass(frozen=True)
class Restaurante:
    """Equivalente a catalog.Comercio (más los datos de presentación)."""
    slug: str
    nombre: str
    iniciales: str
    rating: Decimal
    cocina: str
    tiempo_min: int
    tiempo_max: int
    costo_envio: Decimal
    cierre: str
    categorias: tuple
    items: tuple
    promo: Promo | None = None
    rubro: str = ''             # slug de RUBROS (chips del home)
    acento: bool = False        # iniciales en naranja (True) o tinta (False) en la tarjeta
    direccion: str = ''

    def item(self, codigo):
        for item in self.items:
            if item.codigo == codigo:
                return item
        return None

    def buscar(self, texto='', categoria=''):
        """
        Ítems de la carta, en el orden del menú. Filtra por categoría (slug) y/o
        por texto: alcanza con que el ítem contenga alguna de las palabras en su
        nombre o descripción (sin distinguir mayúsculas ni tildes).
        """
        items = [i for i in self.items if not categoria or i.categoria == categoria]
        palabras = _normalizar(texto).split()
        if palabras:
            items = [
                i for i in items
                if any(p in _normalizar(f'{i.nombre} {i.descripcion}') for p in palabras)
            ]
        return items

    @property
    def badge(self):
        return self.promo.badge if self.promo else ''


# ---------------------------------------------------------------------------
# Rubros (chips "Categorías" del home). El orden es el de la pantalla.
# ---------------------------------------------------------------------------
RUBROS = (
    Categoria('hamburguesas', 'Hamburguesas'),
    Categoria('pizza', 'Pizza'),
    Categoria('sushi', 'Sushi'),
    Categoria('empanadas', 'Empanadas'),
    Categoria('helado', 'Helado'),
    Categoria('farmacia', 'Farmacia'),
    Categoria('super', 'Súper'),
    Categoria('bebidas', 'Bebidas'),
)


FURIA_BURGER = Restaurante(
    slug='furia-burger',
    nombre='Furia Burger',
    iniciales='FB',
    rating=Decimal('4.8'),
    cocina='Hamburguesas',
    tiempo_min=20,
    tiempo_max=30,
    costo_envio=Decimal('900'),
    cierre='01 h',
    categorias=(
        Categoria('burgers', 'Burgers'),
        Categoria('combos', 'Combos'),
        Categoria('papas', 'Papas'),
        Categoria('bebidas', 'Bebidas'),
    ),
    items=(
        ItemMenu('B1', 'Doble Furia', 'Doble medallón, cheddar, panceta y salsa picante.', Decimal('9800'), 'burgers'),
        ItemMenu('B2', 'Doble Bronca', 'Doble carne, cebolla caramelizada y pepinos.', Decimal('9200'), 'burgers'),
        ItemMenu('B3', 'Doble Volcán', 'Jalapeños, cheddar fundido y salsa de ajo.', Decimal('10400'), 'burgers'),
        ItemMenu('B4', 'Doble Veggie Enojada', 'Dos medallones de garbanzo, rúcula y tomate.', Decimal('8900'), 'burgers',
                 ('vegetariano', 'vegano', 'sin_lactosa')),
        ItemMenu('C1', 'Combo Doble Furia', 'Doble Furia + papas + gaseosa 500 ml.', Decimal('13500'), 'combos'),
        ItemMenu('C2', 'Combo Bronca x2', 'Dos Doble Bronca + papas grandes.', Decimal('19900'), 'combos'),
        ItemMenu('P1', 'Papas Rabiosas', 'Papas bastón crocantes con salsa picante.', Decimal('4200'), 'papas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ItemMenu('D1', 'Gaseosa 500 ml', 'Cola, lima-limón o naranja.', Decimal('4500'), 'bebidas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
    ),
    promo=Promo(codigo='FURIA2X1', tipo='2x1', item_codigo='B1', badge='2x1'),
    rubro='hamburguesas',
    acento=True,
    direccion='Av. Juan B. Justo 1700',
)

PIZZA_VIOLENTA = Restaurante(
    slug='pizza-violenta',
    nombre='Pizza Violenta',
    iniciales='PV',
    rating=Decimal('4.6'),
    cocina='Pizza',
    tiempo_min=25,
    tiempo_max=35,
    costo_envio=Decimal('0'),
    cierre='00 h',
    categorias=(
        Categoria('pizzas', 'Pizzas'),
        Categoria('fainas', 'Fainá'),
        Categoria('bebidas', 'Bebidas'),
    ),
    items=(
        ItemMenu('Z1', 'Muzza Violenta', 'Muzzarella a lo bestia, orégano y aceitunas.', Decimal('11200'), 'pizzas',
                 ('vegetariano',)),
        ItemMenu('Z2', 'Napo Furiosa', 'Muzza, tomate en rodajas, ajo y albahaca.', Decimal('12400'), 'pizzas',
                 ('vegetariano',)),
        ItemMenu('Z3', 'Fugazzeta Rabiosa', 'Rellena de muzza con cebolla de verdad.', Decimal('13600'), 'pizzas',
                 ('vegetariano',)),
        ItemMenu('Z4', 'Calabresa Brava', 'Longaniza calabresa y ají molido.', Decimal('13200'), 'pizzas'),
        ItemMenu('F1', 'Fainá', 'Porción de fainá para ponerle encima.', Decimal('2500'), 'fainas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ItemMenu('D1', 'Cerveza 1 L', 'Rubia bien fría.', Decimal('5200'), 'bebidas', ('vegetariano', 'vegano')),
    ),
    rubro='pizza',
    direccion='Av. Scalabrini Ortiz 800',
)

SUSHI_SIN_PACIENCIA = Restaurante(
    slug='sushi-sin-paciencia',
    nombre='Sushi Sin Paciencia',
    iniciales='SP',
    rating=Decimal('4.7'),
    cocina='Sushi',
    tiempo_min=35,
    tiempo_max=45,
    costo_envio=Decimal('1200'),
    cierre='00 h',
    categorias=(
        Categoria('combinados', 'Combinados'),
        Categoria('rolls', 'Rolls'),
        Categoria('bebidas', 'Bebidas'),
    ),
    items=(
        ItemMenu('S1', 'Combinado Apurado 15', '15 piezas variadas: salmón, langostino y palta.', Decimal('16500'), 'combinados'),
        ItemMenu('S2', 'Combinado Impaciente 30', '30 piezas para compartir (o no).', Decimal('29800'), 'combinados'),
        ItemMenu('R1', 'Roll Filadelfia', 'Salmón, queso crema y palta. 8 piezas.', Decimal('9600'), 'rolls', ('sin_tacc',)),
        ItemMenu('R2', 'Roll Veggie Tenso', 'Palta, pepino y zanahoria. 8 piezas.', Decimal('7900'), 'rolls',
                 ('vegetariano', 'vegano', 'sin_lactosa')),
        ItemMenu('D1', 'Agua saborizada', 'Pomelo o limón, 500 ml.', Decimal('2800'), 'bebidas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
    ),
    promo=Promo(codigo='SUSHI20', tipo='porcentaje', porcentaje=20, badge='-20%'),
    rubro='sushi',
    acento=True,
    direccion='Av. Santa Fe 3100',
)

EMPANADAS_DEL_INFIERNO = Restaurante(
    slug='empanadas-del-infierno',
    nombre='Empanadas del Infierno',
    iniciales='EI',
    rating=Decimal('4.9'),
    cocina='Empanadas',
    tiempo_min=15,
    tiempo_max=25,
    costo_envio=Decimal('700'),
    cierre='23 h',
    categorias=(
        Categoria('empanadas', 'Empanadas'),
        Categoria('docenas', 'Docenas'),
    ),
    items=(
        ItemMenu('E1', 'Carne picante', 'Cortada a cuchillo, ají y comino.', Decimal('1300'), 'empanadas'),
        ItemMenu('E2', 'Jamón y queso', 'La que nunca falla.', Decimal('1200'), 'empanadas'),
        ItemMenu('E3', 'Humita', 'Choclo cremoso y salsa blanca.', Decimal('1200'), 'empanadas', ('vegetariano',)),
        ItemMenu('E4', 'Caprese', 'Tomate, muzza y albahaca.', Decimal('1200'), 'empanadas', ('vegetariano',)),
        ItemMenu('X1', 'Docena surtida', '12 empanadas a elección del cocinero enojado.', Decimal('14400'), 'docenas'),
    ),
    rubro='empanadas',
    direccion='Av. Córdoba 4200',
)

HELADO_HIRVIENDO = Restaurante(
    slug='helado-hirviendo',
    nombre='Helado Hirviendo',
    iniciales='HH',
    rating=Decimal('4.5'),
    cocina='Helado',
    tiempo_min=20,
    tiempo_max=30,
    costo_envio=Decimal('800'),
    cierre='01 h',
    categorias=(Categoria('potes', 'Potes'),),
    items=(
        ItemMenu('H1', 'Cuarto kilo', 'Hasta 2 gustos.', Decimal('5200'), 'potes', ('vegetariano', 'sin_tacc')),
        ItemMenu('H2', 'Medio kilo', 'Hasta 3 gustos.', Decimal('9200'), 'potes', ('vegetariano', 'sin_tacc')),
        ItemMenu('H3', 'Kilo', 'Hasta 4 gustos.', Decimal('16800'), 'potes', ('vegetariano', 'sin_tacc')),
        ItemMenu('H4', 'Sorbete de limón ½ kg', 'Al agua, sin lácteos.', Decimal('8600'), 'potes',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
    ),
    rubro='helado',
    direccion='Av. Cabildo 2000',
)

FARMACIA_YA = Restaurante(
    slug='farmacia-ya',
    nombre='Farmacia Ya',
    iniciales='FY',
    rating=Decimal('4.4'),
    cocina='Farmacia',
    tiempo_min=15,
    tiempo_max=20,
    costo_envio=Decimal('0'),
    cierre='24 h',
    categorias=(Categoria('cuidado', 'Cuidado personal'),),
    items=(
        ItemMenu('M1', 'Alcohol en gel 250 ml', 'Para las manos, no para el enojo.', Decimal('3200'), 'cuidado'),
        ItemMenu('M2', 'Protector solar FPS 50', '200 ml.', Decimal('14900'), 'cuidado'),
        ItemMenu('M3', 'Curitas x 20', 'Surtidas.', Decimal('2600'), 'cuidado'),
    ),
    rubro='farmacia',
    direccion='Av. Rivadavia 5000',
)

SUPER_GRUNON = Restaurante(
    slug='super-grunon',
    nombre='Súper Gruñón',
    iniciales='SG',
    rating=Decimal('4.3'),
    cocina='Súper',
    tiempo_min=30,
    tiempo_max=40,
    costo_envio=Decimal('1000'),
    cierre='22 h',
    categorias=(
        Categoria('almacen', 'Almacén'),
        Categoria('bebidas', 'Bebidas'),
    ),
    items=(
        ItemMenu('A1', 'Fideos secos 500 g', 'Tirabuzón.', Decimal('1900'), 'almacen', ('vegetariano', 'vegano', 'sin_lactosa')),
        ItemMenu('A2', 'Yerba 1 kg', 'Con palo, como debe ser.', Decimal('5600'), 'almacen',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ItemMenu('A3', 'Dulce de leche 400 g', 'Repostero.', Decimal('3400'), 'almacen', ('vegetariano', 'sin_tacc')),
        ItemMenu('B1', 'Agua mineral 2 L', 'Sin gas.', Decimal('1800'), 'bebidas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
    ),
    promo=Promo(codigo='GRUNON0', tipo='envio_gratis', minimo=Decimal('15000'), badge='Envío $0'),
    rubro='super',
    acento=True,
    direccion='Av. Corrientes 5100',
)

KIOSCO_RABIOSO = Restaurante(
    slug='kiosco-rabioso',
    nombre='Kiosco Rabioso',
    iniciales='KR',
    rating=Decimal('4.6'),
    cocina='Bebidas',
    tiempo_min=10,
    tiempo_max=20,
    costo_envio=Decimal('600'),
    cierre='03 h',
    categorias=(
        Categoria('bebidas', 'Bebidas'),
        Categoria('golosinas', 'Golosinas'),
    ),
    items=(
        ItemMenu('K1', 'Energizante 473 ml', 'Para seguir enojado hasta tarde.', Decimal('2900'), 'bebidas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ItemMenu('K2', 'Gaseosa 1,5 L', 'Cola.', Decimal('3300'), 'bebidas', ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ItemMenu('K3', 'Alfajor triple', 'Chocolate negro.', Decimal('1500'), 'golosinas', ('vegetariano',)),
        ItemMenu('K4', 'Papas fritas 150 g', 'Clásicas.', Decimal('2700'), 'golosinas',
                 ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
    ),
    rubro='bebidas',
    direccion='Av. Corrientes 5100',
)


# Acá se suman los otros restaurantes: el slug de cada uno es su URL.
RESTAURANTES = {r.slug: r for r in (
    FURIA_BURGER,
    PIZZA_VIOLENTA,
    SUSHI_SIN_PACIENCIA,
    EMPANADAS_DEL_INFIERNO,
    HELADO_HIRVIENDO,
    FARMACIA_YA,
    SUPER_GRUNON,
    KIOSCO_RABIOSO,
)}

ORDENES = {
    'rapidos': ('Más rápidos', lambda r: (r.tiempo_min, r.tiempo_max)),
    'puntuados': ('Mejor puntuados', lambda r: -r.rating),
    'envio': ('Envío más barato', lambda r: r.costo_envio),
}


def todos(rubro='', orden=''):
    """Restaurantes, opcionalmente filtrados por rubro y ordenados (ver ORDENES)."""
    lista = [r for r in RESTAURANTES.values() if not rubro or r.rubro == rubro]
    if orden in ORDENES:
        lista.sort(key=ORDENES[orden][1])
    return lista


def obtener(slug):
    """El restaurante con ese slug, o None si no existe."""
    return RESTAURANTES.get(slug)


def rubros():
    return list(RUBROS)


def buscar_global(texto):
    """
    Búsqueda del header: [(restaurante, [items que coinciden])]. Un restaurante
    aparece si coincide su nombre/cocina (con toda la carta) o algún ítem.
    """
    palabras = _normalizar(texto).split()
    if not palabras:
        return []
    resultados = []
    for restaurante in RESTAURANTES.values():
        items = restaurante.buscar(texto)
        propio = _normalizar(f'{restaurante.nombre} {restaurante.cocina}')
        if items or any(p in propio for p in palabras):
            resultados.append((restaurante, items))
    return resultados
