import re

from django import forms

from .models import MetodoPago
from .validators import detectar_tipo_tarjeta, validar_algoritmo_luhn, validar_vencimiento


class PagoTarjetaForm(forms.Form):
    """Simulador de validación de tarjetas (página 'Medios de pago')."""
    titular = forms.CharField(
        max_length=100,
        label="Nombre y Apellido del Titular",
        widget=forms.TextInput(attrs={'placeholder': 'Como figura en la tarjeta'})
    )
    numero_tarjeta = forms.CharField(
        max_length=23,
        label="Número de Tarjeta",
        widget=forms.TextInput(attrs={'placeholder': '0000 0000 0000 0000', 'id': 'input-card-number',
                                      'inputmode': 'numeric', 'data-tarjeta-numero': ''})
    )
    mes_vencimiento = forms.IntegerField(
        min_value=1,
        max_value=12,
        label="Mes (MM)",
        widget=forms.NumberInput(attrs={'placeholder': 'MM'})
    )
    anio_vencimiento = forms.IntegerField(
        min_value=24,
        max_value=40,
        label="Año (AA)",
        widget=forms.NumberInput(attrs={'placeholder': 'AA'})
    )
    cvv = forms.CharField(
        max_length=4,
        min_length=3,
        label="CVV / CVC",
        widget=forms.PasswordInput(attrs={'placeholder': '123'})
    )

    def clean_numero_tarjeta(self):
        numero = self.cleaned_data.get('numero_tarjeta', '')
        if not validar_algoritmo_luhn(numero):
            raise forms.ValidationError("El número de tarjeta no es válido (falló verificación Luhn).")
        return re.sub(r'\D', '', numero)

    def clean(self):
        cleaned_data = super().clean()
        mes = cleaned_data.get('mes_vencimiento')
        anio = cleaned_data.get('anio_vencimiento')
        if mes and anio and not validar_vencimiento(mes, anio):
            raise forms.ValidationError("La tarjeta ingresada se encuentra vencida.")
        return cleaned_data


class CheckoutForm(forms.Form):
    """
    Pantalla "Resumen, dirección y pago" (mockup 04). Los datos de tarjeta solo
    son obligatorios si el medio elegido es Tarjeta, y se validan con los mismos
    validadores del simulador (Luhn + vencimiento). La tarjeta NO se guarda:
    solo los últimos 4 dígitos y el emisor para mostrar en el detalle.
    """
    direccion = forms.ModelChoiceField(
        queryset=None, widget=forms.RadioSelect, empty_label=None,
        error_messages={'required': 'Elegí a dónde lo llevamos.', 'invalid_choice': 'Elegí una dirección válida.'})
    metodo = forms.ChoiceField(
        choices=MetodoPago.Tipo.choices, widget=forms.RadioSelect, initial=MetodoPago.Tipo.TARJETA,
        error_messages={'required': 'Elegí cómo pagás.'})

    numero_tarjeta = forms.CharField(label='Número de tarjeta', max_length=23, required=False,
                                     widget=forms.TextInput(attrs={
                                         'placeholder': '0000 0000 0000 0000', 'inputmode': 'numeric',
                                         'autocomplete': 'cc-number', 'data-tarjeta-numero': ''}))
    titular = forms.CharField(label='Nombre como figura', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'placeholder': 'THIAGO GONZALEZ', 'autocomplete': 'cc-name'}))
    vencimiento = forms.CharField(label='Vencimiento', max_length=5, required=False,
                                  widget=forms.TextInput(attrs={
                                      'placeholder': 'MM/AA', 'inputmode': 'numeric',
                                      'autocomplete': 'cc-exp', 'data-vencimiento': ''}))
    cvv = forms.CharField(label='Código de seguridad', max_length=4, required=False,
                          widget=forms.PasswordInput(attrs={
                              'placeholder': '123', 'inputmode': 'numeric', 'autocomplete': 'cc-csc'}))

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['direccion'].queryset = cliente.direcciones.all()
        # Los inputs de tarjeta están fuera del <form id="checkout"> (ver checkout.html):
        # el atributo HTML form="checkout" los asocia igual.
        for nombre in ('numero_tarjeta', 'titular', 'vencimiento', 'cvv'):
            self.fields[nombre].widget.attrs['form'] = 'checkout'

    def clean(self):
        datos = super().clean()
        if datos.get('metodo') != MetodoPago.Tipo.TARJETA:
            return datos

        numero = re.sub(r'\D', '', datos.get('numero_tarjeta') or '')
        if not numero:
            self.add_error('numero_tarjeta', 'Ingresá el número de la tarjeta.')
        elif not validar_algoritmo_luhn(numero):
            self.add_error('numero_tarjeta', 'Ese número de tarjeta no es válido. Revisalo.')

        if not (datos.get('titular') or '').strip():
            self.add_error('titular', 'Ingresá el nombre como figura en la tarjeta.')

        venc = (datos.get('vencimiento') or '').strip()
        coincide = re.fullmatch(r'(\d{2})\s*/\s*(\d{2})', venc)
        if not coincide:
            self.add_error('vencimiento', 'Usá el formato MM/AA.')
        elif not validar_vencimiento(int(coincide.group(1)), int(coincide.group(2))):
            self.add_error('vencimiento', 'La tarjeta está vencida.')

        if not re.fullmatch(r'\d{3,4}', datos.get('cvv') or ''):
            self.add_error('cvv', 'Son 3 o 4 números, atrás de la tarjeta.')

        if numero:
            datos['tarjeta'] = {'ultimos4': numero[-4:], 'emisor': detectar_tipo_tarjeta(numero)}
        return datos
