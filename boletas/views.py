from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from .models import ConfiguracionBoleta
from clientes.models import Cliente
from .utils import generar_boletas_desde_excel
import os
import tempfile
from .utils_pdf import procesar_pdfs_facturas

# --- IMPORTACIONES PARA LA VISTA PREVIA ---
import base64
import qrcode
from io import BytesIO
from PIL import Image

# --- IMPORTACIONES PARA LAS NUEVAS HERRAMIENTAS (EXCEL) ---
from .utils_traspasos import procesar_traspasos
from .utils_negativos import procesar_saldos_negativos

# =====================================================================
# 1. VISTA PRINCIPAL (LISTA DE CLIENTES + CONFIGURACIÓN + GENERAR BOLETAS)
# =====================================================================
@login_required
def lista_clientes_boletas(request):
    # 1. Atrapamos los filtros y búsquedas
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('buscar', '')
    
    # 2. Atrapamos qué cliente estamos seleccionando y qué acción queremos hacer
    accion = request.GET.get('accion', '') # 'configurar' o vacío (ver)
    cliente_id = request.GET.get('id')
    
    # 3. Traemos a todos los clientes
    clientes = Cliente.objects.prefetch_related('config_boleta').all().order_by('razon_social')
    
    if estado_filtro:
        clientes = clientes.filter(estado_cliente=estado_filtro)
    if busqueda:
        clientes = clientes.filter(razon_social__icontains=busqueda)

    # 4. Si hay un cliente seleccionado, buscamos o creamos su configuración
    cliente_editar = None
    config = None
    if cliente_id:
        cliente_editar = get_object_or_404(Cliente, id=cliente_id)
        config, created = ConfiguracionBoleta.objects.get_or_create(cliente=cliente_editar)

    # 5. PROCESAMIENTO DE FORMULARIOS (POST)
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # A) GUARDAR CONFIGURACIÓN (Colores y Logo)
        if form_type == 'configurar' and config:
            config.color_cabecera = request.POST.get('color_cabecera', '#0b2b5c')
            config.color_tabla = request.POST.get('color_tabla', '#0b2b5c')
            config.color_neto = request.POST.get('color_neto', '#eaf6ed')
            config.degradado = 'degradado' in request.POST
            
            if 'logo' in request.FILES:
                config.logo = request.FILES['logo']
                
            config.save()
            messages.success(request, f"Configuración guardada exitosamente para {cliente_editar.razon_social}.")
            return redirect(f'/herramientas/?id={cliente_id}')
            
        # B) GENERAR PDF DESDE EXCEL (BOLETAS DE PAGO)
        elif form_type == 'generar' and config:
            excel_file = request.FILES.get('excel_file')
            
            if not excel_file:
                messages.error(request, "Debes seleccionar un archivo Excel.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    for chunk in excel_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                
                try:
                    pdf_path = generar_boletas_desde_excel(tmp_path, config)
                    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Boletas_{cliente_editar.razon_social}.pdf"'
                    return response
                except Exception as e:
                    messages.error(request, f"Error al generar PDF: {str(e)}")
                finally:
                    if os.path.exists(tmp_path): 
                        os.remove(tmp_path)
            
            return redirect(f'/herramientas/?id={cliente_id}&accion=configurar')

    # 6. Enviamos todo al HTML principal
    return render(request, 'boletas/lista_clientes.html', {
        'clientes': clientes,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'accion': accion,
        'cliente_editar': cliente_editar,
        'config': config
    })


# =====================================================================
# 2. VISTA PARA LA VISTA PREVIA DE LA BOLETA (SE CARGA EN EL IFRAME)
# =====================================================================
@login_required
def preview_boleta(request, cliente_id):
    """Renderiza SOLO la plantilla de la boleta para mostrarla en el iframe."""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    config, created = ConfiguracionBoleta.objects.get_or_create(cliente=cliente)
    
    # Permite cambiar colores en tiempo real por la URL
    color_cabecera = request.GET.get('color_cabecera', config.color_cabecera)
    color_tabla = request.GET.get('color_tabla', config.color_tabla)
    color_neto = request.GET.get('color_neto', config.color_neto)
    
    # Lógica de contraste (texto blanco o negro según el fondo)
    def es_color_oscuro(hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3: hex_color = ''.join([c*2 for c in hex_color])
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 128

    texto_cabecera = 'white' if es_color_oscuro(color_cabecera) else '#1a202c'
    texto_tabla = 'white' if es_color_oscuro(color_tabla) else '#1a202c'
    texto_neto = 'white' if es_color_oscuro(color_neto) else '#1d4a2e'
    
    # Convertir Logo a Base64
    logo_base64 = None
    if config.logo:
        try:
            img = Image.open(config.logo.path)
            img.thumbnail((150, 150), Image.LANCZOS)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            logo_base64 = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        except Exception:
            pass

    # Generar QR de prueba
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data("BOLETA DE PRUEBA - VISTA PREVIA")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffered_qr = BytesIO()
    img_qr.save(buffered_qr, format="PNG")
    qr_base64 = f"data:image/png;base64,{base64.b64encode(buffered_qr.getvalue()).decode()}"

    # Datos ficticios para la simulación
    context = {
        'EMPRESA': cliente.razon_social, 
        'NIT': cliente.nit, 
        'MES': 'OCTUBRE', 
        'NRO': '1', 
        'LOGO': logo_base64, 
        'Nombre': 'JUAN PEREZ', 
        'CI': '12345678', 
        'Cargo': 'CONTADOR',
        'Fecha_Ingreso': '01/01/2023', 
        'Dias_Trabajados': '30', 
        'Sueldos_B': '2.500,00',
        'Bono_Ant': '0,00', 
        'Otros_B': '200,00', 
        'Tota_I': '2.700,00', 
        'Afp_lab': '300,00',
        'Rc_iva': '0,00', 
        'Anti': '0,00', 
        'Total_E': '300,00', 
        'Sueldo_N': '2.400,00',
        'QR_IMG': qr_base64,
        'color_cabecera': color_cabecera, 
        'color_tabla': color_tabla, 
        'color_neto': color_neto,
        'texto_cabecera': texto_cabecera, 
        'texto_tabla': texto_tabla, 
        'texto_neto': texto_neto,
    }
    return render(request, 'boletas/preview_boleta.html', context)


# =====================================================================
# 3. VISTA PARA ASIENTOS DE TRASPASOS (EXCEL)
# =====================================================================
@login_required
def vista_traspasos(request):
    """Vista para generar el asiento de traspasos entre almacenes."""
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        num_inicio = int(request.POST.get('num_inicio', 1))
        
        if not excel_file:
            messages.error(request, "Debes subir un archivo Excel.")
        else:
            try:
                # Llamamos a la lógica adaptada del script de traspasos
                output = procesar_traspasos(excel_file, num_inicio)
                
                # Devolvemos el archivo Excel procesado para descargar
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = 'attachment; filename="Resultado_Traspasos.xlsx"'
                return response
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
                
    return render(request, 'boletas/traspasos.html')

@login_required
def vista_extraer_pdf(request):
    """Vista para extraer datos de facturas PDF."""
    if request.method == 'POST':
        archivos_pdf = request.FILES.getlist('pdf_files')
        
        if not archivos_pdf:
            messages.error(request, "Debes seleccionar al menos un archivo PDF.")
        else:
            try:
                # Procesamos los PDFs
                output_excel, num_pdfs, num_filas = procesar_pdfs_facturas(archivos_pdf)
                
                # Preparamos la descarga
                response = HttpResponse(
                    output_excel.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="Facturas_Extraidas.xlsx"'
                return response
                
            except Exception as e:
                messages.error(request, f"Error al procesar: {str(e)}")
                
    return render(request, 'boletas/extraer_pdf.html')


# =====================================================================
# 4. VISTA PARA DETECTAR SALDOS NEGATIVOS (EXCEL)
# =====================================================================
@login_required
def vista_saldos_negativos(request):
    """Vista para detectar saldos negativos en el Kárdex."""
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        
        if not excel_file:
            messages.error(request, "Debes subir un archivo Excel.")
        else:
            try:
                # Procesamos el archivo (devuelve el Excel pintado y el número de filas)
                output_excel, filas_marcadas = procesar_saldos_negativos(excel_file)
                
                # Preparamos la descarga
                response = HttpResponse(
                    output_excel.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = 'attachment; filename="Reporte_Saldos_Negativos.xlsx"'
                
                # Guardamos un mensaje para cuando regrese
                messages.success(request, f"Proceso completado. Se encontraron {filas_marcadas} movimientos con saldo negativo.")
                return response
                
            except Exception as e:
                messages.error(request, f"Error al procesar: {str(e)}")
                
    return render(request, 'boletas/saldos_negativos.html')

