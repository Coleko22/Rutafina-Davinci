from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Direccion, Favorito, User


def crear_usuario(email='thiago@mail.com', **extra):
    user = User.objects.create_user(email, email.split('@')[0], 'clave-segura-123',
                                    first_name='Thiago', last_name='González', **extra)
    Cliente.objects.create(usuario=user)
    return user


class RegistroYLoginTests(TestCase):
    datos = {
        'first_name': 'Ana', 'last_name': 'Paz', 'email': 'Ana@Mail.com',
        'telefono': '11 5555 5555', 'password': 'una-clave-larga-1', 'acepto': 'on',
    }

    def test_login_y_registro_en_la_misma_pantalla(self):
        respuesta = self.client.get(reverse('login'))
        self.assertContains(respuesta, 'Ingresar')
        self.assertContains(respuesta, 'Registrate')

    def test_registro_crea_usuario_cliente_y_loguea(self):
        respuesta = self.client.post(reverse('registro'), self.datos)
        self.assertRedirects(respuesta, reverse('home'))
        user = User.objects.get(email='ana@mail.com')
        self.assertEqual(user.username, 'ana')
        self.assertTrue(Cliente.objects.filter(usuario=user).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_registro_exige_aceptar_terminos_y_email_unico(self):
        crear_usuario('ana@mail.com')
        datos = dict(self.datos)
        datos.pop('acepto')
        respuesta = self.client.post(reverse('registro'), datos)
        self.assertContains(respuesta, 'Tenés que aceptar los términos')
        self.assertContains(respuesta, 'Ya hay una cuenta con ese email')

    def test_login_incorrecto_muestra_el_error(self):
        crear_usuario()
        respuesta = self.client.post(reverse('login'), {'username': 'thiago@mail.com', 'password': 'mal'})
        self.assertContains(respuesta, 'Email o contraseña incorrectos')

    def test_login_sin_recordarme_vence_al_cerrar_el_navegador(self):
        crear_usuario()
        self.client.post(reverse('login'), {'username': 'thiago@mail.com', 'password': 'clave-segura-123'})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_respeta_next_seguro(self):
        crear_usuario()
        destino = reverse('historial')
        respuesta = self.client.post(reverse('login') + f'?next={destino}',
                                     {'username': 'thiago@mail.com', 'password': 'clave-segura-123', 'recordarme': 'on'})
        self.assertRedirects(respuesta, destino)

    def test_repartidor_entra_a_su_panel(self):
        User.objects.create_user('martin@mail.com', 'martin', 'clave-segura-123', role=User.Role.REPARTIDOR)
        respuesta = self.client.post(reverse('login'), {'username': 'martin@mail.com', 'password': 'clave-segura-123'})
        self.assertRedirects(respuesta, reverse('panel_repartidor'))


class PerfilTests(TestCase):
    def setUp(self):
        self.user = crear_usuario()
        self.client.force_login(self.user)

    def test_guardar_datos_y_preferencias(self):
        respuesta = self.client.post(reverse('perfil'), {
            'datos-first_name': 'Thiago', 'datos-last_name': 'G.', 'datos-email': 'thiago@mail.com',
            'datos-telefono': '11 1111 1111',
            'pref-tono': 'TRANQUI', 'pref-vegano': 'on', 'pref-modo_oscuro': 'on',
        })
        self.assertRedirects(respuesta, reverse('perfil'))
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertEqual(cliente.tono, 'TRANQUI')
        self.assertTrue(cliente.vegano and cliente.modo_oscuro)
        self.assertFalse(cliente.avisar_pedido_sale)

    def test_tono_y_modo_oscuro_cambian_el_sitio(self):
        Cliente.objects.filter(usuario=self.user).update(tono='TRANQUI', modo_oscuro=True)
        respuesta = self.client.get(reverse('home'))
        self.assertContains(respuesta, 'data-theme="dark"')
        self.assertContains(respuesta, 'Te lo llevamos.')
        self.assertNotContains(respuesta, 'Nosotros, bronca.')


class DireccionesYFavoritosTests(TestCase):
    def setUp(self):
        self.user = crear_usuario()
        self.client.force_login(self.user)
        self.datos = {'calle': 'Av. Corrientes', 'numero': '1234', 'piso_depto': '5° B',
                      'codigo_postal': 'C1043', 'localidad': 'CABA', 'alias': 'Casa', 'referencia': ''}

    def test_la_primera_direccion_queda_como_principal(self):
        self.client.post(reverse('agregar_direccion'), self.datos)
        self.client.post(reverse('agregar_direccion'), dict(self.datos, alias='Facu', numero='951'))
        principales = Direccion.objects.filter(principal=True)
        self.assertEqual([d.alias for d in principales], ['Casa'])
        self.assertEqual(principales[0].linea, 'Av. Corrientes 1234, 5° B')

    def test_cambiar_principal_y_eliminar(self):
        self.client.post(reverse('agregar_direccion'), self.datos)
        self.client.post(reverse('agregar_direccion'), dict(self.datos, alias='Facu'))
        facu = Direccion.objects.get(alias='Facu')
        self.client.post(reverse('direccion_principal', args=[facu.id]))
        self.assertEqual(Direccion.objects.get(principal=True).alias, 'Facu')
        # Al borrar la principal, otra pasa a serlo
        self.client.post(reverse('eliminar_direccion', args=[facu.id]))
        self.assertEqual(Direccion.objects.get(principal=True).alias, 'Casa')

    def test_eliminar_direccion_no_acepta_get(self):
        self.client.post(reverse('agregar_direccion'), self.datos)
        d = Direccion.objects.get()
        self.assertEqual(self.client.get(reverse('eliminar_direccion', args=[d.id])).status_code, 405)

    def test_no_se_puede_tocar_la_direccion_de_otro(self):
        otro = crear_usuario('otro@mail.com')
        ajena = Direccion.objects.create(cliente=otro.perfil_cliente, calle='X', numero='1', codigo_postal='1')
        self.assertEqual(self.client.post(reverse('eliminar_direccion', args=[ajena.id])).status_code, 404)

    def test_favorito_se_marca_y_desmarca(self):
        url = reverse('favorito_toggle')
        self.client.post(url, {'slug': 'furia-burger', 'codigo': 'B1'})
        self.assertTrue(Favorito.objects.filter(item_codigo='B1').exists())
        pagina = self.client.get(reverse('detalle_restaurante', args=['furia-burger']))
        self.assertContains(pagina, 'Quitar Doble Furia de favoritos')
        self.client.post(url, {'slug': 'furia-burger', 'codigo': 'B1'})
        self.assertFalse(Favorito.objects.exists())

    def test_favorito_de_algo_inexistente_da_404(self):
        self.assertEqual(self.client.post(reverse('favorito_toggle'), {'slug': 'nada'}).status_code, 404)
