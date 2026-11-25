import pandas as pd
import io
import os

def procesar_traspasos(archivo_excel, num_inicio):
    try:
        # 1. Cargar datos
        reporte = pd.read_excel(archivo_excel, sheet_name="REPORTE")
        mapeo   = pd.read_excel(archivo_excel, sheet_name="CUENTA")
        tabla_ufv = pd.read_excel(archivo_excel, sheet_name="UFV", header=None)
        tabla_ufv.columns = ["Fecha", "TC", "UFV"] 
    except Exception as e:
        raise ValueError(f"Error al leer las hojas (Asegúrate de que se llamen REPORTE, CUENTA y UFV): {str(e)}")

    # 2. Limpieza y Formato
    reporte.columns = reporte.columns.str.strip()
    mapeo.columns   = mapeo.columns.str.strip()

    reporte["Fecha_dt"] = pd.to_datetime(reporte["Fecha"], dayfirst=True, errors="coerce")
    tabla_ufv["Fecha_dt"] = pd.to_datetime(tabla_ufv["Fecha"], dayfirst=True, errors="coerce")

    reporte["Fecha_str"] = reporte["Fecha_dt"].dt.strftime('%d/%m/%Y')
    tabla_ufv["Fecha_str"] = tabla_ufv["Fecha_dt"].dt.strftime('%d/%m/%Y')

    tabla_ufv["TC"] = pd.to_numeric(tabla_ufv["TC"], errors="coerce")
    tabla_ufv["UFV"] = pd.to_numeric(tabla_ufv["UFV"], errors="coerce")

    reporte = reporte.dropna(subset=["Fecha_dt"])
    tabla_ufv = tabla_ufv.dropna(subset=["Fecha_dt"])

    reporte["Almacén"] = reporte["Almacén"].astype(str).str.strip().str.upper()
    mapeo["ALMACEN"]   = mapeo["ALMACEN"].astype(str).str.strip().str.upper()

    for col in ["Ingreso Val. Bs", "Salida Val. Bs"]:
        reporte[col] = pd.to_numeric(reporte[col], errors="coerce").fillna(0.0)

    map_dict = mapeo.set_index("ALMACEN")[["CODIGO", "CUENTA"]].to_dict("index")
    reporte["CUENTA_COD"] = reporte["Almacén"].map(lambda x: map_dict.get(x, {}).get("CODIGO"))
    reporte["CUENTA_NOM"] = reporte["Almacén"].map(lambda x: map_dict.get(x, {}).get("CUENTA"))

    # 3. Agrupar
    debe = reporte[reporte["Ingreso Val. Bs"] > 0].copy().rename(columns={"Ingreso Val. Bs": "MONTO"})
    debe_g = debe.groupby(["Fecha_str", "CUENTA_COD"], as_index=False)["MONTO"].sum()
    debe_g["DEBE"], debe_g["HABER"] = debe_g["MONTO"].round(5), 0.0

    haber = reporte[reporte["Salida Val. Bs"] > 0].copy().rename(columns={"Salida Val. Bs": "MONTO"})
    haber_g = haber.groupby(["Fecha_str", "CUENTA_COD"], as_index=False)["MONTO"].sum()
    haber_g["DEBE"], haber_g["HABER"] = 0.0, haber_g["MONTO"].round(5)

    # 4. Armar asiento
    asiento = pd.concat([debe_g, haber_g], ignore_index=True)
    asiento["GLOSA"] = "TRASPASO DE PRODUCTOS ENTRE ALMACENES"

    cuentas_unicas = mapeo.drop_duplicates(subset=['CODIGO']).set_index('CODIGO')['CUENTA'].to_dict()
    asiento["CUENTA_NOM"] = asiento["CUENTA_COD"].map(cuentas_unicas).fillna("SIN NOMBRE")

    asiento = asiento.rename(columns={"CUENTA_COD": "CODIGO", "CUENTA_NOM": "CUENTA"})
    asiento = asiento[(asiento["DEBE"] != 0) | (asiento["HABER"] != 0)]

    asiento["Fecha_Orden"] = pd.to_datetime(asiento["Fecha_str"], format='%d/%m/%Y')
    asiento_out = asiento.sort_values(["Fecha_Orden", "CODIGO", "DEBE"], ascending=[True, True, False]).reset_index(drop=True)

    # 5. UFV
    tabla_ufv_limpia = tabla_ufv.drop_duplicates(subset=["Fecha_str"])
    asiento_out = pd.merge(asiento_out, tabla_ufv_limpia[["Fecha_str", "TC", "UFV"]], on="Fecha_str", how="left")
    asiento_out = asiento_out.sort_values(["Fecha_Orden", "CODIGO", "DEBE"], ascending=[True, True, False])
    
    asiento_out["UFV"] = asiento_out["UFV"].ffill().fillna(0.0)
    asiento_out["TC"] = asiento_out["TC"].ffill().fillna(6.96)

    # 6. Comprobante
    cbte_dict = {}
    current_month = None
    current_seq = num_inicio

    for date_val in asiento_out["Fecha_Orden"].dt.date.unique():
        if current_month != date_val.month:
            current_month = date_val.month
            current_seq = num_inicio
        
        mm = date_val.strftime('%m') 
        cbte_dict[date_val] = f"DI-{mm}{current_seq:04d}" 
        current_seq += 1

    asiento_out["CBTE"] = asiento_out["Fecha_Orden"].dt.date.map(cbte_dict)
    asiento_out = asiento_out.rename(columns={"Fecha_str": "Fecha"})

    # 7. Preparar descarga (BytesIO) CON LAS 4 HOJAS
    output = io.BytesIO()
    columnas_finales = ["Fecha", "CBTE", "UFV", "TC", "CODIGO", "CUENTA", "DEBE", "HABER", "GLOSA"]
    asiento_out = asiento_out[columnas_finales]

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # AQUÍ ESTÁ LA CORRECCIÓN: Guardamos las 4 hojas
        reporte.drop(columns=["Fecha_dt", "Fecha_str", "CUENTA_COD", "CUENTA_NOM"]).to_excel(writer, sheet_name="REPORTE", index=False)
        mapeo.to_excel(writer, sheet_name="CUENTA", index=False)
        tabla_ufv.drop(columns=["Fecha_dt", "Fecha_str"]).to_excel(writer, sheet_name="UFV", index=False)
        asiento_out.to_excel(writer, sheet_name="ASIENTOS", index=False)
    
    output.seek(0)
    return output