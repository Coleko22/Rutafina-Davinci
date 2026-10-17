from django.db import models

class Comercio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30)
    email = models.EmailField()
    estado = models.CharField(max_length=50, default='Activo')

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    categoria = models.CharField(max_length=100, help_text="Ej: Pizzas, Hamburguesas, Bebidas")

    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.comercio.nombre})"