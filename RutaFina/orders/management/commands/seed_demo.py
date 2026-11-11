"""
Carga datos de demostración que reproducen los mockups:

    python manage.py seed_demo          # crea lo que falte
    python manage.py seed_demo --reset  # borra los usuarios demo y los vuelve a crear

Usuarios (contraseña de todos: rabia1234):
    thiago@mail.com   cliente, con direcciones, historial, favoritos y un pedido en camino
    martin@mail.com   repartidor, con el pedido de Thiago activo y entregas del día
    lucia@mail.com    cliente con pedidos esperando repartidor (los "Pedidos disponibles")
"""
from datetime import date, timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cart.carrito import Carrito
from catalog import restaurantes
from orders import servicios
from orders.models import Entrega, MetodoPago, Pago, Pedido
from users.models import Cliente, Direccion, Favorito, Repartidor, User

PASSWORD = 'rabia1234'
EMAILS = ('thiago@mail.com', 'martin@mail.com', 'lucia@mail.com')


class _Sesion(dict):
    """Sesión en memoria para armar carritos fuera de una request."""
    modified = False


def _pedido(cliente, direccion, slug, cantidades, metodo, hace, tarjeta=None):
    """Crea un pedido con el mismo servicio que usa el checkout y le cambia la fecha."""
    restaurante = restaurantes.obtener(slug)
    carrito = Carrito(SimpleNamespace(session=_Sesion(), user=cliente.usuario))
    carrito.cargar(restaurante, cantidades)
    pedido = servicios.crear_pedido(cliente, carrito, direccion, metodo, tarjeta)
    fecha = timezone.now() - hace
    Pedido.objects.filter(pk=pedido.pk).update(fecha_hora=fecha, eta=fecha + timedelta(minutes=restaurante.tiempo_max))
    pedido.refresh_from_db()
    return pedido


def _avanzar(pedido, hasta, inicio, pasos_min=(2, 15, 6, 12)):
    """Lleva el pedido hasta el estado `hasta` poniendo horas creíbles a cada paso."""
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


class Command(BaseCommand):
    help = 'Carga usuarios, direcciones, pedidos y favoritos de demostración (ver docstring).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra los usuarios demo antes de crearlos.')

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            User.objects.filter(email__in=EMAILS).delete()
        if User.objects.filter(email='thiago@mail.com').exists():
            self.stdout.write(self.style.WARNING('Los datos demo ya existen. Usá --reset para recrearlos.'))
            return

        for nombre, tipo in (('Tarjeta', 'Tarjeta'), ('Billetera virtual', 'MercadoPago'), ('Efectivo', 'Efectivo')):
            MetodoPago.objects.get_or_create(tipo=tipo, defaults={'nombre': nombre})

        # --- Thiago (cliente de los mockups) ---
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

        # --- Martín (repartidor) ---
        martin = User.objects.create_user(
            'martin@mail.com', 'martin', PASSWORD, first_name='Martín', last_name='Rodríguez',
            telefono='11 4444 4444', role=User.Role.REPARTIDOR)
        rep = Repartidor.objects.create(usuario=martin, vehiculo='Moto', patente='AB 123 CD', disponibilidad=True)

        # --- Lucía (otra clienta, genera pedidos disponibles para el repartidor) ---
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

        # Historial de Thiago (del más viejo al más nuevo)
        p = _pedido(cli, casa, 'empanadas-del-infierno', {'X1': 1}, T, timedelta(days=23, hours=8), tarjeta)
        _avanzar(p, Pedido.Estado.ENTREGADO, p.fecha_hora)
        p = _pedido(cli, casa, 'sushi-sin-paciencia', {'S1': 1, 'R1': 1, 'D1': 1}, T, timedelta(days=19, hours=1), tarjeta)
        servicios.cancelar_pedido(p)
        p = _pedido(cli, facu, 'pizza-violenta', {'Z1': 1, 'F1': 2}, E, timedelta(days=15, hours=0, minutes=30))
        _avanzar(p, Pedido.Estado.ENTREGADO, p.fecha_hora)
        Pago.objects.filter(pedido=p).update(estado_pago=Pago.Estado.APROBADO)

        # Entregas de hoy de Martín (para las tarjetas Hoy / Ganado / Km)
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

        # El pedido en curso de los mockups 05 y 08: Furia Burger, 2 Doble Furia + papas + gaseosa
        activo = _pedido(cli, casa, 'furia-burger', {'B1': 2, 'P1': 1, 'D1': 1}, T, timedelta(minutes=16), tarjeta)
        _avanzar(activo, Pedido.Estado.EN_CAMINO, activo.fecha_hora, pasos_min=(2, 13, 1))
        Entrega.objects.filter(pedido=activo).update(
            repartidor=rep, estado_entrega=Entrega.Estado.EN_CAMINO, fecha_asignacion=activo.fecha_hora)

        # Pedidos disponibles para tomar
        _pedido(cli2, dir_lucia[0], 'pizza-violenta', {'Z1': 1, 'D1': 1}, T, timedelta(minutes=8), tarjeta)
        _pedido(cli2, dir_lucia[1], 'empanadas-del-infierno', {'X1': 1}, E, timedelta(minutes=3))
        kiosco = _pedido(cli2, dir_lucia[2], 'kiosco-rabioso', {'K1': 1, 'K2': 1, 'K3': 1, 'K4': 1}, B,
                         timedelta(minutes=1))
        # Pagado con billetera: solo se ofrece al repartidor una vez aprobado el pago
        Pago.objects.filter(pedido=kiosco).update(estado_pago=Pago.Estado.APROBADO)

        # Favoritos de Thiago
        for slug, codigo in (('furia-burger', ''), ('empanadas-del-infierno', ''), ('furia-burger', 'B1'), ('pizza-violenta', 'Z1')):
            Favorito.objects.create(usuario=thiago, restaurante_slug=slug, item_codigo=codigo)

        self.stdout.write(self.style.SUCCESS(
            f'Listo. Ingresá como thiago@mail.com o martin@mail.com (contraseña: {PASSWORD}). '
            f'Pedido en camino: #{activo.id}.'))
