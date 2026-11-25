from django.db import models
from clientes.models import Cliente # <--- IMPORTANTE: Importar Cliente

class ConfiguracionBoleta(models.Model):
    # Conectamos la configuración a UN cliente específico
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='config_boleta', verbose_name="Cliente")
    
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name="Logo de la Empresa")
    color_cabecera = models.CharField(max_length=7, default='#0b2b5c', verbose_name="Color Cabecera")
    color_tabla = models.CharField(max_length=7, default='#0b2b5c', verbose_name="Color Tabla")
    color_neto = models.CharField(max_length=7, default='#eaf6ed', verbose_name="Color Sueldo Neto")
    degradado = models.BooleanField(default=True, verbose_name="Aplicar degradado")

    class Meta:
        verbose_name = "Configuración de Boleta"
        verbose_name_plural = "Configuraciones de Boletas"

    def __str__(self):
        return f"Configuración de {self.cliente.razon_social}"