import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import os

def normalizar_numero(valor):
    if not valor:
        return ""
    valor = str(valor).strip()
    valor = re.sub(r"[^\d,\.]", "", valor)

    if "," in valor and "." in valor:
        coma_pos = valor.rfind(",")
        punto_pos = valor.rfind(".")
        if punto_pos < coma_pos:
            return valor
        else:
            valor = valor.replace(",", "X").replace(".", ",").replace("X", ".")
            return valor
    elif "." in valor:
        partes = valor.split(".")
        if len(partes[-1]) > 2:
            valor = valor.replace(".", ",")
        else:
            valor = ".".join(partes[:-1]) + "," + partes[-1]
        return valor
    elif "," in valor:
        return valor
    return valor

def extraer_datos_pdf(archivo_pdf, nombre_archivo):
    """Extrae datos de un archivo PDF cargado en memoria."""
    detalles = []
    
    with pdfplumber.open(archivo_pdf) as pdf:
        texto = "\n".join([p.extract_text() or "" for p in pdf.pages])

        def buscar(patron, default=""):
            m = re.search(patron, texto, re.IGNORECASE)
            return m.group(1).strip() if m else default

        empresa = buscar(r"([A-ZÁÉÍÓÚÑ\s]+S\.R\.L\.)", "Desconocido")
        nit_empresa = buscar(r"NIT[:\s]+([\d-]+)")
        fecha = buscar(r"Fecha[:\s]+([\d/:\sAPM]+)")
        razon_social = buscar(r'Nombre/?Razón Social[:\s"]+([\w\s\.\-&]+S\.R\.L\.)')
        nit_cliente = buscar(r"NIT/CI\/CEX[:\s]+([\d-]+)")
        nro_factura = buscar(r"FACTURA N°[:\s]+([\d-]+)")

        cod_auto = buscar(r"CÓD\.?\s*AUTORIZACIÓN\s+([\w\s-]+)")
        cod_auto = cod_auto.replace("\n", "").replace(" ", "")

        for page in pdf.pages:
            tabla = page.extract_table()
            if tabla:
                for fila in tabla[1:]:
                    if len(fila) >= 7 and fila[0]:
                        cantidad = normalizar_numero(fila[1])
                        precio_unitario = normalizar_numero(fila[4])
                        descuento = normalizar_numero(fila[5])
                        subtotal = normalizar_numero(fila[6])

                        detalles.append({
                            "fecha": fecha,
                            "nro_factura": nro_factura,
                            "cod_autorizacion": cod_auto,
                            "cliente": razon_social,
                            "nit_cliente": nit_cliente,
                            "empresa": empresa,
                            "nit_empresa": nit_empresa,
                            "codigo": str(fila[0]).strip(),
                            "cantidad": cantidad,
                            "unidad": str(fila[2]).strip(),
                            "descripcion": str(fila[3]).strip(),
                            "precio_unitario": precio_unitario,
                            "descuento": descuento,
                            "subtotal": subtotal,
                            "archivo_origen": nombre_archivo
                        })
    return detalles

def procesar_pdfs_facturas(archivos_pdf):
    """Procesa una lista de archivos y devuelve el Excel en memoria."""
    todos_datos = []

    for archivo in archivos_pdf:
        try:
            datos = extraer_datos_pdf(archivo, archivo.name)
            todos_datos.extend(datos)
        except Exception as e:
            print(f"Error procesando {archivo.name}: {e}")

    df = pd.DataFrame(todos_datos)

    if df.empty:
        raise ValueError("No se extrajeron datos de los archivos PDF. Verifica que sean facturas válidas.")

    # Crear el archivo Excel en memoria
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Facturas')
        worksheet = writer.sheets['Facturas']
        worksheet.set_column(0, len(df.columns) - 1, 25)
    
    output.seek(0)
    return output, len(archivos_pdf), len(df)