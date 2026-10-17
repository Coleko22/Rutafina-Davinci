from django.db import models
from users.models import Cliente, Repartidor
from catalog.models import Comercio, Producto

class MetodoPago(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50) # Ej: Tarjeta, Efectivo, MercadoPago
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=50, default='Vigente')

    def __str__(self):
        return f"{self.titulo} ({self.porcentaje_descuento}%)"


class Pedido(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name='pedidos')
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, related_name='pedidos')
    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    fecha_hora = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, default='Pendiente') # Pendiente, En preparación, En camino, Entregado, Cancelado
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente} ({self.estado})"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en Pedido #{self.pedido.id}"


class Entrega(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='entrega')
    repartidor = models.ForeignKey(Repartidor, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado_entrega = models.CharField(max_length=50, default='Pendiente')

    def __str__(self):
        return f"Entrega de Pedido #{self.pedido.id} ({self.estado_entrega})"


class Pago(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='pago')
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pago = models.CharField(max_length=50, default='Completado')

    def __str__(self):
        return f"Pago #{self.id} - ${self.importe} ({self.estado_pago})"