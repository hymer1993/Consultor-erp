from django.db import models
from clientes.models import Cliente
from django.contrib.auth.models import User

class ConfiguracionEmpresa(models.Model):
    nombre = models.CharField(max_length=150, default="J&A ASOCIADOS S.R.L.")
    nit = models.CharField(max_length=30, default="123456789")
    direccion = models.CharField(max_length=200, default="SANTA CRUZ - BOLIVIA")
    
    # Logo para el encabezado de los documentos
    logo = models.ImageField(upload_to='logos_empresa/', blank=True, null=True, verbose_name="Logo Encabezado")
    
    # Logo para la marca de agua
    logo_marca_agua = models.ImageField(upload_to='logos_empresa/', blank=True, null=True, verbose_name="Logo Marca de Agua")
    
    # QR de Cobro y su fecha de vencimiento
    qr_cobro = models.ImageField(upload_to='qr_pagos/', blank=True, null=True, verbose_name="Código QR de Cobro")
    qr_vencimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Vencimiento del QR")
    
    # Datos del Representante Legal
    rep_nombre = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre del Representante Legal")
    rep_cargo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cargo del Representante Legal")
    rep_firma = models.ImageField(upload_to='firmas/', blank=True, null=True, verbose_name="Firma del Representante Legal")

    def __str__(self):
        return f"Configuración: {self.nombre}"

    class Meta:
        verbose_name = "Configuración de Empresa"
        verbose_name_plural = "Configuración de Empresa"

class ConceptoGasto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Concepto")
    cuenta_debe = models.CharField(max_length=100, verbose_name="Cuenta Contable (Debe)")
    cuenta_haber = models.CharField(max_length=100, verbose_name="Cuenta Contable (Haber)", default="110100 Caja Chica")
    
    def __str__(self):
        return self.nombre

class SolicitudCajaChica(models.Model):
    ESTADOS = [('abierta', 'Abierta'), ('rendida', 'Rendida')]
    TIPO_CANCELACION = [('anticipo', 'Anticipo'), ('parcial', 'Parcial'), ('total', 'Total')]
    TIPO_PAGO = [('efectivo', 'Efectivo'), ('cheque', 'Cheque'), ('transferencia', 'Transferencia')]

    numero_solicitud = models.CharField(max_length=20, unique=True, blank=True, null=True)
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_solicitud = models.DateField()
    area = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    motivo_gasto = models.TextField(blank=True, null=True)
    proveedor = models.CharField(max_length=150, blank=True, null=True)
    importe_solicitado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Saldo Final / A Favor")
    
    tipo_cancelacion = models.CharField(max_length=20, choices=TIPO_CANCELACION, default='total')
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO, default='efectivo')
    banco = models.CharField(max_length=100, blank=True, null=True)
    nro_cuenta = models.CharField(max_length=50, blank=True, null=True)
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True)
    moneda = models.CharField(max_length=20, blank=True, null=True)
    ci_beneficiario = models.CharField(max_length=20, blank=True, null=True)
    correo_beneficiario = models.EmailField(blank=True, null=True)
    direccion_beneficiario = models.CharField(max_length=200, blank=True, null=True)
    beneficiario_orden = models.CharField(max_length=150, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierta')
    
    rendido_de = models.CharField(max_length=150, blank=True, null=True, default="HYMER")
    rendido_a = models.CharField(max_length=150, blank=True, null=True, default="GERENCIA ADMINISTRATIVA")
    prestamo_tercero = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Solicitud {self.numero_solicitud}"

class ReembolsoEmpleado(models.Model):
    numero_reembolso = models.CharField(max_length=20, unique=True)
    empleado_nombre = models.CharField(max_length=150)
    fecha_reembolso = models.DateField(auto_now_add=True)
    total_reembolsado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    pagado = models.BooleanField(default=False, verbose_name="¿Dinero Entregado?")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name="Fecha Real de Pago")

    def __str__(self):
        return f"Reembolso {self.numero_reembolso} - {self.empleado_nombre}"

class CartaCobro(models.Model):
    numero_carta = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_emision = models.DateField(auto_now_add=True)
    total_cobrar = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    correspondencia = models.OneToOneField(
        'correspondencia.ControlCorrespondencia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carta_cobro_caja_chica'
    )
    
    cobrado = models.BooleanField(default=False, verbose_name="¿Dinero Cobrado?")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name="Fecha Real de Cobro")

    def __str__(self):
        return f"Carta {self.numero_carta} - {self.cliente.razon_social}"

class ReciboCajaChica(models.Model):
    ESTADOS = [('activo', 'Activo'), ('anulado', 'Anulado')]
    TIPO_RETENCION = [
        ('ninguna', 'No Aplica'),
        ('servicios', 'Servicios (13% + 3%)'),
        ('bienes', 'Bienes (5% + 3%)'),
    ]
    
    solicitud = models.ForeignKey(SolicitudCajaChica, on_delete=models.SET_NULL, null=True, blank=True)
    numero = models.CharField(max_length=20, unique=True)
    fecha = models.DateField()
    lugar = models.CharField(max_length=50, default='SANTA CRUZ')
    
    tercero_nombre = models.CharField(max_length=150, verbose_name="Pagado a")
    nit_ci = models.CharField(max_length=20, blank=True, null=True)
    concepto = models.TextField()
    
    concepto_gasto = models.ForeignKey(ConceptoGasto, on_delete=models.SET_NULL, null=True)
    tipo_retencion = models.CharField(max_length=20, choices=TIPO_RETENCION, default='ninguna')
    
    total_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retencion_rc_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retencion_iue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retencion_it = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    factura_nro = models.CharField(max_length=50, blank=True, null=True)
    
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    asumido_por_cliente = models.BooleanField(default=False, verbose_name="¿Cobrar al cliente?")
    
    devuelto_al_empleado = models.BooleanField(default=False, verbose_name="Devuelto al Empleado")
    cobrado_al_cliente = models.BooleanField(default=False, verbose_name="Cobrado al Cliente")
    fecha_devolucion = models.DateField(null=True, blank=True, verbose_name="Fecha Devolución Empleado")
    fecha_cobro = models.DateField(null=True, blank=True, verbose_name="Fecha Cobro Cliente")
    reembolso = models.ForeignKey(ReembolsoEmpleado, on_delete=models.SET_NULL, null=True, blank=True)
    carta_cobro = models.ForeignKey(CartaCobro, on_delete=models.SET_NULL, null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recibo {self.numero}"
