from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Cliente, Repartidor, Direccion

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Información adicional', {'fields': ('role', 'telefono')}),
    )
    list_display = ('email', 'username', 'role', 'is_staff', 'is_active')
    search_fields = ('email', 'username')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_registro')

@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'vehiculo', 'patente', 'disponibilidad')
    list_filter = ('disponibilidad',)

@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'alias', 'calle', 'numero', 'localidad')