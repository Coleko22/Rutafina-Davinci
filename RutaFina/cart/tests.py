from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from catalog import restaurantes
from catalog.restaurantes import Categoria, ItemMenu, Restaurante

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def agregar(client, codigo, veces=1, slug='furia-burger', **extra):
    for _ in range(veces):
        respuesta = client.post(reverse('carrito_agregar', args=[slug, codigo]), **extra)
    return respuesta


def carrito_de(client):
    """El carrito tal como lo ve la próxima request (lee la sesión del cliente)."""
    from cart.carrito import Carrito
    request = mock.Mock(session=client.session)
    return Carrito(request)


class CarritoTests(TestCase):
    def test_pedido_de_la_captura_da_los_mismos_totales(self):
        # 2 Doble Furia + 1 Papas Rabiosas + 1 Gaseosa, con la promo FURIA2X1
        agregar(self.client, 'B1', 2)
        agregar(self.client, 'P1')
        agregar(self.client, 'D1')

        carrito = carrito_de(self.client)
        self.assertEqual(carrito.cantidad_lineas, 3)
        self.assertEqual(carrito.subtotal, Decimal('28300'))
        self.assertEqual(carrito.envio, Decimal('900'))
        self.assertEqual(carrito.promo.codigo, 'FURIA2X1')
        self.assertEqual(carrito.descuento, Decimal('9800'))
        self.assertEqual(carrito.total, Decimal('19400'))

    def test_promo_2x1_cuenta_de_a_pares(self):
        agregar(self.client, 'B1', 1)
        self.assertIsNone(carrito_de(self.client).promo)
        self.assertEqual(carrito_de(self.client).descuento, 0)

        agregar(self.client, 'B1', 3)  # 4 en total -> 2 gratis
        self.assertEqual(carrito_de(self.client).descuento, Decimal('19600'))

    def test_restar_baja_de_a_uno_y_al_llegar_a_cero_saca_la_linea(self):
        agregar(self.client, 'B2', 2)
        self.client.post(reverse('carrito_restar', args=['B2']))
        self.assertEqual(carrito_de(self.client).lineas[0].cantidad, 1)

        self.client.post(reverse('carrito_restar', args=['B2']))
        self.assertTrue(carrito_de(self.client).vacio)

    def test_eliminar_saca_la_linea_entera(self):
        agregar(self.client, 'B2', 3)
        agregar(self.client, 'P1')
        self.client.post(reverse('carrito_eliminar', args=['B2']))
        codigos = [l.item.codigo for l in carrito_de(self.client).lineas]
        self.assertEqual(codigos, ['P1'])

    def test_carrito_vacio_no_cobra_envio_y_olvida_el_restaurante(self):
        agregar(self.client, 'P1')
        self.client.post(reverse('carrito_eliminar', args=['P1']))
        carrito = carrito_de(self.client)
        self.assertTrue(carrito.vacio)
        self.assertEqual(carrito.envio, 0)
        self.assertEqual(carrito.total, 0)
        self.assertIsNone(carrito.slug)

    def test_tope_de_unidades_por_producto(self):
        from cart.carrito import Carrito
        agregar(self.client, 'D1', Carrito.MAX_POR_ITEM + 5)
        self.assertEqual(carrito_de(self.client).lineas[0].cantidad, Carrito.MAX_POR_ITEM)

    def test_producto_que_ya_no_existe_en_el_catalogo_se_ignora(self):
        agregar(self.client, 'P1')
        sesion = self.client.session
        sesion['carrito']['items']['ZZ9'] = 3
        sesion.save()
        carrito = carrito_de(self.client)
        self.assertEqual([l.item.codigo for l in carrito.lineas], ['P1'])
        self.assertEqual(carrito.subtotal, Decimal('4200'))

    def test_el_carrito_es_de_un_solo_restaurante(self):
        otro = Restaurante(
            slug='otro', nombre='Otro', iniciales='OT', rating=Decimal('4.0'), cocina='Pizzas',
            tiempo_min=10, tiempo_max=20, costo_envio=Decimal('500'), cierre='23 h',
            categorias=(Categoria('pizzas', 'Pizzas'),),
            items=(ItemMenu('Z1', 'Muzza', 'Clásica.', Decimal('7000'), 'pizzas'),),
        )
        with mock.patch.dict(restaurantes.RESTAURANTES, {'otro': otro}):
            agregar(self.client, 'B1', 2)
            agregar(self.client, 'Z1', slug='otro')
            carrito = carrito_de(self.client)
            self.assertEqual(carrito.slug, 'otro')
            self.assertEqual([l.item.codigo for l in carrito.lineas], ['Z1'])
            self.assertEqual(carrito.total, Decimal('7500'))  # 7000 + envío 500, sin promo de Furia


class VistasCarritoTests(TestCase):
    def test_solo_acepta_post(self):
        for nombre, args in [('carrito_agregar', ['furia-burger', 'B1']),
                             ('carrito_restar', ['B1']), ('carrito_eliminar', ['B1'])]:
            self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 405)

    def test_producto_o_restaurante_inexistente_da_404(self):
        self.assertEqual(self.client.post(reverse('carrito_agregar', args=['furia-burger', 'NOPE'])).status_code, 404)
        self.assertEqual(self.client.post(reverse('carrito_agregar', args=['no-existe', 'B1'])).status_code, 404)

    def test_sin_js_redirige_al_next(self):
        destino = reverse('detalle_restaurante', args=['furia-burger']) + '?categoria=combos'
        respuesta = self.client.post(reverse('carrito_agregar', args=['furia-burger', 'C1']), {'next': destino})
        self.assertRedirects(respuesta, destino)

    def test_next_externo_se_ignora(self):
        respuesta = self.client.post(
            reverse('carrito_agregar', args=['furia-burger', 'C1']), {'next': 'https://evil.example.com/'})
        self.assertRedirects(respuesta, reverse('detalle_restaurante', args=['furia-burger']))

    def test_con_fetch_devuelve_solo_el_panel(self):
        respuesta = agregar(self.client, 'B1', 2, **AJAX)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'cart/_carrito.html')
        self.assertTemplateNotUsed(respuesta, 'base.html')
        self.assertContains(respuesta, 'Doble Furia')
        self.assertContains(respuesta, 'Promo FURIA2X1')
        self.assertContains(respuesta, '$ 9.800')

    def test_post_sin_csrf_es_rechazado(self):
        from django.test import Client
        cliente = Client(enforce_csrf_checks=True)
        respuesta = cliente.post(reverse('carrito_agregar', args=['furia-burger', 'B1']))
        self.assertEqual(respuesta.status_code, 403)

    def test_ir_a_pagar_apunta_al_checkout(self):
        agregar(self.client, 'B1')
        pagina = self.client.get(reverse('detalle_restaurante', args=['furia-burger']))
        self.assertContains(pagina, f'href="{reverse("checkout")}"')
