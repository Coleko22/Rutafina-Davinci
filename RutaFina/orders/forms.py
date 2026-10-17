from django import forms
from .validators import validar_algoritmo_luhn, detectar_tipo_tarjeta, validar_vencimiento

class PagoTarjetaForm(forms.Form):
    titular = forms.CharField(
        max_length=100,
        label="Nombre y Apellido del Titular",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Como figura en la tarjeta'})
    )
    numero_tarjeta = forms.CharField(
        max_length=19,
        label="Número de Tarjeta",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXX XXXX XXXX XXXX', 'id': 'input-card-number'})
    )
    mes_vencimiento = forms.IntegerField(
        min_value=1,
        max_value=12,
        label="Mes (MM)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'MM'})
    )
    anio_vencimiento = forms.IntegerField(
        min_value=24,
        max_value=40,
        label="Año (AA)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'AA'})
    )
    cvv = forms.CharField(
        max_length=4,
        min_length=3,
        label="CVV / CVC",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '123'})
    )

    def clean_numero_tarjeta(self):
        numero = self.cleaned_data.get('numero_tarjeta', '')
        if not validar_algoritmo_luhn(numero):
            raise forms.ValidationError("El número de tarjeta no es válido (falló verificación Luhn).")
        return numero

    def clean(self):
        cleaned_data = super().clean()
        mes = cleaned_data.get('mes_vencimiento')
        anio = cleaned_data.get('anio_vencimiento')
        if mes and anio and not validar_vencimiento(mes, anio):
            raise forms.ValidationError("La tarjeta ingresada se encuentra vencida.")
        return cleaned_data