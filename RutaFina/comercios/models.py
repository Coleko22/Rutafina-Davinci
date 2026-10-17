from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Comercio(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    horario = models.CharField(max_length=100)
    estado = models.CharField(max_length=20, default="activo")

    def agregarProducto(self, producto):
        producto.comercio = self
        producto.save()

    def modificarProducto(self, producto, datos):
        for campo, valor in datos.items():
            setattr(producto, campo, valor)
        producto.save()

    def eliminarProducto(self, producto):
        producto.delete()

    def aceptarPedido(self, pedido):
        pedido.cambiarEstado("aceptado")

    def rechazarPedido(self, pedido):
        pedido.cambiarEstado("rechazado")

    def actualizarEstadoPedido(self, pedido, estado):
        pedido.cambiarEstado(estado)

    def __str__(self):
        return self.nombre
        
class Producto(models.Model):
    comercio = models.ForeignKey(
        Comercio,
        on_delete=models.CASCADE,
        related_name="productos"
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    disponible = models.BooleanField(default=True)
    categoria = models.CharField(max_length=50)

    def cambiarPrecio(self, nuevo_precio):
        self.precio = nuevo_precio
        self.save()

    def cambiarDisponibilidad(self):
        self.disponible = not self.disponible
        self.save()

    def __str__(self):
        return self.nombre