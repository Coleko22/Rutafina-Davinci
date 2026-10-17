from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_catalogo_view, name='home_catalogo'),
    path('categoria/<str:categoria_nombre>/', views.productos_por_categoria_view, name='productos_por_categoria'),
    path('comercio/<int:comercio_id>/', views.detalle_comercio_view, name='detalle_comercio'),
]