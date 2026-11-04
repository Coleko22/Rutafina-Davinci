from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from catalog.views import home_catalogo_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_catalogo_view, name='home'),
    path('auth/', include('users.urls')),
    path('catalogo/', include('catalog.urls')),
    path('pagos/', include('orders.urls')),   # checkout, pedidos, historial y panel del repartidor
    path('carrito/', include('cart.urls')),
]

# En desarrollo Django sirve las fotos de perfil subidas (MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
