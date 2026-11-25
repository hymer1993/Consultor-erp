from django import forms
from .models import Cliente, CredencialCliente

class ClienteForm(forms.ModelForm):
    # --- CAMPOS EXTRA PARA CREDENCIALES ---
    user_sin = forms.CharField(required=False, label="Usuario SIN (Impuestos)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_sin = forms.CharField(required=False, label="Contraseña SIN", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))
    user_gestora = forms.CharField(required=False, label="Usuario Gestora Pública", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_gestora = forms.CharField(required=False, label="Contraseña Gestora", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))
    user_cns = forms.CharField(required=False, label="Usuario Caja Salud (CNS/COSSMIL)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_cns = forms.CharField(required=False, label="Contraseña Caja Salud", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))
    user_sedem = forms.CharField(required=False, label="Usuario Subsidios (SEDEM)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_sedem = forms.CharField(required=False, label="Contraseña SEDEM", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))
    
    # --- NUEVOS CAMPOS EXTRA PARA ADUANA Y FIRMA DIGITAL ---
    user_aduana = forms.CharField(required=False, label="Usuario Aduana", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pass_aduana = forms.CharField(required=False, label="Contraseña Aduana", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))
    user_firma = forms.CharField(required=False, label="Usuario Firma Digital", widget=forms.TextInput(attrs={'class': 'form-control'}))
    pin_firma = forms.CharField(required=False, label="PIN Firma Digital", widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}))

    class Meta:
        model = Cliente
        fields = [
            # Datos Generales
            'nit', 'razon_social', 'estado_cliente', 'tipo_empresa', 'tipo_sociedad',
            'rubro_actividad', 'direccion', 'telefono', 'email', 'password_email_empresa',
            'tipo_servicio', 'honorarios_mensuales', 'cierre_gestion', 'habilitado_para_cobro',
            'tipo_caja_salud', 'numero_patronal',
            # Representante Legal
            'representante_legal', 'rep_legal_email',
            # Datos de Contacto
            'contacto_nombre', 'contacto_cargo', 'contacto_email', 'contacto_celular',
        ]
        widgets = {
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'estado_cliente': forms.Select(attrs={'class': 'form-control'}),
            'tipo_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_sociedad': forms.TextInput(attrs={'class': 'form-control'}),
            'rubro_actividad': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password_email_empresa': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'tipo_servicio': forms.TextInput(attrs={'class': 'form-control'}),
            'honorarios_mensuales': forms.NumberInput(attrs={'class': 'form-control'}),
            'cierre_gestion': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_caja_salud': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_patronal': forms.TextInput(attrs={'class': 'form-control'}),
            'representante_legal': forms.TextInput(attrs={'class': 'form-control'}),
            'rep_legal_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contacto_celular': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            for cred in self.instance.credenciales.all():
                portal_lower = cred.portal.lower()
                if 'sin' in portal_lower:
                    self.fields['user_sin'].initial = cred.usuario
                    self.fields['pass_sin'].initial = cred.password
                elif 'gestora' in portal_lower:
                    self.fields['user_gestora'].initial = cred.usuario
                    self.fields['pass_gestora'].initial = cred.password
                elif 'cns' in portal_lower or 'caja' in portal_lower:
                    self.fields['user_cns'].initial = cred.usuario
                    self.fields['pass_cns'].initial = cred.password
                elif 'sedem' in portal_lower or 'subsidio' in portal_lower:
                    self.fields['user_sedem'].initial = cred.usuario
                    self.fields['pass_sedem'].initial = cred.password
                elif 'aduana' in portal_lower:
                    self.fields['user_aduana'].initial = cred.usuario
                    self.fields['pass_aduana'].initial = cred.password
                elif 'firma' in portal_lower:
                    self.fields['user_firma'].initial = cred.usuario
                    self.fields['pin_firma'].initial = cred.password