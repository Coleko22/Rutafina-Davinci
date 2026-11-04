from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_catalogo_view, name='home_catalogo'),
    path('buscar/', views.buscar_view, name='buscar'),
    path('categoria/<str:categoria_nombre>/', views.productos_por_categoria_view, name='productos_por_categoria'),
    path('comercio/<int:comercio_id>/', views.detalle_comercio_view, name='detalle_comercio'),
    path('restaurante/<slug:slug>/', views.detalle_restaurante_view, name='detalle_restaurante'),
]
