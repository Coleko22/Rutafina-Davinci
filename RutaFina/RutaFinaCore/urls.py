from django.contrib import admin
from django.urls import path, include
from catalog.views import home_catalogo_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_catalogo_view, name='home'),
    path('auth/', include('users.urls')),
    path('catalogo/', include('catalog.urls')),
    path('pagos/', include('orders.urls')),
]