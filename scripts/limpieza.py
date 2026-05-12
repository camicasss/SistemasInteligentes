from pathlib import Path
import unicodedata

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE_DIR / "data" / "raw" / "reporteProyectoCoordinacionBasProductos.xlsx"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "dataset_maestro_proyectos.xlsx"

# ====================================
# FUNCION LIMPIAR COLUMNAS
# ====================================
def limpiar_columna(columna):

    columna = columna.lower()

    columna = ''.join(
        c for c in unicodedata.normalize('NFD', columna)
        if unicodedata.category(c) != 'Mn'
    )

    columna = columna.replace(" ", "_")
    columna = columna.replace("-", "_")
    columna = columna.replace("/", "_")
    columna = columna.replace("(", "")
    columna = columna.replace(")", "")

    return columna

# ====================================
# LEER EXCEL
# ====================================
df = pd.read_excel(
    INPUT_FILE
)

print("\nTamaño original:")
print(df.shape)

# ====================================
# LIMPIAR COLUMNAS
# ====================================
df.columns = [
    limpiar_columna(col)
    for col in df.columns
]

# ====================================
# FILTRAR DESDE 2016
# ====================================
df["fecha_propuesto"] = pd.to_datetime(
    df["fecha_propuesto"],
    errors="coerce"
)

df = df[
    df["fecha_propuesto"].dt.year >= 2016
]

print("\nTamaño después del filtro:")
print(df.shape)

# ====================================
# SELECCIONAR COLUMNAS IMPORTANTES
# ====================================
columnas_importantes = [

    "codigo_hermes",
    "nombre_proyecto",
    "estado_actual",
    "fecha_propuesto",

    "departamento_o_instituto___investigador_principal",

    "grupo_de_investigacion",

    "objetivo_general",
    "ods_principal",

    "resumen",

    "tipo_de_producto_propuesto",
    "tipo_de_producto_logrado",

    "nombre_de_producto_logrado",

    "area_ocde",
    "tipo_proyecto"
]

# conservar solo columnas existentes
columnas_importantes = [
    col for col in columnas_importantes
    if col in df.columns
]

df = df[columnas_importantes]

# ====================================
# RELLENAR VACIOS
# ====================================
df = df.fillna("")

# ====================================
# ELIMINAR PROYECTOS SIN TEXTO
# ====================================

df = df[
    (df["resumen"].str.strip() != "") &
    (df["objetivo_general"].str.strip() != "")
]

print("\nTamaño después eliminar proyectos vacíos:")
print(df.shape)

# ====================================
# AGRUPAR PROYECTOS
# ====================================
df_final = df.groupby(
    "codigo_hermes",
    as_index=False
).agg(lambda x: " ; ".join(
    list(set(
        str(v).strip()
        for v in x
        if str(v).strip() != ""
    ))
))

# ====================================
# MOSTRAR RESULTADO
# ====================================
print("\nCantidad proyectos únicos:")
print(df_final.shape)

print("\nPrimeros proyectos:")
print(df_final.head())

# ====================================
# GUARDAR DATASET FINAL
# ====================================
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df_final.to_excel(OUTPUT_FILE, index=False)

print("\nDATASET MAESTRO GUARDADO.")
