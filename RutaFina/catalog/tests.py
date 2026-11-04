from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalog import restaurantes
from catalog.templatetags.catalog_extras import pesos


class PesosFilterTests(TestCase):
    def test_formato_argentino(self):
        self.assertEqual(pesos(Decimal('19600')), '$ 19.600')
        self.assertEqual(pesos(900), '$ 900')
        self.assertEqual(pesos(Decimal('1250.5')), '$ 1.250,50')
        self.assertEqual(pesos(0), '$ 0')
        self.assertEqual(pesos(Decimal('-9800')), '-$ 9.800')


class BuscarEnCartaTests(TestCase):
    def setUp(self):
        self.furia = restaurantes.obtener('furia-burger')

    def test_busqueda_de_la_captura_da_6_resultados(self):
        codigos = [i.codigo for i in self.furia.buscar('burger doble')]
        self.assertEqual(codigos, ['B1', 'B2', 'B3', 'B4', 'C1', 'C2'])

    def test_ignora_tildes_y_mayusculas(self):
        self.assertEqual([i.codigo for i in self.furia.buscar('VOLCAN')], ['B3'])

    def test_filtra_por_categoria_y_texto(self):
        self.assertEqual([i.codigo for i in self.furia.buscar('', 'papas')], ['P1'])
        self.assertEqual([i.codigo for i in self.furia.buscar('doble', 'combos')], ['C1', 'C2'])

    def test_los_codigos_son_unicos_dentro_de_cada_restaurante(self):
        for restaurante in restaurantes.todos():
            codigos = [i.codigo for i in restaurante.items]
            self.assertEqual(len(codigos), len(set(codigos)), restaurante.slug)
            slugs = {c.slug for c in restaurante.categorias}
            self.assertTrue(all(i.categoria in slugs for i in restaurante.items), restaurante.slug)


class PaginaRestauranteTests(TestCase):
    url = reverse('detalle_restaurante', args=['furia-burger'])

    def test_arranca_en_la_primera_pestana(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Doble Furia')
        self.assertNotContains(respuesta, 'Papas Rabiosas')
        self.assertContains(respuesta, 'rest-tab--activa', count=1)

    def test_busqueda_muestra_cantidad_y_texto(self):
        respuesta = self.client.get(self.url, {'q': 'burger doble'})
        self.assertContains(respuesta, '6 resultados')
        self.assertContains(respuesta, 'Combo Bronca x2')
        self.assertNotContains(respuesta, 'rest-tab--activa')  # con búsqueda no hay pestaña activa

    def test_busqueda_se_escapa(self):
        respuesta = self.client.get(self.url, {'q': '<script>alert(1)</script>'})
        self.assertNotContains(respuesta, '<script>alert(1)</script>')
        self.assertContains(respuesta, 'No encontramos nada')

    def test_categoria_invalida_cae_a_la_primera(self):
        respuesta = self.client.get(self.url, {'categoria': 'inventada'})
        self.assertContains(respuesta, 'Doble Furia')

    def test_carrito_vacio(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'Todavía no agregaste nada')
        self.assertContains(respuesta, 'Tu carrito')

    def test_restaurante_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('detalle_restaurante', args=['nada'])).status_code, 404)

    def test_home_lista_los_restaurantes(self):
        respuesta = self.client.get(reverse('home'))
        self.assertContains(respuesta, 'Furia Burger')
        self.assertContains(respuesta, self.url)

    def test_el_sitio_usa_el_sistema_de_diseno_rabia(self):
        respuesta = self.client.get(reverse('home'))
        self.assertContains(respuesta, 'rabia/rabia.css')
        self.assertNotContains(respuesta, 'bootstrap')


class HomeYBusquedaTests(TestCase):
    def test_home_muestra_los_ocho_comercios_y_las_promos(self):
        respuesta = self.client.get(reverse('home'))
        for r in restaurantes.todos():
            self.assertContains(respuesta, r.nombre)
        for codigo in ('FURIA2X1', 'ENOJADO40', 'SINENVIO'):
            self.assertContains(respuesta, codigo)

    def test_filtro_por_categoria(self):
        respuesta = self.client.get(reverse('home'), {'categoria': 'pizza'})
        self.assertContains(respuesta, reverse('detalle_restaurante', args=['pizza-violenta']))
        self.assertNotContains(respuesta, reverse('detalle_restaurante', args=['furia-burger']))

    def test_ordenar_por_rapidos_y_por_puntaje(self):
        rapidos = restaurantes.todos(orden='rapidos')
        self.assertEqual(rapidos[0].slug, 'kiosco-rabioso')  # 10-20 min
        puntuados = restaurantes.todos(orden='puntuados')
        self.assertEqual(puntuados[0].slug, 'empanadas-del-infierno')  # 4.9

    def test_busqueda_de_un_solo_comercio_redirige_a_su_carta(self):
        respuesta = self.client.get(reverse('buscar'), {'q': 'burger doble'})
        self.assertRedirects(respuesta, reverse('detalle_restaurante', args=['furia-burger']) + '?q=burger+doble')

    def test_busqueda_con_varios_comercios_lista_resultados(self):
        respuesta = self.client.get(reverse('buscar'), {'q': 'gaseosa'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Furia Burger')
        self.assertContains(respuesta, 'Kiosco Rabioso')

    def test_busqueda_vacia_vuelve_al_home(self):
        self.assertRedirects(self.client.get(reverse('buscar'), {'q': ' '}), reverse('home'))
