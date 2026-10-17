from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        REPARTIDOR = 'REPARTIDOR', 'Repartidor'
        COMERCIO = 'COMERCIO', 'Comercio'
        ADMIN = 'ADMIN', 'Administrador'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENTE)
    telefono = models.CharField(max_length=30, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente')
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Cliente: {self.usuario.get_full_name() or self.usuario.username}"


class Repartidor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_repartidor')
    vehiculo = models.CharField(max_length=50)
    patente = models.CharField(max_length=20)
    disponibilidad = models.BooleanField(default=True)

    def __str__(self):
        return f"Repartidor: {self.usuario.username} - {self.vehiculo}"


class Direccion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='direcciones')
    calle = models.CharField(max_length=150)
    numero = models.CharField(max_length=20)
    localidad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    referencia = models.CharField(max_length=255, blank=True)
    alias = models.CharField(max_length=50, blank=True, help_text="Ej: Casa, Trabajo")

    def __str__(self):
        return f"{self.calle} {self.numero}, {self.localidad} ({self.alias})"