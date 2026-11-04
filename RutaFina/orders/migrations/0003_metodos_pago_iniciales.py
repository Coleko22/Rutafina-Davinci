from django.db import migrations

# Los tres medios de pago de la pantalla "¿Cómo pagás?". El tipo coincide con
# MetodoPago.Tipo y con lo que ya usaba templates/orders/metodos_pago.html.
METODOS = [
    ('Tarjeta', 'Tarjeta'),
    ('Billetera virtual', 'MercadoPago'),
    ('Efectivo', 'Efectivo'),
]


def crear(apps, schema_editor):
    MetodoPago = apps.get_model('orders', 'MetodoPago')
    for nombre, tipo in METODOS:
        MetodoPago.objects.get_or_create(tipo=tipo, defaults={'nombre': nombre, 'disponible': True})


class Migration(migrations.Migration):
    dependencies = [('orders', '0002_pedido_seguimiento_y_snapshot')]
    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
