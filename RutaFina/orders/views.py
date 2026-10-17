from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MetodoPago
from .forms import PagoTarjetaForm
from .validators import detectar_tipo_tarjeta

@login_required
def metodos_pago_view(request):
    """Muestra los métodos de pago habilitados en la plataforma."""
    metodos = MetodoPago.objects.filter(disponible=True)
    return render(request, 'orders/metodos_pago.html', {'metodos': metodos})

@login_required
def simulador_tarjeta_view(request):
    """Permite validar los datos de una tarjeta de crédito/débito."""
    tipo_detectado = None
    if request.method == 'POST':
        form = PagoTarjetaForm(request.POST)
        if form.is_valid():
            numero = form.cleaned_data['numero_tarjeta']
            tipo_detectado = detectar_tipo_tarjeta(numero)
            messages.success(request, f"¡Tarjeta {tipo_detectado} validada con éxito! Operación simulada aprobada.")
            return render(request, 'orders/tarjeta_exito.html', {
                'titular': form.cleaned_data['titular'],
                'tipo': tipo_detectado,
                'ultimos4': numero[-4:]
            })
    else:
        form = PagoTarjetaForm()

    return render(request, 'orders/simulador_tarjeta.html', {'form': form})

@login_required
def mercadopago_simulado_view(request):
    """Muestra el checkout simulado de Mercado Pago con opciones de QR / Dinero en cuenta."""
    return render(request, 'orders/mercadopago_checkout.html')