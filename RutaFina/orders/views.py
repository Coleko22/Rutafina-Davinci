import io
import base64
import qrcode
import mercadopago
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MetodoPago
from .forms import PagoTarjetaForm
from .validators import detectar_tipo_tarjeta

MP_ACCESS_TOKEN = settings.MP_ACCESS_TOKEN

@login_required
def metodos_pago_view(request):
    metodos = MetodoPago.objects.filter(disponible=True)
    return render(request, 'orders/metodos_pago.html', {'metodos': metodos})

@login_required
def simulador_tarjeta_view(request):
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
    init_point = None

    try:
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        preference_data = {
            "items": [
                {
                    "title": "Pedido en RutaFina Delivery",
                    "quantity": 1,
                    "unit_price": 50.0,
                    "currency_id": "ARS"
                }
            ]
        }
        preference_response = sdk.preference().create(preference_data)
        response_data = preference_response.get("response", {})
        init_point = response_data.get("init_point") or response_data.get("sandbox_init_point")
    except Exception as e:
        print(f"Error Mercado Pago API: {e}")

    # Fallback si MP no devuelve preferencia o si no hay conexión
    if not init_point:
        init_point = "https://www.mercadopago.com.ar"

    # Generamos el código QR en memoria directamente con Python (Base64)
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(init_point)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    qr_data_uri = f"data:image/png;base64,{qr_base64}"

    return render(request, 'orders/mercadopago_checkout.html', {
        'init_point': init_point,
        'qr_data_uri': qr_data_uri,
        'monto': "50.00",
    })