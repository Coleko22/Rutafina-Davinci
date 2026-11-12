from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog import restaurantes
from .forms import DireccionForm, LoginForm, PerfilForm, PreferenciasForm, RegistroForm
from .models import Cliente, Direccion, Favorito


# --- Utilidades ----------------------------------------------------------------

def _next_seguro(request, por_defecto):
    """El parámetro `next` (POST o GET) si apunta a este mismo sitio; si no, `por_defecto`."""
    destino = request.POST.get('next') or request.GET.get('next') or ''
    if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return por_defecto


def _cliente(request):
    """Perfil de cliente del usuario logueado (se crea si falta, p. ej. usuarios del admin)."""
    cliente, _ = Cliente.objects.get_or_create(usuario=request.user)
    return cliente


def _inicio_segun_rol(user):
    return reverse('panel_repartidor') if user.es_repartidor else reverse('home')


# --- Acceso: login y registro en la misma pantalla (mockup 02) -------------------

def _render_acceso(request, login_form=None, registro_form=None, status=200):
    return render(request, 'users/acceso.html', {
        'login_form': login_form or LoginForm(request),
        'registro_form': registro_form or RegistroForm(),
        'next': _next_seguro(request, ''),
    }, status=status)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_inicio_segun_rol(request.user))

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not form.cleaned_data.get('recordarme'):
                request.session.set_expiry(0)  # se cierra al cerrar el navegador
            return redirect(_next_seguro(request, _inicio_segun_rol(user)))
        return _render_acceso(request, login_form=form)
    return _render_acceso(request)


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Listo, {user.first_name}. Ya tenés cuenta.')
            return redirect(_next_seguro(request, reverse('home')))
        return _render_acceso(request, registro_form=form)
    return _render_acceso(request)


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    return redirect('home')


# --- Perfil (mockup 07) ------------------------------------------------------------

@login_required
def perfil_view(request):
    cliente = _cliente(request)
    if request.method == 'POST':
        perfil_form = PerfilForm(request.POST, request.FILES, instance=request.user, prefix='datos')
        preferencias_form = PreferenciasForm(request.POST, instance=cliente, prefix='pref')
        if perfil_form.is_valid() and preferencias_form.is_valid():
            perfil_form.save()
            preferencias_form.save()
            messages.success(request, 'Cambios guardados.')
            return redirect('perfil')
        messages.error(request, 'Revisá los campos marcados.')
    else:
        perfil_form = PerfilForm(instance=request.user, prefix='datos')
        preferencias_form = PreferenciasForm(instance=cliente, prefix='pref')

    return render(request, 'users/perfil.html', {
        'perfil_form': perfil_form,
        'preferencias_form': preferencias_form,
        'cliente': cliente,
        'direcciones': cliente.direcciones.all(),
        'cantidad_pedidos': cliente.pedidos.count(),
        'restricciones_campos': [preferencias_form[c] for c in Cliente.RESTRICCIONES],
        'switches_campos': [preferencias_form[c] for c in ('avisar_pedido_sale', 'recibir_promos', 'modo_oscuro')],
    })


# --- Direcciones -----------------------------------------------------------------

@login_required
def mis_direcciones_view(request):
    # Las direcciones se gestionan en el perfil (sección "Direcciones guardadas").
    return redirect(reverse('perfil') + '#direcciones')


def _guardar_direccion(request, form, cliente):
    direccion = form.save(commit=False)
    direccion.cliente = cliente
    # La primera dirección queda como principal; si se marcó "usar como principal", también.
    es_primera = not cliente.direcciones.exclude(pk=direccion.pk).exists()
    direccion.save()
    if es_primera or request.POST.get('principal'):
        direccion.marcar_principal()
    return direccion


@login_required
def agregar_direccion_view(request):
    cliente = _cliente(request)
    if request.method == 'POST':
        form = DireccionForm(request.POST)
        if form.is_valid():
            direccion = _guardar_direccion(request, form, cliente)
            messages.success(request, f'Guardamos {direccion.alias or direccion.linea}.')
            destino = _next_seguro(request, reverse('perfil') + '#direcciones')
            # Si viene del checkout, la dirección nueva queda elegida
            if destino.startswith(reverse('checkout')):
                request.session['checkout_direccion'] = direccion.id
            return redirect(destino)
    else:
        form = DireccionForm()
    return render(request, 'users/direccion_form.html', {
        'form': form, 'titulo': 'Nueva dirección', 'next': _next_seguro(request, ''),
    })


@login_required
def editar_direccion_view(request, direccion_id):
    cliente = _cliente(request)
    direccion = get_object_or_404(Direccion, id=direccion_id, cliente=cliente)
    if request.method == 'POST':
        form = DireccionForm(request.POST, instance=direccion)
        if form.is_valid():
            _guardar_direccion(request, form, cliente)
            messages.success(request, 'Dirección actualizada.')
            return redirect(_next_seguro(request, reverse('perfil') + '#direcciones'))
    else:
        form = DireccionForm(instance=direccion)
    return render(request, 'users/direccion_form.html', {
        'form': form, 'direccion': direccion, 'titulo': 'Editar dirección', 'next': _next_seguro(request, ''),
    })


@login_required
@require_POST
def eliminar_direccion_view(request, direccion_id):
    cliente = _cliente(request)
    direccion = get_object_or_404(Direccion, id=direccion_id, cliente=cliente)
    era_principal = direccion.principal
    direccion.delete()
    if era_principal:
        siguiente = cliente.direcciones.first()
        if siguiente:
            siguiente.marcar_principal()
    messages.success(request, 'Dirección eliminada.')
    return redirect(_next_seguro(request, reverse('perfil') + '#direcciones'))


@login_required
@require_POST
def direccion_principal_view(request, direccion_id):
    direccion = get_object_or_404(Direccion, id=direccion_id, cliente=_cliente(request))
    direccion.marcar_principal()
    request.session['checkout_direccion'] = direccion.id
    return redirect(_next_seguro(request, reverse('home')))


# --- Favoritos -------------------------------------------------------------------

@login_required
@require_POST
def favorito_toggle(request):
    slug = request.POST.get('slug', '').strip()
    codigo = request.POST.get('codigo', '').strip()
    comercio = restaurantes.obtener(slug)
    if comercio is None:
        raise Http404('Ese comercio no existe.')
    producto = None
    if codigo:
        producto = comercio.item(codigo)
        if producto is None:
            raise Http404('Ese producto no existe.')

    favorito, creado = Favorito.objects.get_or_create(
        usuario=request.user,
        comercio=comercio,
        producto=producto,
    )
    if not creado:
        favorito.delete()
    return redirect(_next_seguro(request, reverse('historial') + '#favoritos'))


def favoritos_de(user):
    """
    Claves 'slug:codigo' marcadas por el usuario ('slug:' para comercios), para
    pintar los corazones en los templates.
    """
    if not user.is_authenticated:
        return set()
    filas = Favorito.objects.filter(usuario=user).select_related('comercio', 'producto')
    return {
        f"{fav.comercio.slug}:{fav.producto.codigo if fav.producto else ''}"
        for fav in filas
    }
