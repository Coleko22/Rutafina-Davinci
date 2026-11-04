from django.urls import path
from . import views

urlpatterns = [
    path('agregar/<slug:slug>/<str:codigo>/', views.agregar, name='carrito_agregar'),
    path('restar/<str:codigo>/', views.restar, name='carrito_restar'),
    path('eliminar/<str:codigo>/', views.eliminar, name='carrito_eliminar'),
    path('cupon/', views.aplicar_cupon, name='carrito_cupon'),
]
