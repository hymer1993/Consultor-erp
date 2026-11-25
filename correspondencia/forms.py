from django import forms
from django.utils import timezone
from .models import ControlCorrespondencia

class CorrespondenciaForm(forms.ModelForm):
    class Meta:
        model = ControlCorrespondencia
        fields = ['tipo_carta', 'unidad_cites', 'destino', 'nit', 'numero_factura', 'fecha_factura', 'fecha', 'objeto', 'monto', 'factura_pdf']
        widgets = {
            'tipo_carta': forms.Select(attrs={'class': 'form-control'}),
            'unidad_cites': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nit': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'numero_factura': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_factura': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'objeto': forms.TextInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'factura_pdf': forms.FileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['fecha'].initial = timezone.localdate()
            self.fields['fecha_factura'].initial = timezone.localdate()