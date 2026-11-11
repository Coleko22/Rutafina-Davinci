from decimal import Decimal
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from users.models import Cliente, Direccion, Repartidor, User
from .models import Entrega, Pago, Pedido

TARJETA_OK = {'numero_tarjeta': '4111 1111 1111 1111', 'titular': 'THIAGO GONZALEZ', 'vencimiento': '12/39', 'cvv': '123'}


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('thiago@mail.com', 'thiago', 'clave-segura-123',
                                             first_name='Thiago', last_name='González', telefono='11 5555 5555')
        self.cliente = Cliente.objects.create(usuario=self.user)
        self.casa = Direccion.objects.create(cliente=self.cliente, alias='Casa', calle='Av. Corrientes', numero='1234',
                                             piso_depto='5° B', codigo_postal='C1043', principal=True)
        self.client.force_login(self.user)

    def llenar_carrito(self):
        """El carrito del mockup: 2 Doble Furia + Papas + Gaseosa = $19.400 con la promo."""
        for codigo, veces in (('B1', 2), ('P1', 1), ('D1', 1)):
            for _ in range(veces):
                self.client.post(reverse('carrito_agregar', args=['furia-burger', codigo]))

    def confirmar(self, metodo='Tarjeta', **extra):
        datos = {'direccion': self.casa.id, 'metodo': metodo}
        if metodo == 'Tarjeta':
            datos.update(TARJETA_OK)
        datos.update(extra)
        return self.client.post(reverse('checkout'), datos)


class CheckoutTests(Base):
    def test_checkout_con_carrito_vacio_vuelve_al_home(self):
        self.assertRedirects(self.client.get(reverse('checkout')), reverse('home') + '#comercios',
                             fetch_redirect_response=False)

    def test_checkout_pide_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('checkout'))
        self.assertTrue(respuesta.url.startswith(reverse('login')))

    def test_pantalla_de_checkout_muestra_resumen_y_direcciones(self):
        self.llenar_carrito()
        respuesta = self.client.get(reverse('checkout'))
        self.assertContains(respuesta, 'Av. Corrientes 1234, 5° B')
        self.assertContains(respuesta, '$ 19.400')
        self.assertContains(respuesta, 'Confirmar pedido')

    def test_confirmar_con_tarjeta_crea_el_pedido_y_vacia_el_carrito(self):
        self.llenar_carrito()
        respuesta = self.confirmar()
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, reverse('pedido_detalle', args=[pedido.id]))
        self.assertEqual(pedido.total, Decimal('19400'))
        self.assertEqual(pedido.descuento_promo, Decimal('9800'))
        self.assertEqual(pedido.promo_codigo, 'FURIA2X1')
        self.assertEqual(pedido.cantidad_productos, 4)
        self.assertEqual(pedido.direccion_texto, 'Av. Corrientes 1234, 5° B, CABA')
        self.assertEqual(pedido.estado, Pedido.Estado.CONFIRMADO)
        self.assertEqual(pedido.pago.estado_pago, Pago.Estado.APROBADO)
        self.assertEqual(pedido.pago.ultimos4, '1111')
        self.assertEqual(pedido.pago.emisor, 'Visa')
        self.assertIsNotNone(pedido.eta)
        self.assertNotIn('carrito', self.client.session)

    def test_tarjeta_invalida_no_crea_pedido(self):
        self.llenar_carrito()
        respuesta = self.confirmar(numero_tarjeta='4111 1111 1111 1112', vencimiento='01/20', cvv='1')
        self.assertContains(respuesta, 'Ese número de tarjeta no es válido')
        self.assertContains(respuesta, 'La tarjeta está vencida')
        self.assertContains(respuesta, 'Son 3 o 4 números')
        self.assertFalse(Pedido.objects.exists())

    def test_efectivo_no_pide_tarjeta_y_queda_a_cobrar(self):
        self.llenar_carrito()
        self.confirmar('Efectivo')
        self.assertEqual(Pedido.objects.get().pago.estado_pago, Pago.Estado.A_COBRAR)

    def test_billetera_lleva_al_qr_y_se_aprueba_al_volver(self):
        self.llenar_carrito()
        respuesta = self.confirmar('MercadoPago')
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, reverse('pago_billetera', args=[pedido.id]), fetch_redirect_response=False)
        self.assertEqual(pedido.pago.estado_pago, Pago.Estado.PENDIENTE)
        self.client.get(reverse('pago_billetera_retorno', args=[pedido.id]), {'status': 'approved'})
        pedido.pago.refresh_from_db()
        self.assertEqual(pedido.pago.estado_pago, Pago.Estado.APROBADO)

    def test_no_se_puede_usar_la_direccion_de_otro(self):
        otro = User.objects.create_user('otro@mail.com', 'otro', 'x')
        ajena = Direccion.objects.create(cliente=Cliente.objects.create(usuario=otro), calle='X', numero='1', codigo_postal='1')
        self.llenar_carrito()
        respuesta = self.confirmar(direccion=ajena.id)
        self.assertContains(respuesta, 'Elegí una dirección válida')
        self.assertFalse(Pedido.objects.exists())


class CuponTests(Base):
    def test_enojado40_solo_en_la_primera_compra(self):
        self.llenar_carrito()
        self.client.post(reverse('carrito_cupon'), {'codigo': 'enojado40'})
        self.confirmar()
        primero = Pedido.objects.get()
        self.assertEqual(primero.cupon_codigo, 'ENOJADO40')
        self.assertEqual(primero.descuento_cupon, Decimal('5000'))  # 40% de 28.300 tiene tope 5.000
        self.assertEqual(primero.total, Decimal('14400'))

        self.llenar_carrito()
        self.client.post(reverse('carrito_cupon'), {'codigo': 'ENOJADO40'})
        self.confirmar()
        segundo = Pedido.objects.latest('id')
        self.assertEqual(segundo.descuento_cupon, 0)
        self.assertEqual(segundo.total, Decimal('19400'))

    def test_sinenvio_desde_15000(self):
        self.client.post(reverse('carrito_agregar', args=['furia-burger', 'P1']))
        self.client.post(reverse('carrito_cupon'), {'codigo': 'SINENVIO'})
        pagina = self.client.get(reverse('checkout'))
        self.assertContains(pagina, 'Este código aplica desde un subtotal de $15.000')

        for _ in range(3):
            self.client.post(reverse('carrito_agregar', args=['furia-burger', 'P1']))  # 4 x 4.200 = 16.800
        self.confirmar()
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.descuento_cupon, Decimal('900'))
        self.assertEqual(pedido.total, Decimal('16800'))

    def test_codigo_inexistente(self):
        self.llenar_carrito()
        respuesta = self.client.post(reverse('carrito_cupon'), {'codigo': 'TRUCHO', 'next': reverse('checkout')}, follow=True)
        self.assertContains(respuesta, 'Ese código no existe')


class SeguimientoTests(Base):
    def setUp(self):
        super().setUp()
        self.llenar_carrito()
        self.confirmar()
        self.pedido = Pedido.objects.get()

    def test_detalle_muestra_estado_y_pago(self):
        respuesta = self.client.get(reverse('pedido_detalle', args=[self.pedido.id]))
        self.assertContains(respuesta, f'Pedido #{self.pedido.id}')
        self.assertContains(respuesta, 'Tarjeta terminada en 1111')
        self.assertContains(respuesta, 'Aprobado')
        self.assertContains(respuesta, 'http-equiv="refresh"')

    def test_no_se_ve_el_pedido_de_otro(self):
        otro = User.objects.create_user('otro@mail.com', 'otro', 'x')
        self.client.force_login(otro)
        self.assertEqual(self.client.get(reverse('pedido_detalle', args=[self.pedido.id])).status_code, 404)

    def test_cancelar_antes_de_que_lo_tomen(self):
        self.client.post(reverse('cancelar_pedido', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.Estado.CANCELADO)
        self.assertEqual(self.pedido.pago.estado_pago, Pago.Estado.CANCELADO)

    def test_historial_y_repetir(self):
        respuesta = self.client.get(reverse('historial'))
        self.assertContains(respuesta, 'Furia Burger')
        self.assertContains(respuesta, '$ 19.400')
        self.client.post(reverse('repetir_pedido', args=[self.pedido.id]))
        self.assertEqual(self.client.session['carrito']['items'], {'B1': 2, 'P1': 1, 'D1': 1})

    def test_pasos_y_mapa(self):
        pasos = self.pedido.pasos()
        self.assertEqual([p['estado'] for p in pasos], ['actual', 'pendiente', 'pendiente', 'pendiente', 'pendiente'])
        self.pedido.cambiar_estado(Pedido.Estado.EN_CAMINO)
        self.assertEqual([p['estado'] for p in self.pedido.pasos()], ['hecho', 'hecho', 'hecho', 'actual', 'pendiente'])
        self.assertIsNotNone(self.pedido.retirado_en)  # se rellenan las horas de pasos salteados
        self.assertEqual(self.pedido.mapa()['hecho'], 550)


class RepartidorTests(Base):
    def setUp(self):
        super().setUp()
        self.llenar_carrito()
        self.confirmar('Efectivo')
        self.pedido = Pedido.objects.get()
        self.martin = User.objects.create_user('martin@mail.com', 'martin', 'x', first_name='Martín',
                                               last_name='Rodríguez', role=User.Role.REPARTIDOR, telefono='11 4444 4444')
        self.rep = Repartidor.objects.create(usuario=self.martin, vehiculo='Moto', patente='AB 123 CD')
        self.client.force_login(self.martin)

    def test_un_cliente_no_entra_al_panel(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('panel_repartidor')).status_code, 404)

    def test_flujo_completo_tomar_retirar_salir_entregar(self):
        panel = self.client.get(reverse('panel_repartidor'))
        self.assertContains(panel, f'#{self.pedido.id} · Furia Burger')

        self.client.post(reverse('repartidor_tomar', args=[self.pedido.id]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.Estado.PREPARACION)
        self.assertEqual(self.pedido.entrega.repartidor, self.rep)
        self.assertFalse(self.pedido.cancelable)

        # El cliente ve al repartidor en el seguimiento
        self.client.force_login(self.user)
        detalle = self.client.get(reverse('pedido_detalle', args=[self.pedido.id]))
        self.assertContains(detalle, 'Martín R. · Moto · AB 123 CD')
        self.client.force_login(self.martin)

        for esperado in (Pedido.Estado.RETIRADO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO):
            self.client.post(reverse('repartidor_avanzar'))
            self.pedido.refresh_from_db()
            self.assertEqual(self.pedido.estado, esperado)

        self.assertEqual(self.pedido.entrega.estado_entrega, Entrega.Estado.ENTREGADO)
        self.assertEqual(self.pedido.pago.estado_pago, Pago.Estado.APROBADO)  # el efectivo se cobró
        panel = self.client.get(reverse('panel_repartidor'))
        self.assertContains(panel, '1 pedido')
        self.assertContains(panel, 'No tenés ningún pedido en curso')

    def test_no_puede_tomar_dos_ni_estando_desconectado(self):
        self.client.post(reverse('repartidor_tomar', args=[self.pedido.id]))
        self.client.force_login(self.user)
        self.llenar_carrito()
        self.confirmar()
        segundo = Pedido.objects.latest('id')
        self.client.force_login(self.martin)
        self.client.post(reverse('repartidor_tomar', args=[segundo.id]))
        segundo.refresh_from_db()
        self.assertFalse(segundo.tiene_repartidor)

        self.rep.disponibilidad = False
        self.rep.save()
        respuesta = self.client.post(reverse('repartidor_tomar', args=[segundo.id]), follow=True)
        self.assertContains(respuesta, 'Ponete en línea')

    def test_otro_repartidor_no_puede_tomar_uno_ya_tomado(self):
        self.client.post(reverse('repartidor_tomar', args=[self.pedido.id]))
        otro = User.objects.create_user('ana@mail.com', 'ana', 'x', role=User.Role.REPARTIDOR)
        self.client.force_login(otro)
        respuesta = self.client.post(reverse('repartidor_tomar', args=[self.pedido.id]), follow=True)
        self.assertContains(respuesta, 'Ese pedido ya no está disponible')
        self.pedido.entrega.refresh_from_db()
        self.assertEqual(self.pedido.entrega.repartidor, self.rep)

    def test_en_linea_se_alterna(self):
        self.client.post(reverse('repartidor_en_linea'))
        self.rep.refresh_from_db()
        self.assertFalse(self.rep.disponibilidad)


    def test_no_se_ofrece_un_pedido_con_billetera_sin_pagar(self):
        self.client.force_login(self.user)
        self.llenar_carrito()
        self.confirmar('MercadoPago')
        billetera = Pedido.objects.latest('id')
        self.client.force_login(self.martin)

        self.assertNotContains(self.client.get(reverse('panel_repartidor')), f'#{billetera.id} · Furia Burger')
        respuesta = self.client.post(reverse('repartidor_tomar', args=[billetera.id]), follow=True)
        self.assertContains(respuesta, 'todavía no está pago')
        billetera.refresh_from_db()
        self.assertFalse(billetera.tiene_repartidor)

        # Cuando Mercado Pago aprueba, ya aparece
        Pago.objects.filter(pedido=billetera).update(estado_pago=Pago.Estado.APROBADO)
        self.assertContains(self.client.get(reverse('panel_repartidor')), f'#{billetera.id} · Furia Burger')

    def _llevar_hasta_en_camino(self):
        self.client.post(reverse('repartidor_tomar', args=[self.pedido.id]))
        self.client.post(reverse('repartidor_avanzar'))  # retirado
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('repartidor_avanzar'))  # en camino

    def test_avisa_por_mail_cuando_el_pedido_sale(self):
        self._llevar_hasta_en_camino()
        self.assertEqual(len(mail.outbox), 1)
        aviso = mail.outbox[0]
        self.assertEqual(aviso.to, ['thiago@mail.com'])
        self.assertIn(f'pedido #{self.pedido.id}', aviso.subject)
        self.assertIn('Martín R.', aviso.body)
        self.assertIn('Tené listo el efectivo', aviso.body)

    def test_no_avisa_si_el_cliente_lo_desactivo(self):
        Cliente.objects.filter(pk=self.cliente.pk).update(avisar_pedido_sale=False)
        self._llevar_hasta_en_camino()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.Estado.EN_CAMINO)
        self.assertEqual(mail.outbox, [])


class EnviarPromosTests(Base):
    def test_solo_a_quienes_eligieron_recibir_promos(self):
        ana = User.objects.create_user('ana@mail.com', 'ana', 'x', first_name='Ana')
        Cliente.objects.create(usuario=ana, recibir_promos=True, tono=Cliente.Tono.TRANQUI)
        salida = StringIO()
        call_command('enviar_promos', stdout=salida)
        self.assertEqual(len(mail.outbox), 1)  # Thiago no las pidió
        self.assertEqual(mail.outbox[0].to, ['ana@mail.com'])
        self.assertEqual(mail.outbox[0].subject, 'Promos de la semana')
        self.assertIn('FURIA2X1', mail.outbox[0].body)
        self.assertIn('1 mail enviado', salida.getvalue())

    def test_dry_run_no_manda_nada(self):
        Cliente.objects.filter(pk=self.cliente.pk).update(recibir_promos=True)
        salida = StringIO()
        call_command('enviar_promos', '--dry-run', stdout=salida)
        self.assertEqual(mail.outbox, [])
        self.assertIn('a 1 cliente', salida.getvalue())
