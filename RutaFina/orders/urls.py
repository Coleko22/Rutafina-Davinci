from django.urls import path
from . import views

urlpatterns = [
    path('metodos/', views.metodos_pago_view, name='metodos_pago'),
    path('tarjeta/validar/', views.simulador_tarjeta_view, name='simulador_tarjeta'),
    path('mercadopago/checkout/', views.mercadopago_simulado_view, name='mercadopago_checkout'),
]