import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Cliente, Direccion, User


class RegistroForm(forms.ModelForm):
    """
    Registro del mockup 02: nombre, apellido, email, teléfono y UNA contraseña.
    El username (obligatorio en AbstractUser) se genera solo a partir del email.
    """
    password = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres', 'autocomplete': 'new-password'}),
    )
    acepto = forms.BooleanField(
        label='Acepto los términos y condiciones',
        error_messages={'required': 'Tenés que aceptar los términos para crear la cuenta.'},
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telefono')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Email', 'telefono': 'Teléfono'}
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Thiago', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'González', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'vos@mail.com', 'autocomplete': 'email'}),
            'telefono': forms.TextInput(attrs={'placeholder': '11 5555 5555', 'autocomplete': 'tel', 'type': 'tel'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya hay una cuenta con ese email. Probá ingresar.')
        return email

    def _post_clean(self):
        super()._post_clean()
        # Igual que UserCreationForm: valida la contraseña con AUTH_PASSWORD_VALIDATORS
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password', error)

    @staticmethod
    def _username_libre(email):
        base = re.sub(r'[^\w.@+-]', '', email.split('@')[0])[:140] or 'usuario'
        candidato, n = base, 1
        while User.objects.filter(username=candidato).exists():
            n += 1
            candidato = f'{base}{n}'
        return candidato

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self._username_libre(user.email)
        user.role = User.Role.CLIENTE
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            Cliente.objects.get_or_create(usuario=user)
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email', widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}))
    password = forms.CharField(
        label='Contraseña', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))
    recordarme = forms.BooleanField(label='Recordarme', required=False, initial=True)

    error_messages = {
        'invalid_login': 'Email o contraseña incorrectos. Intentá de nuevo.',
        'inactive': 'Esta cuenta está desactivada.',
    }


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ('calle', 'numero', 'piso_depto', 'codigo_postal', 'localidad', 'alias', 'referencia')
        widgets = {
            'calle': forms.TextInput(attrs={'placeholder': 'Av. Rivadavia', 'autocomplete': 'address-line1'}),
            'numero': forms.TextInput(attrs={'placeholder': '5000'}),
            'piso_depto': forms.TextInput(attrs={'placeholder': '3° A', 'autocomplete': 'address-line2'}),
            'codigo_postal': forms.TextInput(attrs={'placeholder': 'C1424', 'autocomplete': 'postal-code'}),
            'localidad': forms.TextInput(attrs={'placeholder': 'CABA', 'autocomplete': 'address-level2'}),
            'alias': forms.TextInput(attrs={'placeholder': 'Trabajo'}),
            'referencia': forms.TextInput(attrs={'placeholder': 'Portón verde'}),
        }


class PerfilForm(forms.ModelForm):
    """'Mis datos' del perfil."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telefono', 'foto')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Email', 'telefono': 'Teléfono'}
        widgets = {
            'telefono': forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}),
            'foto': forms.FileInput(attrs={'accept': 'image/*', 'data-foto-input': ''}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ese email ya lo usa otra cuenta.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # En perfil.html los campos están en varias tarjetas: se asocian a <form id="perfil">
        for campo in self.fields.values():
            campo.widget.attrs['form'] = 'perfil'
        self.fields['first_name'].required = True

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'size') and foto.size > 3 * 1024 * 1024:
            raise forms.ValidationError('La foto puede pesar hasta 3 MB.')
        return foto


class PreferenciasForm(forms.ModelForm):
    tono = forms.ChoiceField(choices=Cliente.Tono.choices, widget=forms.RadioSelect, label='Tono de la app')

    class Meta:
        model = Cliente
        fields = ('tono', 'sin_tacc', 'vegetariano', 'vegano', 'sin_lactosa',
                  'avisar_pedido_sale', 'recibir_promos', 'modo_oscuro')
