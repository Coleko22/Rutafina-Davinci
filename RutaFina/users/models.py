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
    foto = models.ImageField(upload_to='avatares/', blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def iniciales(self):
        """'Thiago González' -> 'TG'. Es el avatar cuando no hay foto."""
        partes = [p for p in (self.first_name, self.last_name) if p]
        if partes:
            return ''.join(p[0] for p in partes).upper()[:2]
        return (self.username or self.email)[:2].upper()

    @property
    def nombre_visible(self):
        return self.get_full_name() or self.username

    @property
    def es_repartidor(self):
        return self.role == self.Role.REPARTIDOR or hasattr(self, 'perfil_repartidor')


class Cliente(models.Model):
    class Tono(models.TextChoices):
        TRANQUI = 'TRANQUI', 'Tranqui'
        ENOJADO = 'ENOJADO', 'Enojado'
        FURIOSO = 'FURIOSO', 'Furioso'

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente')
    fecha_registro = models.DateField(auto_now_add=True)

    # Preferencias (pantalla "Personalización de usuario")
    tono = models.CharField(max_length=10, choices=Tono.choices, default=Tono.FURIOSO,
                            help_text='Cambia los textos del sitio.')
    sin_tacc = models.BooleanField('Sin TACC', default=False)
    vegetariano = models.BooleanField(default=False)
    vegano = models.BooleanField(default=False)
    sin_lactosa = models.BooleanField('Sin lactosa', default=False)
    avisar_pedido_sale = models.BooleanField('Avisarme cuando el pedido sale', default=True)
    recibir_promos = models.BooleanField('Recibir promos por email', default=False)
    modo_oscuro = models.BooleanField('Modo oscuro', default=False)

    RESTRICCIONES = ('sin_tacc', 'vegetariano', 'vegano', 'sin_lactosa')

    def __str__(self):
        return f"Cliente: {self.usuario.get_full_name() or self.usuario.username}"

    @property
    def restricciones(self):
        """Claves de las restricciones marcadas (coinciden con restaurantes.ETIQUETAS)."""
        return [r for r in self.RESTRICCIONES if getattr(self, r)]

    @property
    def direccion_principal(self):
        return self.direcciones.filter(principal=True).first() or self.direcciones.first()


class Repartidor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_repartidor')
    vehiculo = models.CharField(max_length=50)
    patente = models.CharField(max_length=20)
    disponibilidad = models.BooleanField(default=True, help_text='En línea para tomar pedidos.')

    def __str__(self):
        return f"Repartidor: {self.usuario.username} - {self.vehiculo}"

    @property
    def nombre_corto(self):
        """'Martín R.'"""
        u = self.usuario
        if u.first_name:
            return f"{u.first_name} {u.last_name[:1]}.".strip() if u.last_name else u.first_name
        return u.username


class Direccion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='direcciones')
    calle = models.CharField(max_length=150)
    numero = models.CharField('Número', max_length=20)
    piso_depto = models.CharField('Piso / Depto', max_length=30, blank=True)
    localidad = models.CharField(max_length=100, default='CABA')
    codigo_postal = models.CharField('Código postal', max_length=20)
    referencia = models.CharField('Indicaciones', max_length=255, blank=True)
    alias = models.CharField(max_length=50, blank=True, help_text="Ej: Casa, Trabajo")
    principal = models.BooleanField(default=False)

    class Meta:
        ordering = ['-principal', 'id']

    def __str__(self):
        return f"{self.calle} {self.numero}, {self.localidad} ({self.alias})"

    @property
    def linea(self):
        """'Av. Corrientes 1234, 5° B'"""
        texto = f"{self.calle} {self.numero}"
        return f"{texto}, {self.piso_depto}" if self.piso_depto else texto

    @property
    def completa(self):
        return f"{self.linea}, {self.localidad}"

    def marcar_principal(self):
        """Deja a esta como la única principal del cliente."""
        self.cliente.direcciones.exclude(pk=self.pk).update(principal=False)
        if not self.principal:
            self.principal = True
            self.save(update_fields=['principal'])


class Favorito(models.Model):
    """
    Un comercio (item_codigo vacío) o un producto marcado con el corazón.
    Guarda slug/código porque los restaurantes todavía viven en catalog/restaurantes.py.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    restaurante_slug = models.SlugField(max_length=80)
    item_codigo = models.CharField(max_length=20, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'restaurante_slug', 'item_codigo'], name='favorito_unico'),
        ]

    def __str__(self):
        return f"{self.usuario} ♥ {self.restaurante_slug} {self.item_codigo}".strip()

    @property
    def es_producto(self):
        return bool(self.item_codigo)

    @property
    def restaurante(self):
        from catalog import restaurantes
        return restaurantes.obtener(self.restaurante_slug)

    @property
    def item(self):
        restaurante = self.restaurante
        return restaurante.item(self.item_codigo) if restaurante and self.item_codigo else None
