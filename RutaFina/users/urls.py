from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('direcciones/', views.mis_direcciones_view, name='mis_direcciones'),
    path('direcciones/agregar/', views.agregar_direccion_view, name='agregar_direccion'),
    path('direcciones/eliminar/<int:direccion_id>/', views.eliminar_direccion_view, name='eliminar_direccion'),
]