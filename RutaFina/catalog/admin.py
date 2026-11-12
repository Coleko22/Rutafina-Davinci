from django.contrib import admin

from .models import CategoriaMenu, Comercio, Cupon, Producto, PromocionComercio, Rubro


@admin.register(Rubro)
class RubroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'orden')
    prepopulated_fields = {'slug': ('nombre',)}


class CategoriaMenuInline(admin.TabularInline):
    model = CategoriaMenu
    extra = 1


class ProductoInline(admin.TabularInline):
    model = Producto
    extra = 1


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rubro', 'rating', 'costo_envio', 'activo')
    list_filter = ('activo', 'rubro')
    search_fields = ('nombre', 'cocina', 'direccion')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [CategoriaMenuInline, ProductoInline]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'comercio', 'categoria', 'precio', 'disponible')
    list_filter = ('disponible', 'comercio', 'sin_tacc', 'vegetariano', 'vegano', 'sin_lactosa')
    search_fields = ('codigo', 'nombre', 'descripcion')


@admin.register(PromocionComercio)
class PromocionComercioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'comercio', 'tipo', 'badge', 'activa')
    list_filter = ('activa', 'tipo')


@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo', 'porcentaje', 'minimo', 'destacado_home', 'activo')
    list_filter = ('activo', 'destacado_home', 'tipo')