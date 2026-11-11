"""
Manda por email las promos vigentes a los clientes que activaron
"Recibir promos por email" en Mi cuenta > Preferencias.

    python manage.py enviar_promos            # manda los mails (en desarrollo salen por consola)
    python manage.py enviar_promos --dry-run  # solo dice a cuántos les llegaría
"""
from django.core.management.base import BaseCommand

from catalog import promos
from orders import avisos


class Command(BaseCommand):
    help = 'Manda las promos vigentes a los clientes que eligieron recibirlas por email.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='No manda nada, solo cuenta los destinatarios.')

    def handle(self, *args, dry_run=False, **options):
        vigentes = promos.vigentes()
        if not vigentes:
            self.stdout.write(self.style.WARNING('No hay promos vigentes. No se mandó nada.'))
            return
        if dry_run:
            cantidad = avisos.clientes_que_reciben_promos().count()
            self.stdout.write(f'Se mandarían {len(vigentes)} promos a {cantidad} cliente{"s" if cantidad != 1 else ""}.')
            return
        enviados = avisos.enviar_promos(vigentes)
        self.stdout.write(self.style.SUCCESS(f'Listo: {enviados} mail{"s" if enviados != 1 else ""} enviado{"s" if enviados != 1 else ""}.'))
