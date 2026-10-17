from django.contrib import admin
from .models import Comercio, Producto

@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono', 'email', 'estado')
    search_fields = ('nombre', 'direccion')
    list_filter = ('estado',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'comercio', 'categoria', 'precio', 'disponible')
    search_fields = ('nombre', 'categoria')
    list_filter = ('categoria', 'disponible', 'comercio')