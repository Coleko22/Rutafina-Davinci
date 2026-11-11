"""
Avisos por email al cliente, según lo que eligió en Mi cuenta > Preferencias
(users.Cliente: avisar_pedido_sale y recibir_promos).

En desarrollo los mails salen por consola (settings.MAILERS); en los tests
Django los guarda en django.core.mail.outbox.
"""
from django.core.mail import send_mail, send_mass_mail
from django.urls import reverse
from django.utils import timezone

from catalog.templatetags.catalog_extras import pesos
from users import tono as tonos
from users.models import Cliente

PIE = 'Podés dejar de recibir estos avisos desde Mi cuenta > Preferencias ({url}).'


def _pie():
    return PIE.format(url=reverse('perfil'))


def avisar_pedido_en_camino(pedido):
    """
    Mail de "tu pedido ya salió" cuando el repartidor marca En camino.
    Devuelve True si se mandó (el cliente lo tiene activado y tiene email).
    """
    cliente = pedido.cliente
    usuario = cliente.usuario
    if not cliente.avisar_pedido_sale or not usuario.email:
        return False

    lineas = [
        f'Hola {usuario.first_name or usuario.username},',
        '',
        f'Tu pedido #{pedido.id} de {pedido.restaurante_nombre} ya salió para {pedido.direccion_texto}.',
    ]
    repartidor = pedido.repartidor
    if repartidor:
        lineas.append(f'Lo lleva {repartidor.nombre_corto} ({repartidor.vehiculo}).')
    if pedido.eta:
        lineas.append(f'Llega aprox. {timezone.localtime(pedido.eta):%H:%M} h.')
    pago = getattr(pedido, 'pago', None)
    if pago is not None and pago.estado_pago == pago.Estado.A_COBRAR:
        lineas.append(f'Tené listo el efectivo: {pesos(pedido.total)}.')
    lineas += ['', f"Seguilo acá: {reverse('pedido_detalle', args=[pedido.id])}", '', _pie()]

    asunto = f"{tonos.textos(cliente.tono)['mail_sale']} (pedido #{pedido.id})"
    send_mail(asunto, '\n'.join(lineas), None, [usuario.email], fail_silently=True)
    return True


def clientes_que_reciben_promos():
    return (Cliente.objects
            .filter(recibir_promos=True, usuario__is_active=True)
            .exclude(usuario__email='')
            .select_related('usuario'))


def mails_de_promos(promos_vigentes, clientes):
    """Arma un mail por cliente con las promos vigentes (formato de send_mass_mail)."""
    cuerpo_promos = '\n'.join(
        f'- {p.titulo} · {p.subtitulo}: {p.descripcion} Código {p.codigo}. {p.vence}.'
        for p in promos_vigentes
    )
    mensajes = []
    for cliente in clientes:
        usuario = cliente.usuario
        asunto = tonos.textos(cliente.tono)['mail_promos']
        cuerpo = '\n'.join([
            f'Hola {usuario.first_name or usuario.username},', '',
            'Estas son las promos vigentes en RABIA:', '', cuerpo_promos, '', _pie(),
        ])
        mensajes.append((asunto, cuerpo, None, [usuario.email]))
    return mensajes


def enviar_promos(promos_vigentes):
    """Manda las promos a quienes marcaron "Recibir promos por email". Devuelve cuántos mails salieron."""
    if not promos_vigentes:
        return 0
    mensajes = mails_de_promos(promos_vigentes, clientes_que_reciben_promos())
    return send_mass_mail(mensajes, fail_silently=False) if mensajes else 0
