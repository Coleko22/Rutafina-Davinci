from django.contrib import admin
from .models import MetodoPago, Promocion, Pedido, DetallePedido, Entrega, Pago

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'restaurante_nombre', 'estado', 'total', 'fecha_hora')
    list_filter = ('estado', 'fecha_hora', 'restaurante_nombre')
    inlines = [DetallePedidoInline]

    def save_model(self, request, obj, form, change):
        # Si se cambia el estado desde el admin, se anotan las horas de la barra de seguimiento
        if change and 'estado' in form.changed_data:
            obj.cambiar_estado(obj.estado)
        else:
            super().save_model(request, obj, form, change)

@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'disponible')

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'porcentaje_descuento', 'fecha_inicio', 'fecha_fin', 'estado')

@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'repartidor', 'estado_entrega', 'distancia_km', 'pago_repartidor', 'fecha_asignacion')
    list_filter = ('estado_entrega',)

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'metodo_pago', 'importe', 'estado_pago', 'fecha')