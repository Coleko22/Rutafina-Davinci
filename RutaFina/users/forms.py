from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User
from .models import Direccion

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta:
        model = User
        fields = ('username', 'email', 'telefono')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ('alias', 'calle', 'numero', 'localidad', 'codigo_postal', 'referencia')
        widgets = {
            'alias': forms.TextInput(attrs={'placeholder': 'Ej: Casa, Trabajo, Novia'}),
            'calle': forms.TextInput(attrs={'placeholder': 'Ej: Av. Corrientes'}),
            'numero': forms.TextInput(attrs={'placeholder': 'Ej: 1234'}),
            'localidad': forms.TextInput(attrs={'placeholder': 'Ej: CABA'}),
            'codigo_postal': forms.TextInput(attrs={'placeholder': 'Ej: C1043'}),
            'referencia': forms.TextInput(attrs={'placeholder': 'Ej: Timbre 4B, portón negro'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})