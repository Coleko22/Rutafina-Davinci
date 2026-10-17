from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, LoginForm
from django.shortcuts import get_object_or_404
from .models import Cliente, Direccion
from .forms import DireccionForm

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistroForm()

    return render(request, 'users/registro.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home_view(request):
    return render(request, 'home.html')

@login_required
def mis_direcciones_view(request):
    # Aseguramos que el usuario tenga perfil de Cliente creado
    cliente, _ = Cliente.objects.get_or_create(usuario=request.user)
    direcciones = cliente.direcciones.all()
    return render(request, 'users/direcciones.html', {'direcciones': direcciones})

@login_required
def agregar_direccion_view(request):
    cliente, _ = Cliente.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        form = DireccionForm(request.POST)
        if form.is_valid():
            direccion = form.save(commit=False)
            direccion.cliente = cliente
            direccion.save()
            return redirect('mis_direcciones')
    else:
        form = DireccionForm()

    return render(request, 'users/agregar_direccion.html', {'form': form})

@login_required
def eliminar_direccion_view(request, direccion_id):
    cliente = get_object_or_404(Cliente, usuario=request.user)
    direccion = get_object_or_404(Direccion, id=direccion_id, cliente=cliente)
    direccion.delete()
    return redirect('mis_direcciones')