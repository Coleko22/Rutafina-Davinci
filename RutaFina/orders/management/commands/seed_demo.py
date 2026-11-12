"""
Carga datos completos de demostración en la base de datos relacional:

    python manage.py seed_demo          # crea el catálogo, comercios y usuarios demo
    python manage.py seed_demo --reset  # borra datos demo y vuelve a poblar todo

Usuarios demo (contraseña de todos: rabia1234):
    thiago@mail.com   cliente, con direcciones, historial, favoritos y un pedido en camino
    martin@mail.com   repartidor, con el pedido de Thiago activo y entregas del día
    lucia@mail.com    cliente con pedidos esperando repartidor (los "Pedidos disponibles")
"""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cart.carrito import Carrito
from catalog import restaurantes
from catalog.models import CategoriaMenu, Comercio, Cupon, Producto, PromocionComercio, Rubro
from orders import servicios
from orders.models import Entrega, MetodoPago, Pago, Pedido
from users.models import Cliente, Direccion, Favorito, Repartidor, User

PASSWORD = 'rabia1234'
EMAILS_DEMO = ('thiago@mail.com', 'martin@mail.com', 'lucia@mail.com')


class _Sesion(dict):
    modified = False


def _pedido(cliente, direccion, slug, cantidades, metodo, hace, tarjeta=None):
    restaurante = restaurantes.obtener(slug)
    carrito = Carrito(SimpleNamespace(session=_Sesion(), user=cliente.usuario))
    carrito.cargar(restaurante, cantidades)
    pedido = servicios.crear_pedido(cliente, carrito, direccion, metodo, tarjeta)
    fecha = timezone.now() - hace
    Pedido.objects.filter(pk=pedido.pk).update(fecha_hora=fecha, eta=fecha + timedelta(minutes=restaurante.tiempo_max))
    pedido.refresh_from_db()
    return pedido


def _avanzar(pedido, hasta, inicio, pasos_min=(2, 15, 6, 12)):
    campos = ['preparacion_en', 'retirado_en', 'en_camino_en', 'entregado_en']
    estados = [Pedido.Estado.PREPARACION, Pedido.Estado.RETIRADO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]
    momento = inicio
    for campo, estado, minutos in zip(campos, estados, pasos_min):
        momento += timedelta(minutes=minutos)
        setattr(pedido, campo, momento)
        pedido.estado = estado
        if estado == hasta:
            break
    pedido.save()


CATALOGO_INICIAL = [
    {
        'slug': 'furia-burger',
        'nombre': 'Furia Burger',
        'iniciales': 'FB',
        'rating': Decimal('4.8'),
        'cocina': 'Hamburguesas',
        'rubro': 'hamburguesas',
        'tiempo_min': 20,
        'tiempo_max': 30,
        'costo_envio': Decimal('900'),
        'cierre': '01 h',
        'acento': True,
        'direccion': 'Av. Juan B. Justo 1700',
        'telefono': '11 4800 1001',
        'email': 'contacto@furiaburger.local',
        'categorias': [
            ('burgers', 'Burgers'),
            ('combos', 'Combos'),
            ('papas', 'Papas'),
            ('bebidas', 'Bebidas'),
        ],
        'items': [
            ('B1', 'Doble Furia', 'Doble medallón, cheddar, panceta y salsa picante.', Decimal('9800'), 'burgers', ()),
            ('B2', 'Doble Bronca', 'Doble carne, cebolla caramelizada y pepinos.', Decimal('9200'), 'burgers', ()),
            ('B3', 'Doble Volcán', 'Jalapeños, cheddar fundido y salsa de ajo.', Decimal('10400'), 'burgers', ()),
            ('B4', 'Doble Veggie Enojada', 'Dos medallones de garbanzo, rúcula y tomate.', Decimal('8900'), 'burgers',
             ('vegetariano', 'vegano', 'sin_lactosa')),
            ('C1', 'Combo Doble Furia', 'Doble Furia + papas + gaseosa 500 ml.', Decimal('13500'), 'combos', ()),
            ('C2', 'Combo Bronca x2', 'Dos Doble Bronca + papas grandes.', Decimal('19900'), 'combos', ()),
            ('P1', 'Papas Rabiosas', 'Papas bastón crocantes con salsa picante.', Decimal('4200'), 'papas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
            ('D1', 'Gaseosa 500 ml', 'Cola, lima-limón o naranja.', Decimal('4500'), 'bebidas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ],
        'promo': {'codigo': 'FURIA2X1', 'tipo': '2x1', 'item_codigo': 'B1', 'badge': '2x1'},
    },
    {
        'slug': 'pizza-violenta',
        'nombre': 'Pizza Violenta',
        'iniciales': 'PV',
        'rating': Decimal('4.6'),
        'cocina': 'Pizza',
        'rubro': 'pizza',
        'tiempo_min': 25,
        'tiempo_max': 35,
        'costo_envio': Decimal('0'),
        'cierre': '00 h',
        'acento': False,
        'direccion': 'Av. Scalabrini Ortiz 800',
        'telefono': '11 4800 1002',
        'email': 'contacto@pizzaviolenta.local',
        'categorias': [
            ('pizzas', 'Pizzas'),
            ('fainas', 'Fainá'),
            ('bebidas', 'Bebidas'),
        ],
        'items': [
            ('Z1', 'Muzza Violenta', 'Muzzarella a lo bestia, orégano y aceitunas.', Decimal('11200'), 'pizzas', ('vegetariano',)),
            ('Z2', 'Napo Furiosa', 'Muzza, tomate en rodajas, ajo y albahaca.', Decimal('12400'), 'pizzas', ('vegetariano',)),
            ('Z3', 'Fugazzeta Rabiosa', 'Rellena de muzza con cebolla de verdad.', Decimal('13600'), 'pizzas', ('vegetariano',)),
            ('Z4', 'Calabresa Brava', 'Longaniza calabresa y ají molido.', Decimal('13200'), 'pizzas', ()),
            ('F1', 'Fainá', 'Porción de fainá para ponerle encima.', Decimal('2500'), 'fainas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
            ('D1', 'Cerveza 1 L', 'Rubia bien fría.', Decimal('5200'), 'bebidas', ('vegetariano', 'vegano')),
        ],
        'promo': None,
    },
    {
        'slug': 'sushi-sin-paciencia',
        'nombre': 'Sushi Sin Paciencia',
        'iniciales': 'SP',
        'rating': Decimal('4.7'),
        'cocina': 'Sushi',
        'rubro': 'sushi',
        'tiempo_min': 35,
        'tiempo_max': 45,
        'costo_envio': Decimal('1200'),
        'cierre': '00 h',
        'acento': True,
        'direccion': 'Av. Santa Fe 3100',
        'telefono': '11 4800 1003',
        'email': 'contacto@sushisinpaciencia.local',
        'categorias': [
            ('combinados', 'Combinados'),
            ('rolls', 'Rolls'),
            ('bebidas', 'Bebidas'),
        ],
        'items': [
            ('S1', 'Combinado Apurado 15', '15 piezas variadas: salmón, langostino y palta.', Decimal('16500'), 'combinados', ()),
            ('S2', 'Combinado Impaciente 30', '30 piezas para compartir (o no).', Decimal('29800'), 'combinados', ()),
            ('R1', 'Roll Filadelfia', 'Salmón, queso crema y palta. 8 piezas.', Decimal('9600'), 'rolls', ('sin_tacc',)),
            ('R2', 'Roll Veggie Tenso', 'Palta, pepino y zanahoria. 8 piezas.', Decimal('7900'), 'rolls',
             ('vegetariano', 'vegano', 'sin_lactosa')),
            ('D1', 'Agua saborizada', 'Pomelo o limón, 500 ml.', Decimal('2800'), 'bebidas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ],
        'promo': {'codigo': 'SUSHI20', 'tipo': 'porcentaje', 'porcentaje': 20, 'badge': '-20%'},
    },
    {
        'slug': 'empanadas-del-infierno',
        'nombre': 'Empanadas del Infierno',
        'iniciales': 'EI',
        'rating': Decimal('4.9'),
        'cocina': 'Empanadas',
        'rubro': 'empanadas',
        'tiempo_min': 15,
        'tiempo_max': 25,
        'costo_envio': Decimal('700'),
        'cierre': '23 h',
        'acento': False,
        'direccion': 'Av. Córdoba 4200',
        'telefono': '11 4800 1004',
        'email': 'contacto@empanadasinfierno.local',
        'categorias': [
            ('empanadas', 'Empanadas'),
            ('docenas', 'Docenas'),
        ],
        'items': [
            ('E1', 'Carne picante', 'Cortada a cuchillo, ají y comino.', Decimal('1300'), 'empanadas', ()),
            ('E2', 'Jamón y queso', 'La que nunca falla.', Decimal('1200'), 'empanadas', ()),
            ('E3', 'Humita', 'Choclo cremoso y salsa blanca.', Decimal('1200'), 'empanadas', ('vegetariano',)),
            ('E4', 'Caprese', 'Tomate, muzza y albahaca.', Decimal('1200'), 'empanadas', ('vegetariano',)),
            ('X1', 'Docena surtida', '12 empanadas a elección del cocinero enojado.', Decimal('14400'), 'docenas', ()),
        ],
        'promo': None,
    },
    {
        'slug': 'helado-hirviendo',
        'nombre': 'Helado Hirviendo',
        'iniciales': 'HH',
        'rating': Decimal('4.5'),
        'cocina': 'Helado',
        'rubro': 'helado',
        'tiempo_min': 20,
        'tiempo_max': 30,
        'costo_envio': Decimal('800'),
        'cierre': '01 h',
        'acento': False,
        'direccion': 'Av. Cabildo 2000',
        'telefono': '11 4800 1005',
        'email': 'contacto@heladohirviendo.local',
        'categorias': [('potes', 'Potes')],
        'items': [
            ('H1', 'Cuarto kilo', 'Hasta 2 gustos.', Decimal('5200'), 'potes', ('vegetariano', 'sin_tacc')),
            ('H2', 'Medio kilo', 'Hasta 3 gustos.', Decimal('9200'), 'potes', ('vegetariano', 'sin_tacc')),
            ('H3', 'Kilo', 'Hasta 4 gustos.', Decimal('16800'), 'potes', ('vegetariano', 'sin_tacc')),
            ('H4', 'Sorbete de limón ½ kg', 'Al agua, sin lácteos.', Decimal('8600'), 'potes',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ],
        'promo': None,
    },
    {
        'slug': 'farmacia-ya',
        'nombre': 'Farmacia Ya',
        'iniciales': 'FY',
        'rating': Decimal('4.4'),
        'cocina': 'Farmacia',
        'rubro': 'farmacia',
        'tiempo_min': 15,
        'tiempo_max': 20,
        'costo_envio': Decimal('0'),
        'cierre': '24 h',
        'acento': False,
        'direccion': 'Av. Rivadavia 5000',
        'telefono': '11 4800 1006',
        'email': 'contacto@farmaciaya.local',
        'categorias': [('cuidado', 'Cuidado personal')],
        'items': [
            ('M1', 'Alcohol en gel 250 ml', 'Para las manos, no para el enojo.', Decimal('3200'), 'cuidado', ()),
            ('M2', 'Protector solar FPS 50', '200 ml.', Decimal('14900'), 'cuidado', ()),
            ('M3', 'Curitas x 20', 'Surtidas.', Decimal('2600'), 'cuidado', ()),
        ],
        'promo': None,
    },
    {
        'slug': 'super-grunon',
        'nombre': 'Súper Gruñón',
        'iniciales': 'SG',
        'rating': Decimal('4.3'),
        'cocina': 'Súper',
        'rubro': 'super',
        'tiempo_min': 30,
        'tiempo_max': 40,
        'costo_envio': Decimal('1000'),
        'cierre': '22 h',
        'acento': True,
        'direccion': 'Av. Corrientes 5100',
        'telefono': '11 4800 1007',
        'email': 'contacto@supergrunon.local',
        'categorias': [
            ('almacen', 'Almacén'),
            ('bebidas', 'Bebidas'),
        ],
        'items': [
            ('A1', 'Fideos secos 500 g', 'Tirabuzón.', Decimal('1900'), 'almacen', ('vegetariano', 'vegano', 'sin_lactosa')),
            ('A2', 'Yerba 1 kg', 'Con palo, como debe ser.', Decimal('5600'), 'almacen',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
            ('A3', 'Dulce de leche 400 g', 'Repostero.', Decimal('3400'), 'almacen', ('vegetariano', 'sin_tacc')),
            ('B1', 'Agua mineral 2 L', 'Sin gas.', Decimal('1800'), 'bebidas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ],
        'promo': {'codigo': 'GRUNON0', 'tipo': 'envio_gratis', 'minimo': Decimal('15000'), 'badge': 'Envío $0'},
    },
    {
        'slug': 'kiosco-rabioso',
        'nombre': 'Kiosco Rabioso',
        'iniciales': 'KR',
        'rating': Decimal('4.6'),
        'cocina': 'Bebidas',
        'rubro': 'bebidas',
        'tiempo_min': 10,
        'tiempo_max': 20,
        'costo_envio': Decimal('600'),
        'cierre': '03 h',
        'acento': False,
        'direccion': 'Av. Corrientes 5100',
        'telefono': '11 4800 1008',
        'email': 'contacto@kioscorabioso.local',
        'categorias': [
            ('bebidas', 'Bebidas'),
            ('golosinas', 'Golosinas'),
        ],
        'items': [
            ('K1', 'Energizante 473 ml', 'Para seguir enojado hasta tarde.', Decimal('2900'), 'bebidas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
            ('K2', 'Gaseosa 1,5 L', 'Cola.', Decimal('3300'), 'bebidas', ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
            ('K3', 'Alfajor triple', 'Chocolate negro.', Decimal('1500'), 'golosinas', ('vegetariano',)),
            ('K4', 'Papas fritas 150 g', 'Clásicas.', Decimal('2700'), 'golosinas',
             ('vegetariano', 'vegano', 'sin_tacc', 'sin_lactosa')),
        ],
        'promo': None,
    },
]


class Command(BaseCommand):
    help = 'Carga rubros, comercios, productos, cupones, usuarios y pedidos de demostración en la BD.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra los datos demo antes de recrearlos.')

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            Pedido.objects.all().delete()
            Favorito.objects.all().delete()
            Comercio.objects.all().delete()
            Rubro.objects.all().delete()
            Cupon.objects.all().delete()
            User.objects.filter(email__in=EMAILS_DEMO).delete()
            User.objects.filter(role=User.Role.COMERCIO).delete()

        if Comercio.objects.exists() and User.objects.filter(email='thiago@mail.com').exists():
            self.stdout.write(self.style.WARNING('Los datos demo ya existen. Usá --reset para recrearlos.'))
            return

        # 1. Rubros
        rubros_lista = [
            ('hamburguesas', 'Hamburguesas'),
            ('pizza', 'Pizza'),
            ('sushi', 'Sushi'),
            ('empanadas', 'Empanadas'),
            ('helado', 'Helado'),
            ('farmacia', 'Farmacia'),
            ('super', 'Súper'),
            ('bebidas', 'Bebidas'),
        ]
        rubros_map = {}
        for idx, (slug, nombre) in enumerate(rubros_lista, start=1):
            rubro_obj, _ = Rubro.objects.get_or_create(slug=slug, defaults={'nombre': nombre, 'orden': idx})
            rubros_map[slug] = rubro_obj

        # 2. Comercios, categorías, productos y promociones
        for data in CATALOGO_INICIAL:
            dueno, _ = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'username': data['slug'],
                    'first_name': data['nombre'],
                    'role': User.Role.COMERCIO,
                    'telefono': data['telefono'],
                },
            )
            dueno.set_password(PASSWORD)
            dueno.save()

            comercio, _ = Comercio.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'usuario': dueno,
                    'rubro': rubros_map[data['rubro']],
                    'nombre': data['nombre'],
                    'iniciales': data['iniciales'],
                    'rating': data['rating'],
                    'cocina': data['cocina'],
                    'tiempo_min': data['tiempo_min'],
                    'tiempo_max': data['tiempo_max'],
                    'costo_envio': data['costo_envio'],
                    'cierre': data['cierre'],
                    'direccion': data['direccion'],
                    'telefono': data['telefono'],
                    'email': data['email'],
                    'acento': data['acento'],
                    'activo': True,
                },
            )

            categorias_map = {}
            for orden_cat, (cat_slug, cat_nombre) in enumerate(data['categorias'], start=1):
                cat_obj, _ = CategoriaMenu.objects.get_or_create(
                    comercio=comercio,
                    slug=cat_slug,
                    defaults={'nombre': cat_nombre, 'orden': orden_cat},
                )
                categorias_map[cat_slug] = cat_obj

            productos_map = {}
            for orden_prod, (cod, nom, desc, precio, cat_slug, etiquetas) in enumerate(data['items'], start=1):
                prod_obj, _ = Producto.objects.get_or_create(
                    comercio=comercio,
                    codigo=cod,
                    defaults={
                        'categoria': categorias_map[cat_slug],
                        'nombre': nom,
                        'descripcion': desc,
                        'precio': precio,
                        'orden': orden_prod,
                        'sin_tacc': 'sin_tacc' in etiquetas,
                        'vegetariano': 'vegetariano' in etiquetas,
                        'vegano': 'vegano' in etiquetas,
                        'sin_lactosa': 'sin_lactosa' in etiquetas,
                    },
                )
                productos_map[cod] = prod_obj

            promo_data = data.get('promo')
            if promo_data:
                PromocionComercio.objects.get_or_create(
                    codigo=promo_data['codigo'],
                    defaults={
                        'comercio': comercio,
                        'tipo': promo_data['tipo'],
                        'producto': productos_map.get(promo_data.get('item_codigo')),
                        'porcentaje': promo_data.get('porcentaje', 0),
                        'minimo': promo_data.get('minimo', Decimal('0')),
                        'badge': promo_data.get('badge', ''),
                        'activa': True,
                    },
                )

        # 3. Cupones y tarjetas del home
        hoy = timezone.localdate()
        en_dos_semanas = hoy + timedelta(days=14)
        Cupon.objects.get_or_create(
            codigo='FURIA2X1',
            defaults={
                'tipo': Cupon.Tipo.PORCENTAJE,
                'porcentaje': 0,
                'descripcion': 'En la Doble Furia de Furia Burger. Se aplica sola en el carrito.',
                'destacado_home': True,
                'titulo_home': '2x1',
                'subtitulo_home': 'Burgers dobles',
                'vence_texto': f'Vence {en_dos_semanas:%d/%m}',
                'activo': False,  # Se aplica automáticamente vía PromocionComercio
            },
        )
        Cupon.objects.get_or_create(
            codigo='ENOJADO40',
            defaults={
                'tipo': Cupon.Tipo.PORCENTAJE,
                'porcentaje': 40,
                'tope': Decimal('5000'),
                'solo_primera_compra': True,
                'descripcion': 'Tope de descuento de $5.000. Una vez por cuenta.',
                'destacado_home': True,
                'titulo_home': '-40%',
                'subtitulo_home': 'Tu primera compra',
                'vence_texto': 'Vence fin de mes',
                'activo': True,
            },
        )
        Cupon.objects.get_or_create(
            codigo='SINENVIO',
            defaults={
                'tipo': Cupon.Tipo.ENVIO_GRATIS,
                'minimo': Decimal('15000'),
                'descripcion': 'En pedidos mayores a $15.000 en tu zona.',
                'destacado_home': True,
                'titulo_home': '$0',
                'subtitulo_home': 'Envío gratis',
                'vence_texto': 'Hoy hasta 23 h',
                'activo': True,
            },
        )

        # 4. Métodos de pago
        for nombre, tipo in (('Tarjeta', 'Tarjeta'), ('Billetera virtual', 'MercadoPago'), ('Efectivo', 'Efectivo')):
            MetodoPago.objects.get_or_create(tipo=tipo, defaults={'nombre': nombre})

        # 5. Usuarios demo
        thiago = User.objects.create_user(
            'thiago@mail.com', 'thiago', PASSWORD, first_name='Thiago', last_name='González',
            telefono='11 5555 5555')
        cli = Cliente.objects.create(usuario=thiago, tono=Cliente.Tono.FURIOSO, sin_tacc=True)
        Cliente.objects.filter(pk=cli.pk).update(fecha_registro=date(2026, 3, 2))
        casa = Direccion.objects.create(
            cliente=cli, alias='Casa', calle='Av. Corrientes', numero='1234', piso_depto='5° B',
            localidad='CABA', codigo_postal='C1043', referencia='Timbre roto, llamar al llegar', principal=True)
        facu = Direccion.objects.create(
            cliente=cli, alias='Facultad', calle='Av. Medrano', numero='951',
            localidad='CABA', codigo_postal='C1179', referencia='Entrada principal')

        martin = User.objects.create_user(
            'martin@mail.com', 'martin', PASSWORD, first_name='Martín', last_name='Rodríguez',
            telefono='11 4444 4444', role=User.Role.REPARTIDOR)
        rep = Repartidor.objects.create(usuario=martin, vehiculo='Moto', patente='AB 123 CD', disponibilidad=True)

        lucia = User.objects.create_user(
            'lucia@mail.com', 'lucia', PASSWORD, first_name='Lucía', last_name='Pérez', telefono='11 3333 3333')
        cli2 = Cliente.objects.create(usuario=lucia)
        dir_lucia = [
            Direccion.objects.create(cliente=cli2, alias='Casa', calle='Gurruchaga', numero='1500',
                                     localidad='CABA', codigo_postal='C1414', principal=True),
            Direccion.objects.create(cliente=cli2, alias='Oficina', calle='Thames', numero='2100',
                                     localidad='CABA', codigo_postal='C1425'),
            Direccion.objects.create(cliente=cli2, alias='Mamá', calle='Aguirre', numero='900',
                                     localidad='CABA', codigo_postal='C1414'),
        ]

        tarjeta = {'ultimos4': '4521', 'emisor': 'Visa'}
        T, B, E = MetodoPago.Tipo.TARJETA, MetodoPago.Tipo.BILLETERA, MetodoPago.Tipo.EFECTIVO

        # Historial de Thiago
        p = _pedido(cli, casa, 'empanadas-del-infierno', {'X1': 1}, T, timedelta(days=23, hours=8), tarjeta)
        _avanzar(p, Pedido.Estado.ENTREGADO, p.fecha_hora)
        p = _pedido(cli, casa, 'sushi-sin-paciencia', {'S1': 1, 'R1': 1, 'D1': 1}, T, timedelta(days=19, hours=1), tarjeta)
        servicios.cancelar_pedido(p)
        p = _pedido(cli, facu, 'pizza-violenta', {'Z1': 1, 'F1': 2}, E, timedelta(days=15, hours=0, minutes=30))
        _avanzar(p, Pedido.Estado.ENTREGADO, p.fecha_hora)
        Pago.objects.filter(pedido=p).update(estado_pago=Pago.Estado.APROBADO)

        # Entregas de hoy de Martín
        for i, (slug, cantidades) in enumerate([
            ('kiosco-rabioso', {'K1': 2, 'K3': 3}), ('pizza-violenta', {'Z2': 1}),
            ('helado-hirviendo', {'H2': 1}), ('empanadas-del-infierno', {'E1': 6}),
            ('furia-burger', {'C1': 1}), ('farmacia-ya', {'M1': 1}),
        ]):
            hecho = _pedido(cli2, dir_lucia[i % 3], slug, cantidades, T, timedelta(hours=7 - i), tarjeta)
            _avanzar(hecho, Pedido.Estado.ENTREGADO, hecho.fecha_hora)
            Entrega.objects.filter(pedido=hecho).update(
                repartidor=rep, estado_entrega=Entrega.Estado.ENTREGADO,
                fecha_asignacion=hecho.fecha_hora, fecha_entrega=hecho.entregado_en)

        # Pedido activo en camino
        activo = _pedido(cli, casa, 'furia-burger', {'B1': 2, 'P1': 1, 'D1': 1}, T, timedelta(minutes=16), tarjeta)
        _avanzar(activo, Pedido.Estado.EN_CAMINO, activo.fecha_hora, pasos_min=(2, 13, 1))
        Entrega.objects.filter(pedido=activo).update(
            repartidor=rep, estado_entrega=Entrega.Estado.EN_CAMINO, fecha_asignacion=activo.fecha_hora)

        # Pedidos disponibles para repartidores
        _pedido(cli2, dir_lucia[0], 'pizza-violenta', {'Z1': 1, 'D1': 1}, T, timedelta(minutes=8), tarjeta)
        _pedido(cli2, dir_lucia[1], 'empanadas-del-infierno', {'X1': 1}, E, timedelta(minutes=3))
        kiosco = _pedido(cli2, dir_lucia[2], 'kiosco-rabioso', {'K1': 1, 'K2': 1, 'K3': 1, 'K4': 1}, B,
                         timedelta(minutes=1))
        Pago.objects.filter(pedido=kiosco).update(estado_pago=Pago.Estado.APROBADO)

        # Favoritos de Thiago usando claves foráneas reales
        for slug, codigo in (('furia-burger', ''), ('empanadas-del-infierno', ''), ('furia-burger', 'B1'), ('pizza-violenta', 'Z1')):
            com = Comercio.objects.get(slug=slug)
            prod = com.item(codigo) if codigo else None
            Favorito.objects.create(usuario=thiago, comercio=com, producto=prod)

        self.stdout.write(self.style.SUCCESS(
            f'Base de datos poblada con éxito. Ingresá como thiago@mail.com o martin@mail.com (contraseña: {PASSWORD}). '
            f'Pedido en camino: #{activo.id}.'))