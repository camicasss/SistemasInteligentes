from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_PROJECTS_FILE = RAW_DIR / "reporteProyectoCoordinacionBas.xlsx"
RAW_PRODUCTS_FILE = RAW_DIR / "reporteProyectoCoordinacionBasProductos.xlsx"
CLEAN_EXCEL = BASE_DIR / "data" / "processed" / "datos_limpios.xlsx"
DB_FILE = BASE_DIR / "data" / "processed" / "proyectos.db"
DASHBOARD_JSON = BASE_DIR / "data" / "dashboard" / "proyectos_from_db.json"

PROJECT_FILE_CANDIDATES = [
    RAW_PROJECTS_FILE,
    RAW_DIR / "main.xlsx",
    RAW_DIR / "reporteProyectos.xlsx",
    RAW_DIR / "reporteProyectoCoordinacion.xlsx",
    RAW_DIR / "reporteProyecto.xlsx",
]

PRODUCT_FILE_CANDIDATES = [
    RAW_PRODUCTS_FILE,
    RAW_DIR / "productos.xlsx",
]

PROJECT_RAW_COLUMNS = [
    "codigo_hermes",
    "codigo_quipu",
    "tipo",
    "nombre_proyecto",
    "estado_actual",
    "fecha_propuesto",
    "fecha_inicio",
    "fecha_final_programada",
    "fecha_final_con_prorrogas",
    "investigador_principal",
    "e_mail_investigador_principal",
    "grupo_de_investigacion",
    "grupo_investigacion",
    "nombre_grupo_investigacion",
    "grupo",
    "departamento_o_instituto_investigador_principal",
    "facultad_investigador_principal",
    "objetivo_general",
    "ods_principal",
    "resumen",
    "area_ocde",
    "tipo_proyecto",
]

PRODUCT_RAW_COLUMNS = [
    "codigo_hermes",
    "tipo_de_producto_propuesto",
    "cantidad_de_producto",
    "cumplio_con_la_entrega_del_producto",
    "tipo_de_producto_logrado",
    "nombre_de_producto_logrado",
    "subtipo_de_producto",
    "enlace_o_link_del_producto",
    "fecha_de_entrega_del_producto_o_publicacion",
    "es_suceptible_de_proteccion_producto",
    "lugar_de_deposito_del_producto",
    "objetivo_de_desarrollo_sostenible_producto",
    "area_ocde_productos",
]

PROJECT_COLUMNS = [
    "id",
    "codigo_hermes",
    "nombre",
    "objetivo",
    "resumen",
    "grupo_investigacion",
    "investigador_principal",
    "email_investigador_principal",
    "departamento",
    "facultad",
    "año_inicio",
    "año_fin",
    "estado",
    "ods_principal",
    "area_ocde",
    "tipo_proyecto",
    "macrocategoria_id",
    "macrocategoria",
    "subcategoria_id",
    "subcategoria",
    "palabras_clave",
    "productos_esperados",
    "cantidad_de_producto",
    "cumplio_con_la_entrega_del_producto",
    "productos_logrados",
    "nombres_productos_logrados",
    "subtipo_de_producto",
    "enlace_o_link_del_producto",
    "fecha_de_entrega_del_producto_o_publicacion",
    "es_suceptible_de_proteccion_producto",
    "lugar_de_deposito_del_producto",
    "objetivo_de_desarrollo_sostenible_producto",
    "area_ocde_productos",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def slugify(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value).lower())
    ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    ascii_text = re.sub(r"[^a-z0-9]+", "_", ascii_text)
    return ascii_text.strip("_")


def split_multi_value(value: object) -> list[str]:
    parts = re.split(r"\s*;\s*", clean_text(value))
    return [part for part in parts if part]


def join_unique(values: Any) -> str:
    seen = set()
    cleaned = []

    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)

    return " ; ".join(cleaned)


def normalize_department(value: object) -> str:
    text = clean_text(value)
    text = re.sub(r"^\d+\s*-\s*", "", text)
    return text.title() if text.isupper() else text


def normalize_estado(value: object) -> str:
    text = clean_text(value)
    lowered = text.lower()
    if "final" in lowered:
        return "Finalizado"
    if "ejec" in lowered or "activo" in lowered:
        return "En ejecución"
    if "suspend" in lowered:
        return "Suspendido"
    return text or "Sin registro"


def year_from_date(value: object) -> int | None:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        return None
    return int(date.year)


def find_projects_file() -> Path | None:
    for candidate in PROJECT_FILE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def find_products_file() -> Path | None:
    for candidate in PRODUCT_FILE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def read_excel_slugged(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [slugify(column) for column in df.columns]
    return df.fillna("")


def available_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available_columns = [column for column in columns if column in df.columns]
    if "codigo_hermes" not in available_columns:
        raise ValueError("El archivo no contiene la columna requerida CÓDIGO HERMES.")
    return df[available_columns]


def filter_valid_projects(df: pd.DataFrame) -> pd.DataFrame:
    if "fecha_propuesto" in df.columns:
        dates = pd.to_datetime(df["fecha_propuesto"], errors="coerce")
        df = df[dates.dt.year >= 2016]

    if "resumen" in df.columns and "objetivo_general" in df.columns:
        df = df[
            (df["resumen"].astype(str).str.strip() != "")
            & (df["objetivo_general"].astype(str).str.strip() != "")
        ]

    return df


def read_raw_projects() -> pd.DataFrame:
    projects_file = find_projects_file()
    source = projects_file or RAW_PRODUCTS_FILE

    if not source.exists():
        raise FileNotFoundError(
            "No se encontró un archivo raw de proyectos. Ubica el archivo maestro "
            f"en {RAW_PROJECTS_FILE} o el archivo de productos en {RAW_PRODUCTS_FILE}."
        )

    df = read_excel_slugged(source)
    df = filter_valid_projects(df)
    return available_frame(df, PROJECT_RAW_COLUMNS)


def read_raw_products() -> pd.DataFrame:
    products_file = find_products_file()
    if not products_file:
        return pd.DataFrame(columns=["codigo_hermes"])

    df = read_excel_slugged(products_file)
    return available_frame(df, PRODUCT_RAW_COLUMNS)


def collapse_by_project(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.groupby("codigo_hermes", as_index=False).agg(join_unique)


def first_value(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column in row:
            value = clean_text(row.get(column))
            if value:
                return value
    return ""


def first_year(row: pd.Series, columns: list[str]) -> int | None:
    for column in columns:
        if column in row:
            year = year_from_date(row.get(column))
            if year:
                return year
    return None


def merge_project_sources(projects_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    grouped_projects = collapse_by_project(projects_df)
    grouped_products = collapse_by_project(products_df)

    if grouped_products.empty:
        return grouped_projects

    return grouped_projects.merge(grouped_products, on="codigo_hermes", how="left")


def build_projects(df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for idx, row in df.iterrows():
        expected_products = split_multi_value(row.get("tipo_de_producto_propuesto"))
        achieved_products = split_multi_value(row.get("tipo_de_producto_logrado"))
        achieved_names = split_multi_value(row.get("nombre_de_producto_logrado"))
        objetivo = clean_text(row.get("objetivo_general"))
        resumen = clean_text(row.get("resumen"))

        records.append(
            {
                "id": idx + 1,
                "codigo_hermes": clean_text(row.get("codigo_hermes")),
                "nombre": clean_text(row.get("nombre_proyecto")),
                "objetivo": objetivo,
                "resumen": resumen,
                "grupo_investigacion": first_value(
                    row,
                    [
                        "grupo_de_investigacion",
                        "grupo_investigacion",
                        "nombre_grupo_investigacion",
                        "grupo",
                    ],
                ),
                "investigador_principal": clean_text(
                    row.get("investigador_principal")
                ),
                "email_investigador_principal": clean_text(
                    row.get("e_mail_investigador_principal")
                ),
                "departamento": normalize_department(
                    row.get("departamento_o_instituto_investigador_principal")
                ),
                "facultad": clean_text(row.get("facultad_investigador_principal"))
                or "Ingeniería",
                "año_inicio": first_year(row, ["fecha_inicio", "fecha_propuesto"]),
                "año_fin": first_year(
                    row, ["fecha_final_con_prorrogas", "fecha_final_programada"]
                ),
                "estado": normalize_estado(row.get("estado_actual")),
                "ods_principal": clean_text(row.get("ods_principal")),
                "area_ocde": clean_text(row.get("area_ocde")),
                "tipo_proyecto": clean_text(row.get("tipo_proyecto")),
                "macrocategoria_id": "M00",
                "macrocategoria": "Sin asignar",
                "subcategoria_id": "M00-S00",
                "subcategoria": "Sin asignar",
                "palabras_clave": [],
                "productos_esperados": expected_products,
                "cantidad_de_producto": clean_text(row.get("cantidad_de_producto")),
                "cumplio_con_la_entrega_del_producto": clean_text(
                    row.get("cumplio_con_la_entrega_del_producto")
                ),
                "productos_logrados": achieved_products,
                "nombres_productos_logrados": achieved_names,
                "subtipo_de_producto": clean_text(row.get("subtipo_de_producto")),
                "enlace_o_link_del_producto": clean_text(
                    row.get("enlace_o_link_del_producto")
                ),
                "fecha_de_entrega_del_producto_o_publicacion": clean_text(
                    row.get("fecha_de_entrega_del_producto_o_publicacion")
                ),
                "es_suceptible_de_proteccion_producto": clean_text(
                    row.get("es_suceptible_de_proteccion_producto")
                ),
                "lugar_de_deposito_del_producto": clean_text(
                    row.get("lugar_de_deposito_del_producto")
                ),
                "objetivo_de_desarrollo_sostenible_producto": clean_text(
                    row.get("objetivo_de_desarrollo_sostenible_producto")
                ),
                "area_ocde_productos": clean_text(row.get("area_ocde_productos")),
            }
        )

    return pd.DataFrame(records)


def flatten_for_excel(projects: pd.DataFrame) -> pd.DataFrame:
    excel_df = projects[PROJECT_COLUMNS].copy()
    for column in [
        "productos_esperados",
        "productos_logrados",
        "nombres_productos_logrados",
        "palabras_clave",
    ]:
        excel_df[column] = excel_df[column].apply(lambda values: " ; ".join(values))
    return excel_df


def write_clean_excel(projects: pd.DataFrame) -> None:
    CLEAN_EXCEL.parent.mkdir(parents=True, exist_ok=True)
    excel_df = flatten_for_excel(projects)

    with pd.ExcelWriter(CLEAN_EXCEL, engine="openpyxl") as writer:
        excel_df.to_excel(writer, sheet_name="datos_limpios", index=False)
        pd.DataFrame(
            {
                "orden": range(1, len(PROJECT_COLUMNS) + 1),
                "columnas_utilizadas": PROJECT_COLUMNS,
            }
        ).to_excel(writer, sheet_name="columnas_utilizadas", index=False)


def write_database(projects: pd.DataFrame) -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    db_df = flatten_for_excel(projects)

    with sqlite3.connect(DB_FILE) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS projects;

            CREATE TABLE projects (
              id INTEGER PRIMARY KEY,
              codigo_hermes TEXT UNIQUE,
              nombre TEXT NOT NULL,
              objetivo TEXT,
              resumen TEXT,
              grupo_investigacion TEXT,
              investigador_principal TEXT,
              email_investigador_principal TEXT,
              departamento TEXT,
              facultad TEXT,
              año_inicio INTEGER,
              año_fin INTEGER,
              estado TEXT,
              ods_principal TEXT,
              area_ocde TEXT,
              tipo_proyecto TEXT,
              macrocategoria_id TEXT,
              macrocategoria TEXT,
              subcategoria_id TEXT,
              subcategoria TEXT,
              palabras_clave TEXT,
              productos_esperados TEXT,
              cantidad_de_producto TEXT,
              cumplio_con_la_entrega_del_producto TEXT,
              productos_logrados TEXT,
              nombres_productos_logrados TEXT,
              subtipo_de_producto TEXT,
              enlace_o_link_del_producto TEXT,
              fecha_de_entrega_del_producto_o_publicacion TEXT,
              es_suceptible_de_proteccion_producto TEXT,
              lugar_de_deposito_del_producto TEXT,
              objetivo_de_desarrollo_sostenible_producto TEXT,
              area_ocde_productos TEXT
            );

            CREATE INDEX idx_projects_estado ON projects(estado);
            CREATE INDEX idx_projects_departamento ON projects(departamento);
            CREATE INDEX idx_projects_macro ON projects(macrocategoria_id);
            """
        )
        db_df.to_sql("projects", conn, if_exists="append", index=False)


def records_for_dashboard(projects: pd.DataFrame) -> list[dict[str, Any]]:
    records = projects.where(pd.notna(projects), None).to_dict("records")
    for record in records:
        for year_column in ["año_inicio", "año_fin"]:
            value = record.get(year_column)
            record[year_column] = None if pd.isna(value) else int(value)
    return records


def write_dashboard_json(projects: pd.DataFrame) -> None:
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(
        json.dumps(records_for_dashboard(projects), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    raw_projects_df = read_raw_projects()
    raw_products_df = read_raw_products()
    merged_df = merge_project_sources(raw_projects_df, raw_products_df)
    projects = build_projects(merged_df)

    write_clean_excel(projects)
    write_database(projects)
    write_dashboard_json(projects)

    print(f"Project raw rows used: {len(raw_projects_df)}")
    print(f"Product raw rows used: {len(raw_products_df)}")
    print(f"Projects imported: {len(projects)}")
    print(f"Clean Excel: {CLEAN_EXCEL}")
    print(f"Database: {DB_FILE}")
    print(f"Dashboard JSON: {DASHBOARD_JSON}")


if __name__ == "__main__":
    main()
