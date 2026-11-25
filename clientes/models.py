from django.db import models

class Cliente(models.Model):
    # --- DATOS GENERALES DE LA EMPRESA ---
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    razon_social = models.CharField(max_length=200, verbose_name="Razón Social")
    
    ESTADO_CHOICES = [
        ('activo', 'Activo / Recurrente'),
        ('eventual', 'Eventual'),
        ('inactivo', 'Inactivo'),
    ]
    estado_cliente = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo', verbose_name="Estado del Cliente")
    
    tipo_empresa = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Empresa")
    tipo_sociedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Sociedad")
    rubro_actividad = models.CharField(max_length=150, blank=True, null=True, verbose_name="Rubro Actividad")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email de la Empresa")
    password_email_empresa = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contraseña Email Empresa")
    
    tipo_servicio = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Servicio")
    honorarios_mensuales = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Honorarios Mensuales")
    cierre_gestion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cierre de Gestión")
    habilitado_para_cobro = models.BooleanField(default=True, verbose_name="Habilitado para Cobro")
    
    # --- DATOS DE CAJA DE SALUD (Nuevos) ---
    tipo_caja_salud = models.CharField(max_length=100, blank=True, null=True, verbose_name="Caja de Salud a la que Aporta")
    numero_patronal = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número Patronal")

    # --- DATOS DEL REPRESENTANTE LEGAL ---
    representante_legal = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre del Representante Legal")
    rep_legal_email = models.EmailField(blank=True, null=True, verbose_name="Email del Representante Legal")

    # --- DATOS DE CONTACTO ---
    contacto_nombre = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de Contacto")
    contacto_cargo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cargo de Contacto")
    contacto_email = models.EmailField(blank=True, null=True, verbose_name="Email de Contacto")
    contacto_celular = models.CharField(max_length=50, blank=True, null=True, verbose_name="Celular de Contacto")

    # --- AUDITORÍA ---
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.razon_social} ({self.nit})"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['razon_social']


class CredencialCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='credenciales')
    portal = models.CharField(max_length=100, verbose_name="Portal")
    usuario = models.CharField(max_length=100, blank=True, null=True, verbose_name="Usuario")
    password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contraseña")
    token = models.CharField(max_length=100, blank=True, null=True, verbose_name="Token / PIN")

    def __str__(self):
        return f"{self.portal} - {self.cliente.razon_social}"

    class Meta:
        verbose_name = "Credencial"
        verbose_name_plural = "Credenciales"
        unique_together = ('cliente', 'portal')