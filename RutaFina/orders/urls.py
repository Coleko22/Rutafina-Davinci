from django.urls import path
from . import views

urlpatterns = [
    # Flujo de compra
    path('checkout/', views.checkout_view, name='checkout'),
    path('pedido/<int:pedido_id>/', views.pedido_detalle_view, name='pedido_detalle'),
    path('pedido/<int:pedido_id>/cancelar/', views.cancelar_pedido_view, name='cancelar_pedido'),
    path('pedido/<int:pedido_id>/repetir/', views.repetir_pedido_view, name='repetir_pedido'),
    path('pedido/<int:pedido_id>/billetera/', views.pago_billetera_view, name='pago_billetera'),
    path('pedido/<int:pedido_id>/billetera/retorno/', views.pago_billetera_retorno_view, name='pago_billetera_retorno'),
    path('mis-pedidos/', views.historial_view, name='historial'),

    # Panel del repartidor
    path('repartidor/', views.panel_repartidor_view, name='panel_repartidor'),
    path('repartidor/en-linea/', views.repartidor_en_linea_view, name='repartidor_en_linea'),
    path('repartidor/tomar/<int:pedido_id>/', views.repartidor_tomar_view, name='repartidor_tomar'),
    path('repartidor/avanzar/', views.repartidor_avanzar_view, name='repartidor_avanzar'),

    # Medios de pago (páginas de prueba que ya existían)
    path('metodos/', views.metodos_pago_view, name='metodos_pago'),
    path('tarjeta/validar/', views.simulador_tarjeta_view, name='simulador_tarjeta'),
    path('mercadopago/checkout/', views.mercadopago_simulado_view, name='mercadopago_checkout'),
]
