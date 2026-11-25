import os
import unicodedata
import pandas as pd
import io
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

def leer_excel(archivo_excel):
    xls = pd.ExcelFile(archivo_excel)
    for hoja in xls.sheet_names:
        for hr in range(0, 10):
            try:
                temp = pd.read_excel(archivo_excel, sheet_name=hoja, header=hr, nrows=5)
                cols = [str(c).strip().lower() for c in temp.columns]
                if "codigo" in cols and "saldo" in cols:
                    df = pd.read_excel(archivo_excel, sheet_name=hoja, header=hr, dtype=str)
                    df.columns = [str(c).strip() for c in df.columns]
                    return df
            except Exception:
                continue
    raise ValueError("No se encontró una hoja que contenga las columnas 'CODIGO' y 'Saldo'.")

def procesar_saldos_negativos(archivo_excel):
    try:
        df = leer_excel(archivo_excel)
    except Exception as e:
        raise ValueError(str(e))

    def norm(s):
        s = str(s).strip().lower()
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    
    col_map = {norm(c): c for c in df.columns}
    def col(n):
        n = norm(n)
        if n in col_map: return col_map[n]
        for k, v in col_map.items():
            if n in k: return v
        return None

    C_COD = col("CODIGO")
    C_ALM = col("Almacen")
    C_FEC = col("Fecha")
    C_ING = col("Ingresos")
    C_SAL = col("Salidas")

    for n, c in [("CODIGO", C_COD), ("Almacen", C_ALM), ("Fecha", C_FEC), ("Ingresos", C_ING), ("Salidas", C_SAL)]:
        if not c:
            raise ValueError(f"Falta la columna '{n}' en el archivo Excel. Columnas detectadas: {list(df.columns)}")

    # Preparar campos
    df["__ord__"] = range(len(df))
    df["__dia__"] = df[C_FEC].astype(str).str.strip().str.split(" ").str[0]
    df[C_ING] = pd.to_numeric(df[C_ING], errors="coerce").fillna(0)
    df[C_SAL] = pd.to_numeric(df[C_SAL], errors="coerce").fillna(0)
    df["__neto__"] = df[C_ING] - df[C_SAL]
    df["__es_ing__"] = df["__neto__"] > 0

    # Reordenar
    df_ord = df.sort_values(
        [C_COD, C_ALM, "__dia__", "__es_ing__", "__ord__"],
        ascending=[True, True, True, False, True],
    ).reset_index(drop=True)

    # Recalcular saldo
    df_ord["SALDO_CALC"] = df_ord.groupby([C_COD, C_ALM], sort=False)["__neto__"].cumsum()
    df_ord["NEGATIVO"] = df_ord["SALDO_CALC"].apply(lambda x: "SI" if pd.notna(x) and x < 0 else "")

    # Volver al orden original
    df = df.merge(df_ord[["__ord__", "SALDO_CALC", "NEGATIVO"]], on="__ord__", how="left").sort_values("__ord__").reset_index(drop=True)
    
    # Limpiar columnas temporales
    df_out = df.drop(columns=["__ord__", "__dia__", "__neto__", "__es_ing__"])

    # Guardar en memoria
    output = io.BytesIO()
    df_out.to_excel(output, index=False, sheet_name="KARDEX")
    output.seek(0)

    # Volver a abrir con openpyxl para pintar
    wb = load_workbook(output)
    ws = wb["KARDEX"]
    hdrs = [c.value for c in ws[1]]
    
    if "NEGATIVO" not in hdrs:
        raise ValueError("Error interno: no se generó la columna NEGATIVO.")
        
    cn = hdrs.index("NEGATIVO") + 1
    nc = ws.max_column

    fr = PatternFill("solid", start_color="FFC7CE")
    fnt = Font(color="9C0006", bold=True)

    cnt = 0
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=cn).value == "SI":
            cnt += 1
            for ci in range(1, nc + 1):
                c = ws.cell(row=r, column=ci)
                c.fill = fr
                c.font = fnt

    for ci in range(1, nc + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 16

    # Guardar el archivo final en otro stream
    output_final = io.BytesIO()
    wb.save(output_final)
    output_final.seek(0)
    
    return output_final, cnt