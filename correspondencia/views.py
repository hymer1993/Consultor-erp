from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils import timezone
from django.conf import settings # <-- NUEVO
from .models import ControlCorrespondencia
from .forms import CorrespondenciaForm
from clientes.models import Cliente
from playwright.sync_api import sync_playwright
import io
import os # <-- NUEVO
import re
import datetime
from pypdf import PdfWriter, PdfReader

def lista_correspondencia(request):
    cartas = ControlCorrespondencia.objects.all().order_by('-gestion', '-numero')
    return render(request, 'correspondencia/lista.html', {'cartas': cartas})

def crear_correspondencia(request):
    clientes_habilitados = Cliente.objects.filter(habilitado_para_cobro=True).order_by('razon_social')
    if request.method == 'POST':
        form = CorrespondenciaForm(request.POST, request.FILES) 
        if form.is_valid():
            nueva_carta = form.save()
            return redirect('generar_pdf_carta', carta_id=nueva_carta.id)
    else:
        cliente_id = request.GET.get('cliente_id')
        if cliente_id:
            cliente_sel = get_object_or_404(Cliente, id=cliente_id)
            form = CorrespondenciaForm(initial={
                'destino': cliente_sel.razon_social, 
                'nit': cliente_sel.nit,
                'monto': cliente_sel.honorarios_mensuales, 
                'objeto': f"Cobro de Honorarios - {cliente_sel.tipo_servicio}",
                'tipo_carta': 'COBRO'
            })
        else:
            form = CorrespondenciaForm()
    return render(request, 'correspondencia/crear.html', {'form': form, 'clientes': clientes_habilitados})

def generar_pdf_carta(request, carta_id):
    carta = get_object_or_404(ControlCorrespondencia, id=carta_id)
    monto_formateado = intcomma(carta.monto) if carta.monto else "0.00"
    
    contexto = {
        'carta': carta,
        'fecha': carta.fecha.strftime('%d de %B de %Y'),
        'correlativo': f"{carta.unidad_cites} {carta.correlativo_completo}",
        'destino': carta.destino,
        'nit': carta.nit,
        'objeto': carta.objeto,
        'monto': monto_formateado,
        'numero_factura': carta.numero_factura,
        'fecha_factura': carta.fecha_factura,
    }
    
    html_string = render_to_string('correspondencia/documento.html', contexto, request=request)
    base_url = request.build_absolute_uri('/')
    html_con_base = f'<base href="{base_url}">{html_string}'

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_con_base, wait_until="networkidle")
        pdf_carta_bytes = page.pdf(format="Letter", print_background=True, margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"})
        browser.close()

    if carta.factura_pdf:
        writer = PdfWriter()
        reader_carta = PdfReader(io.BytesIO(pdf_carta_bytes))
        for page in reader_carta.pages:
            writer.add_page(page)
        reader_factura = PdfReader(carta.factura_pdf.path)
        for page in reader_factura.pages:
            writer.add_page(page)
        pdf_final_stream = io.BytesIO()
        writer.write(pdf_final_stream)
        pdf_final_stream.seek(0)
        pdf_bytes_finales = pdf_final_stream.getvalue()
    else:
        pdf_bytes_finales = pdf_carta_bytes

    response = HttpResponse(pdf_bytes_finales, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Carta_{carta.id}.pdf"'
    return response

def generacion_masiva(request):
    clientes = Cliente.objects.filter(habilitado_para_cobro=True).order_by('razon_social')
    hoy = timezone.localdate()
    
    if request.method == 'POST':
        tipo_carta = request.POST.get('tipo_carta')
        fecha_carta_str = request.POST.get('fecha_carta') 
        
        try:
            fecha_carta_obj = datetime.datetime.strptime(fecha_carta_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_carta_obj = hoy

        clientes_ids = request.POST.getlist('clientes_seleccionados')
        archivos_subidos = request.FILES.getlist('facturas_pdf')
        
        if not clientes_ids:
            return render(request, 'correspondencia/masiva.html', {'clientes': clientes, 'hoy': hoy, 'error': 'Debes seleccionar al menos un cliente.'})

        facturas_dict = {}
        for archivo in archivos_subidos:
            nombre_limpio = archivo.name.replace('.pdf', '').replace('.PDF', '').strip()
            facturas_dict[nombre_limpio.upper()] = {
                'archivo': archivo,
                'nombre_original': nombre_limpio
            }

        carpeta_destino = os.path.join(settings.MEDIA_ROOT, 'cobranzas_generadas')
        os.makedirs(carpeta_destino, exist_ok=True)
        
        archivos_generados = [] 
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            for c_id in clientes_ids:
                cliente = get_object_or_404(Cliente, id=c_id)
                
                servicio = cliente.tipo_servicio if cliente.tipo_servicio else "Servicios Profesionales"
                objeto_texto = f"Cobro de Honorarios - {servicio}"
                
                archivo_factura_encontrado = None
                nombre_original_factura = ""
                numero_factura_extraido = "S/N"

                for nombre_archivo, data in facturas_dict.items():
                    if cliente.razon_social.upper() in nombre_archivo or str(cliente.nit) in nombre_archivo:
                        archivo_factura_encontrado = data['archivo']
                        nombre_original_factura = data['nombre_original']
                        match = re.search(r'(FACT[-\s]?\d+|\b\d+\b)', nombre_original_factura.upper())
                        if match:
                            numero_factura_extraido = match.group(1)
                        break

                # CORRECCIÓN AQUÍ: Guardamos el archivo de la factura en la base de datos
                nueva_carta = ControlCorrespondencia.objects.create(
                    tipo_carta=tipo_carta,
                    fecha=fecha_carta_obj,
                    destino=cliente.razon_social,
                    nit=cliente.nit,
                    monto=cliente.honorarios_mensuales,
                    objeto=objeto_texto,
                    numero_factura=numero_factura_extraido,
                    fecha_factura=fecha_carta_obj,
                    factura_pdf=archivo_factura_encontrado # <-- ESTO FALTABA
                )
                
                contexto = {
                    'carta': nueva_carta,
                    'fecha': nueva_carta.fecha.strftime('%d de %B de %Y'),
                    'correlativo': f"{nueva_carta.unidad_cites} {nueva_carta.correlativo_completo}",
                    'destino': nueva_carta.destino,
                    'nit': nueva_carta.nit,
                    'objeto': nueva_carta.objeto,
                    'monto': intcomma(nueva_carta.monto),
                    'numero_factura': nueva_carta.numero_factura,
                    'fecha_factura': nueva_carta.fecha_factura,
                }
                
                html_string = render_to_string('correspondencia/documento.html', contexto, request=request)
                base_url = request.build_absolute_uri('/')
                html_con_base = f'<base href="{base_url}">{html_string}'
                
                page.set_content(html_con_base, wait_until="networkidle")
                pdf_carta_bytes = page.pdf(format="Letter", print_background=True, margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"})
                
                if archivo_factura_encontrado:
                    writer = PdfWriter()
                    reader_carta = PdfReader(io.BytesIO(pdf_carta_bytes))
                    for p_carta in reader_carta.pages:
                        writer.add_page(p_carta)
                        
                    archivo_factura_encontrado.seek(0) # Volver al inicio del archivo para leerlo
                    reader_factura = PdfReader(archivo_factura_encontrado)
                    for p_factura in reader_factura.pages:
                        writer.add_page(p_factura)
                        
                    pdf_final_stream = io.BytesIO()
                    writer.write(pdf_final_stream)
                    pdf_final_stream.seek(0)
                    pdf_bytes_finales = pdf_final_stream.getvalue()
                    
                    nombre_salida = f"Cobranza {nombre_original_factura}.pdf"
                else:
                    pdf_bytes_finales = pdf_carta_bytes
                    nombre_salida = f"Cobranza_SinFactura_{cliente.nit}.pdf"
                
                ruta_completa_archivo = os.path.join(carpeta_destino, nombre_salida)
                with open(ruta_completa_archivo, 'wb') as f:
                    f.write(pdf_bytes_finales)
                
                archivos_generados.append({
                    'nombre': nombre_salida,
                    'url': f"{settings.MEDIA_URL}cobranzas_generadas/{nombre_salida}"
                })
            
            browser.close()

        return render(request, 'correspondencia/masiva.html', {
            'clientes': clientes, 
            'hoy': hoy, 
            'archivos_generados': archivos_generados,
            'mensaje_exito': f'¡Se generaron {len(archivos_generados)} PDFs correctamente!'
        })

    return render(request, 'correspondencia/masiva.html', {'clientes': clientes, 'hoy': hoy})