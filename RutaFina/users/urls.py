from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('perfil/', views.perfil_view, name='perfil'),

    path('direcciones/', views.mis_direcciones_view, name='mis_direcciones'),
    path('direcciones/agregar/', views.agregar_direccion_view, name='agregar_direccion'),
    path('direcciones/<int:direccion_id>/editar/', views.editar_direccion_view, name='editar_direccion'),
    path('direcciones/eliminar/<int:direccion_id>/', views.eliminar_direccion_view, name='eliminar_direccion'),
    path('direcciones/<int:direccion_id>/principal/', views.direccion_principal_view, name='direccion_principal'),

    path('favoritos/toggle/', views.favorito_toggle, name='favorito_toggle'),

    # "¿Te la olvidaste?": vistas de Django con templates propios (el mail sale por consola en desarrollo)
    path('recuperar/', auth_views.PasswordResetView.as_view(
        template_name='users/recuperar.html',
        success_url=reverse_lazy('password_reset_done')), name='password_reset'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/recuperar_enviado.html'), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/recuperar_nueva.html',
        success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    path('recuperar/listo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/recuperar_listo.html'), name='password_reset_complete'),
]
