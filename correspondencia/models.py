from django.db import models
from django.utils import timezone

class ControlCorrespondencia(models.Model):
    TIPO_CARTA_CHOICES = [
        ('COBRO', 'Cobro de Honorarios'),
        ('PROPUESTA', 'Propuesta de Servicios'),
        ('INFORME', 'Informe General'),
    ]
    
    tipo_carta = models.CharField(max_length=20, choices=TIPO_CARTA_CHOICES, default='COBRO', verbose_name="Tipo de Documento")
    gestion = models.IntegerField(default=timezone.now().year, verbose_name="Gestión")
    numero = models.IntegerField(editable=False, null=True, blank=True, verbose_name="Nro Correlativo")
    unidad_cites = models.CharField(max_length=50, default="GG/BT&A/OF.", verbose_name="Unidad / CITES")
    
    destino = models.CharField(max_length=200, verbose_name="Destino (Cliente)")
    nit = models.CharField(max_length=50, blank=True, null=True, verbose_name="NIT")
    
    numero_factura = models.CharField(max_length=50, blank=True, null=True, verbose_name="Nº de Factura")
    fecha_factura = models.DateField(blank=True, null=True, verbose_name="Fecha de Factura")
    
    factura_pdf = models.FileField(upload_to='facturas_pdf/', blank=True, null=True, verbose_name="Adjuntar Factura (PDF)")
    
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha de la Carta")
    objeto = models.CharField(max_length=300, verbose_name="Objeto / Referencia")
    monto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Monto (Bs)")

    def save(self, *args, **kwargs):
        if not self.pk:  
            ultimo = ControlCorrespondencia.objects.filter(gestion=self.gestion).order_by('-numero').first()
            self.numero = (ultimo.numero + 1) if ultimo and ultimo.numero else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.unidad_cites} {self.correlativo_completo}"

    @property
    def correlativo_completo(self):
        return f"No. {str(self.numero).zfill(3)}/{self.gestion}"