import os
import tempfile
import pandas as pd
from django.template.loader import render_to_string
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright
import re
import qrcode
from io import BytesIO
import base64
from PIL import Image

def limpiar_texto(texto):
    if not isinstance(texto, str): return texto
    texto = texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return re.sub(r'\s+', ' ', texto).strip()

def generar_qr_base64(datos):
    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
    qr.add_data(datos)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3: hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def es_color_oscuro(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128

def oscurecer_color(hex_color, factor=0.7):
    r, g, b = hex_to_rgb(hex_color)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

def imagen_a_base64(image_field):
    if not image_field: return None
    try:
        img = Image.open(image_field.path)
        img.thumbnail((150, 150), Image.LANCZOS)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except Exception:
        return None

def generar_boletas_desde_excel(excel_path, configuracion):
    texto_cabecera = 'white' if es_color_oscuro(configuracion.color_cabecera) else '#1a202c'
    texto_tabla = 'white' if es_color_oscuro(configuracion.color_tabla) else '#1a202c'
    texto_neto = 'white' if es_color_oscuro(configuracion.color_neto) else '#1d4a2e'
    
    oscuro_cabecera = oscurecer_color(configuracion.color_cabecera)
    oscuro_tabla = oscurecer_color(configuracion.color_tabla)
    oscuro_neto = oscurecer_color(configuracion.color_neto)
    
    df = pd.read_excel(excel_path, sheet_name="TABLA", engine="openpyxl")
    if df.empty: raise ValueError("El Excel está vacío o no tiene la hoja 'TABLA'")
    
    df.columns = df.columns.str.strip()
    output_dir = tempfile.mkdtemp()
    pdf_list = []
    logo_base64 = imagen_a_base64(configuracion.logo)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1200, 'height': 900})
        
        for i, row in df.iterrows():
            ctx = row.to_dict()
            for k, v in ctx.items():
                if pd.isna(v): ctx[k] = ""; continue
                if isinstance(v, pd.Timestamp): ctx[k] = v.strftime("%d/%m/%Y"); continue
                valor = str(v)
                if k in ['NIT', 'NRO']: ctx[k] = re.sub(r'[^0-9]', '', valor); continue
                if k in ['Nombre', 'CI', 'Cargo', 'EMPRESA', 'MES']: ctx[k] = limpiar_texto(valor); continue
                if isinstance(v, (int, float)):
                    ctx[k] = str(int(v)) if k == 'Dias_Trabajados' else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                else: ctx[k] = limpiar_texto(valor)
            
            ctx.update({
                'color_cabecera': configuracion.color_cabecera,
                'color_tabla': configuracion.color_tabla,
                'color_neto': configuracion.color_neto,
                'texto_cabecera': texto_cabecera,
                'texto_tabla': texto_tabla,
                'texto_neto': texto_neto,
                'degradado': configuracion.degradado,
                'oscuro_cabecera': oscuro_cabecera,
                'oscuro_tabla': oscuro_tabla,
                'oscuro_neto': oscuro_neto,
                'LOGO': logo_base64,
            })
            
            datos_qr = f"BOLETA\nEMPRESA: {ctx.get('EMPRESA', '')}\nNIT: {ctx.get('NIT', '')}\nNRO: {ctx.get('NRO', '')}\nTRABAJADOR: {ctx.get('Nombre', '')}\nNETO: Bs. {ctx.get('Sueldo_N', '')}"
            ctx['QR_IMG'] = generar_qr_base64(datos_qr)
            
            # Renderiza el HTML usando Django
            html_content = render_to_string('boletas/plantilla_boleta.html', ctx)
            
            pdf_file = os.path.join(output_dir, f"boleta_{i+1}.pdf")
            page.set_content(html_content)
            page.pdf(path=pdf_file, format='Letter', landscape=True, print_background=True, margin={'top': '6mm', 'bottom': '6mm', 'left': '8mm', 'right': '8mm'})
            pdf_list.append(pdf_file)
        
        browser.close()
    
    merger = PdfMerger()
    for pdf in pdf_list: merger.append(pdf)
    
    final_pdf = os.path.join(output_dir, "BOLETAS_GENERADAS.pdf")
    with open(final_pdf, "wb") as f: merger.write(f)
    merger.close()
    
    return final_pdf