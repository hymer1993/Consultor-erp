from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Cliente, CredencialCliente
from .forms import ClienteForm
import pandas as pd

# --- FUNCIÓN AUXILIAR PARA GUARDAR CREDENCIALES ---
def guardar_credenciales(cliente, form):
    mapeo = {
        'SIN': ('user_sin', 'pass_sin'),
        'Gestora Pública': ('user_gestora', 'pass_gestora'),
        'CNS': ('user_cns', 'pass_cns'),
        'Subsidios SEDEM': ('user_sedem', 'pass_sedem'),
        'Aduana': ('user_aduana', 'pass_aduana'),
        'Firma Digital': ('user_firma', 'pin_firma'),
    }
    for portal, (user_field, pass_field) in mapeo.items():
        user_val = form.cleaned_data.get(user_field)
        pass_val = form.cleaned_data.get(pass_field)
        if user_val or pass_val:
            cred, created = CredencialCliente.objects.get_or_create(
                cliente=cliente, portal=portal,
                defaults={'usuario': user_val, 'password': pass_val}
            )
            if not created:
                cred.usuario = user_val
                cred.password = pass_val
                cred.save()

# --- VISTA PRINCIPAL ---
@login_required
def lista_clientes(request):
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('buscar', '')
    accion = request.GET.get('accion', '')
    cliente_id = request.GET.get('id')

    clientes = Cliente.objects.prefetch_related('credenciales').all().order_by('razon_social')
    if estado_filtro:
        clientes = clientes.filter(estado_cliente=estado_filtro)
    if busqueda:
        clientes = clientes.filter(Q(razon_social__icontains=busqueda) | Q(nit__icontains=busqueda))

    cliente_editar = None
    if cliente_id:
        cliente_editar = get_object_or_404(Cliente, id=cliente_id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente_editar)
        if form.is_valid():
            cliente_guardado = form.save()
            guardar_credenciales(cliente_guardado, form)
            messages.success(request, "Cliente guardado exitosamente.")
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente_editar)

    mostrar_formulario = accion in ['nuevo', 'editar']

    return render(request, 'clientes/lista.html', {
        'clientes': clientes,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'form': form,
        'mostrar_formulario': mostrar_formulario,
        'accion': accion,
        'cliente_editar': cliente_editar
    })

# --- VISTAS DE APOYO ---
@login_required
def crear_cliente(request):
    return redirect('/clientes/?accion=nuevo')

@login_required
def editar_cliente(request, id):
    return redirect(f'/clientes/?accion=editar&id={id}')

@login_required
def eliminar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.delete()
    messages.success(request, "Cliente eliminado exitosamente.")
    return redirect('lista_clientes')

# --- VISTA DE DESCARGAR PLANTILLA (CON EJEMPLO Y EN EL ORDEN SOLICITADO) ---
@login_required
def descargar_plantilla(request):
    # Definimos exactamente el orden solicitado
    columnas = [
        'NIT', 'Razón Social',
        'Usuario SIN', 'Contraseña SIN',
        'Usuario Gestora', 'Contraseña Gestora',
        'Usuario Caja Salud', 'Contraseña Caja Salud',
        'Usuario SEDEM', 'Contraseña SEDEM',
        'Usuario Aduana', 'Contraseña Aduana',
        'Usuario Firma Digital', 'PIN Firma Digital',
        'Estado Cliente', 'Tipo Empresa', 'Tipo Sociedad', 'Rubro', 'Tipo Servicio',
        'Dirección', 'Teléfono', 'Email Empresa', 'Pass Email Empresa',
        'Honorarios (Bs)', 'Cierre Gestión', 'Caja Salud (Aporta)', 'Nro. Patronal', 'Habilitado Cobro',
        'Representante Legal', 'Email Rep. Legal',
        'Contacto Nombre', 'Contacto Cargo', 'Contacto Email', 'Contacto Celular'
    ]
    
    # Datos de ejemplo
    ejemplo = [{
        'NIT': '123456789',
        'Razón Social': 'EMPRESA DE EJEMPLO S.R.L.',
        'Usuario SIN': 'user_sin_123',
        'Contraseña SIN': 'pass_sin_123',
        'Usuario Gestora': 'user_gestora_123',
        'Contraseña Gestora': 'pass_gestora_123',
        'Usuario Caja Salud': 'user_cns_123',
        'Contraseña Caja Salud': 'pass_cns_123',
        'Usuario SEDEM': 'user_sedem_123',
        'Contraseña SEDEM': 'pass_sedem_123',
        'Usuario Aduana': 'user_aduana_123',
        'Contraseña Aduana': 'pass_aduana_123',
        'Usuario Firma Digital': 'user_firma_123',
        'PIN Firma Digital': 'pin_firma_123',
        'Estado Cliente': 'activo',
        'Tipo Empresa': 'S.R.L.',
        'Tipo Sociedad': 'Responsabilidad Limitada',
        'Rubro': 'Comercial',
        'Tipo Servicio': 'Contabilidad',
        'Dirección': 'Av. Principal #123',
        'Teléfono': '333-4444',
        'Email Empresa': 'contacto@empresa.com',
        'Pass Email Empresa': 'pass_email_123',
        'Honorarios (Bs)': 1500.00,
        'Cierre Gestión': 'Diciembre',
        'Caja Salud (Aporta)': 'CNS',
        'Nro. Patronal': '12-345-67',
        'Habilitado Cobro': 'Sí',
        'Representante Legal': 'JUAN PEREZ',
        'Email Rep. Legal': 'juan@empresa.com',
        'Contacto Nombre': 'MARIA LOPEZ',
        'Contacto Cargo': 'Contadora',
        'Contacto Email': 'maria@empresa.com',
        'Contacto Celular': '777-8888'
    }]
    
    df = pd.DataFrame(ejemplo, columns=columnas)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Plantilla_Clientes.xlsx"'
    df.to_excel(response, index=False)
    return response

# --- VISTA DE IMPORTAR EXCEL (LECTURA EN EL ORDEN CORRECTO Y SIN PESTAÑAS) ---
@login_required
def importar_clientes(request):
    if request.method == 'POST':
        # Aceptamos el nombre del input del base.html o el de la lista
        archivo_excel = request.FILES.get('archivo_excel') or request.FILES.get('excel_file')
        
        if not archivo_excel:
            messages.error(request, "Por favor, selecciona un archivo Excel.")
            return redirect('lista_clientes') # CORREGIDO: Devuelve a la lista
        
        try:
            df = pd.read_excel(archivo_excel)
            
            for index, row in df.iterrows():
                if pd.isna(row.get('NIT')):
                    continue
                
                nit = str(row.get('NIT')).strip()
                if nit == 'nan' or not nit:
                    continue

                # 1. Guardar o actualizar Cliente
                cliente, created = Cliente.objects.update_or_create(
                    nit=nit,
                    defaults={
                        'razon_social': str(row.get('Razón Social', '')).strip() if not pd.isna(row.get('Razón Social')) else '',
                        'estado_cliente': str(row.get('Estado Cliente', 'activo')).strip().lower(),
                        'tipo_empresa': str(row.get('Tipo Empresa', '')).strip() if not pd.isna(row.get('Tipo Empresa')) else '',
                        'tipo_sociedad': str(row.get('Tipo Sociedad', '')).strip() if not pd.isna(row.get('Tipo Sociedad')) else '',
                        'rubro_actividad': str(row.get('Rubro', '')).strip() if not pd.isna(row.get('Rubro')) else '',
                        'tipo_servicio': str(row.get('Tipo Servicio', '')).strip() if not pd.isna(row.get('Tipo Servicio')) else '',
                        'direccion': str(row.get('Dirección', '')).strip() if not pd.isna(row.get('Dirección')) else '',
                        'telefono': str(row.get('Teléfono', '')).strip() if not pd.isna(row.get('Teléfono')) else '',
                        'email': str(row.get('Email Empresa', '')).strip() if not pd.isna(row.get('Email Empresa')) else '',
                        'password_email_empresa': str(row.get('Pass Email Empresa', '')).strip() if not pd.isna(row.get('Pass Email Empresa')) else '',
                        'honorarios_mensuales': float(row.get('Honorarios (Bs)', 0.00)) if not pd.isna(row.get('Honorarios (Bs)')) else 0.00,
                        'cierre_gestion': str(row.get('Cierre Gestión', '')).strip() if not pd.isna(row.get('Cierre Gestión')) else '',
                        'tipo_caja_salud': str(row.get('Caja Salud (Aporta)', '')).strip() if not pd.isna(row.get('Caja Salud (Aporta)')) else '',
                        'numero_patronal': str(row.get('Nro. Patronal', '')).strip() if not pd.isna(row.get('Nro. Patronal')) else '',
                        'habilitado_para_cobro': True if str(row.get('Habilitado Cobro', 'Sí')).strip().lower() in ['sí', 'si', 'true', '1'] else False,
                        'representante_legal': str(row.get('Representante Legal', '')).strip() if not pd.isna(row.get('Representante Legal')) else '',
                        'rep_legal_email': str(row.get('Email Rep. Legal', '')).strip() if not pd.isna(row.get('Email Rep. Legal')) else '',
                        'contacto_nombre': str(row.get('Contacto Nombre', '')).strip() if not pd.isna(row.get('Contacto Nombre')) else '',
                        'contacto_cargo': str(row.get('Contacto Cargo', '')).strip() if not pd.isna(row.get('Contacto Cargo')) else '',
                        'contacto_email': str(row.get('Contacto Email', '')).strip() if not pd.isna(row.get('Contacto Email')) else '',
                        'contacto_celular': str(row.get('Contacto Celular', '')).strip() if not pd.isna(row.get('Contacto Celular')) else '',
                    }
                )

                # 2. Guardar Credenciales
                credenciales_mapping = {
                    'SIN': ('Usuario SIN', 'Contraseña SIN'),
                    'Gestora Pública': ('Usuario Gestora', 'Contraseña Gestora'),
                    'CNS': ('Usuario Caja Salud', 'Contraseña Caja Salud'),
                    'Subsidios SEDEM': ('Usuario SEDEM', 'Contraseña SEDEM'),
                    'Aduana': ('Usuario Aduana', 'Contraseña Aduana'),
                    'Firma Digital': ('Usuario Firma Digital', 'PIN Firma Digital'),
                }

                for portal, (col_user, col_pass) in credenciales_mapping.items():
                    u_val = str(row.get(col_user, '')).strip() if not pd.isna(row.get(col_user)) else ''
                    p_val = str(row.get(col_pass, '')).strip() if not pd.isna(row.get(col_pass)) else ''
                    
                    if u_val or p_val:
                        cred, c_created = CredencialCliente.objects.get_or_create(cliente=cliente, portal=portal)
                        cred.usuario = u_val
                        cred.password = p_val
                        cred.save()

            messages.success(request, "¡Clientes importados correctamente!")
            return redirect('lista_clientes') # CORREGIDO: Devuelve a la lista
            
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return redirect('lista_clientes') # CORREGIDO: Devuelve a la lista si hay error
            
    # SI ALGUIEN ENTRA A LA URL POR ERROR (GET), LO REGRESA A LA LISTA
    return redirect('lista_clientes') # CORREGIDO: Ya no renderiza el HTML

# --- VISTA DE EXPORTAR EXCEL (EN EL MISMO ORDEN) ---
@login_required
def exportar_clientes_excel(request):
    clientes = Cliente.objects.prefetch_related('credenciales').all()
    data = []
    
    for c in clientes:
        # Buscar credenciales del cliente
        creds = {cred.portal: cred for cred in c.credenciales.all()}
        
        def get_cred(portal, field):
            cred = creds.get(portal)
            if cred:
                return cred.usuario if field == 'user' else cred.password
            return ''

        data.append({
            'NIT': c.nit,
            'Razón Social': c.razon_social,
            'Usuario SIN': get_cred('SIN', 'user'),
            'Contraseña SIN': get_cred('SIN', 'pass'),
            'Usuario Gestora': get_cred('Gestora Pública', 'user'),
            'Contraseña Gestora': get_cred('Gestora Pública', 'pass'),
            'Usuario Caja Salud': get_cred('CNS', 'user'),
            'Contraseña Caja Salud': get_cred('CNS', 'pass'),
            'Usuario SEDEM': get_cred('Subsidios SEDEM', 'user'),
            'Contraseña SEDEM': get_cred('Subsidios SEDEM', 'pass'),
            'Usuario Aduana': get_cred('Aduana', 'user'),
            'Contraseña Aduana': get_cred('Aduana', 'pass'),
            'Usuario Firma Digital': get_cred('Firma Digital', 'user'),
            'PIN Firma Digital': get_cred('Firma Digital', 'pass'),
            'Estado Cliente': c.estado_cliente,
            'Tipo Empresa': c.tipo_empresa,
            'Tipo Sociedad': c.tipo_sociedad,
            'Rubro': c.rubro_actividad,
            'Tipo Servicio': c.tipo_servicio,
            'Dirección': c.direccion,
            'Teléfono': c.telefono,
            'Email Empresa': c.email,
            'Pass Email Empresa': c.password_email_empresa,
            'Honorarios (Bs)': c.honorarios_mensuales,
            'Cierre Gestión': c.cierre_gestion,
            'Caja Salud (Aporta)': c.tipo_caja_salud,
            'Nro. Patronal': c.numero_patronal,
            'Habilitado Cobro': 'Sí' if c.habilitado_para_cobro else 'No',
            'Representante Legal': c.representante_legal,
            'Email Rep. Legal': c.rep_legal_email,
            'Contacto Nombre': c.contacto_nombre,
            'Contacto Cargo': c.contacto_cargo,
            'Contacto Email': c.contacto_email,
            'Contacto Celular': c.contacto_celular,
        })
    
    df = pd.DataFrame(data)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Clientes_Exportados.xlsx"'
    df.to_excel(response, index=False)
    return response