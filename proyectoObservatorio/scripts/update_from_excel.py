from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_database import (
    BASE_DIR,
    DASHBOARD_JSON,
    DB_FILE,
    ML_DATASET,
    clean_text,
    slugify,
    build_projects,
)


SUMMARY_FILE = BASE_DIR / "data" / "processed" / "last_update_summary.json"
PROPOSED_PRODUCT_COLUMNS = {
    "tipo_de_producto_propuesto",
    "tipo_producto_propuesto",
    "producto_propuesto",
    "productos_propuestos",
}
ACHIEVED_PRODUCT_COLUMNS = {
    "tipo_de_producto_logrado",
    "tipo_producto_logrado",
    "nombre_de_producto_logrado",
    "nombre_producto_logrado",
}
PROTECTION_COLUMNS = {
    "es_suceptible_de_proteccion_producto",
    "es_suceptible_de_proteccion___producto",
    "es_susceptible_de_proteccion_producto",
    "es_susceptible_de_proteccion___producto",
    "es_succeptible_de_proteccion_producto",
    "es_succeptible_de_proteccion___producto",
    "susceptible_de_proteccion_producto",
    "succeptible_de_proteccion_producto",
    "suceptible_de_proteccion_producto",
    "proteccion_producto",
}
KEYWORD_COLUMNS = {
    "palabras_clave",
    "palabra_clave",
    "keywords",
    "key_words",
    "palabras_clave_proyecto",
    "palabras_clave_del_proyecto",
}
GROUP_COLUMNS = {
    "grupo_de_investigacion",
    "nombre_grupo_de_investigacion",
    "grupo_investigacion",
    "nombre_del_grupo_de_investigacion",
}
REQUIRED_IMPORT_GROUPS = {
    "código HERMES": {"codigo_hermes"},
    "nombre del proyecto": {"nombre_proyecto"},
    "objetivo general": {"objetivo_general"},
    "resumen": {"resumen"},
    "estado actual": {"estado_actual"},
    "fecha propuesto": {"fecha_propuesto"},
    "departamento/instituto": {
        "departamento_o_instituto_investigador_principal",
        "departamento_o_instituto___investigador_principal",
    },
}
UNASSIGNED = {
    "macrocategoria_id": "M00",
    "macrocategoria": "Sin asignar",
    "subcategoria_id": "M00-S00",
    "subcategoria": "Sin asignar",
    "clasificacion_origen": "pendiente_autoclasificacion",
    "clasificacion_confianza": 0.0,
}


ADMIN_COLUMNS = [
    "codigo_hermes",
    "nombre",
    "objetivo",
    "resumen",
    "departamento",
    "facultad",
    "grupo_de_investigacion",
    "estado",
    "ods_principal",
    "area_ocde",
    "tipo_proyecto",
    "proteccion_producto",
    "año_inicio",
    "año_fin",
    "texto_ml",
]


CLASSIFICATION_COLUMNS = [
    "macrocategoria_id",
    "macrocategoria",
    "subcategoria_id",
    "subcategoria",
    "clasificacion_origen",
    "clasificacion_confianza",
    "clasificacion_revisada",
    "clasificacion_actualizada_en",
]


def load_report(excel_file: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_file)
    df.columns = [slugify(col) for col in df.columns]
    source_columns = set(df.columns)
    missing_groups = [
        label
        for label, options in REQUIRED_IMPORT_GROUPS.items()
        if not source_columns & options
    ]
    if missing_groups:
        missing = ", ".join(missing_groups)
        raise ValueError(
            "El archivo no parece ser un reporte de proyectos válido. "
            f"Faltan columnas de: {missing}. "
            "Sube el Excel oficial generado por la plataforma."
        )

    if "fecha_propuesto" in df.columns:
        df["fecha_propuesto"] = pd.to_datetime(df["fecha_propuesto"], errors="coerce")
        df = df[df["fecha_propuesto"].dt.year >= 2016]

    columns = [
        "codigo_hermes",
        "nombre_proyecto",
        "estado_actual",
        "fecha_propuesto",
        "departamento_o_instituto_investigador_principal",
        "departamento_o_instituto___investigador_principal",
        "grupo_de_investigacion",
        *sorted(GROUP_COLUMNS),
        "objetivo_general",
        "ods_principal",
        "resumen",
        *sorted(PROPOSED_PRODUCT_COLUMNS),
        *sorted(ACHIEVED_PRODUCT_COLUMNS),
        *sorted(KEYWORD_COLUMNS),
        *sorted(PROTECTION_COLUMNS),
        "area_ocde",
        "tipo_proyecto",
    ]
    existing_columns = [column for column in columns if column in df.columns]
    df = df[existing_columns].fillna("")

    if "resumen" in df.columns and "objetivo_general" in df.columns:
        df = df[
            (df["resumen"].astype(str).str.strip() != "")
            & (df["objetivo_general"].astype(str).str.strip() != "")
        ]

    if "codigo_hermes" not in df.columns:
        raise ValueError("El Excel debe incluir la columna codigo_hermes.")

    grouped = df.groupby("codigo_hermes", as_index=False).agg(
        lambda values: " ; ".join(
            sorted(
                {
                    str(value).strip()
                    for value in values
                    if str(value).strip() and str(value).strip().lower() != "nan"
                }
            )
        )
    )
    projects = build_projects(grouped)
    projects.attrs["source_columns"] = source_columns
    projects.attrs["has_proposed_products"] = bool(source_columns & PROPOSED_PRODUCT_COLUMNS)
    projects.attrs["has_achieved_products"] = bool(source_columns & ACHIEVED_PRODUCT_COLUMNS)
    projects.attrs["has_protection"] = bool(source_columns & PROTECTION_COLUMNS)
    return projects


def ensure_database_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
    migrations = {
        "clasificacion_origen": "ALTER TABLE projects ADD COLUMN clasificacion_origen TEXT DEFAULT 'sin_asignar'",
        "clasificacion_confianza": "ALTER TABLE projects ADD COLUMN clasificacion_confianza REAL",
        "clasificacion_revisada": "ALTER TABLE projects ADD COLUMN clasificacion_revisada INTEGER DEFAULT 0",
        "clasificacion_actualizada_en": "ALTER TABLE projects ADD COLUMN clasificacion_actualizada_en TEXT",
        "proteccion_producto": "ALTER TABLE projects ADD COLUMN proteccion_producto TEXT",
        "grupo_de_investigacion": "ALTER TABLE projects ADD COLUMN grupo_de_investigacion TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            conn.execute(statement)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_products (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          tipo TEXT NOT NULL DEFAULT 'esperado',
          producto TEXT NOT NULL,
          FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    product_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(project_products)")
    }
    if "tipo" not in product_columns:
        conn.execute(
            "ALTER TABLE project_products ADD COLUMN tipo TEXT NOT NULL DEFAULT 'esperado'"
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_keywords (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          palabra TEXT NOT NULL,
          FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def normalize_for_compare(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value


def is_without_category(project: dict[str, Any]) -> bool:
    macro_id = clean_text(project.get("macrocategoria_id"))
    sub_id = clean_text(project.get("subcategoria_id"))
    return macro_id in {"", "M00"} or sub_id in {"", "M00-S00"}


def should_autoclassify(project: dict[str, Any]) -> bool:
    if bool(project.get("clasificacion_revisada")):
        return False
    origin = clean_text(project.get("clasificacion_origen"))
    already_pending = origin == "pendiente_autoclasificacion"
    return is_without_category(project) and not already_pending


def classify_project(project: dict[str, Any]) -> dict[str, Any]:
    # Punto de extensión: aquí se conectará un clasificador por reglas, embeddings o ML.
    # Por ahora no se infiere una categoría real; se marca como pendiente.
    return dict(UNASSIGNED)


def classification_payload(project: dict[str, Any], now: str) -> dict[str, Any]:
    classification = classify_project(project)
    return {
        **classification,
        "clasificacion_revisada": 0,
        "clasificacion_actualizada_en": now,
    }


def fetch_products(
    conn: sqlite3.Connection,
    project_id: int,
    product_type: str | None = None,
) -> list[str]:
    if product_type:
        rows = conn.execute(
            """
            SELECT producto FROM project_products
            WHERE project_id = ? AND tipo = ?
            ORDER BY producto
            """,
            (project_id, product_type),
        ).fetchall()
        return [row["producto"] for row in rows]

    rows = conn.execute(
        "SELECT producto FROM project_products WHERE project_id = ? ORDER BY producto",
        (project_id,),
    ).fetchall()
    return [row["producto"] for row in rows]


def fetch_keywords(conn: sqlite3.Connection, project_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT palabra FROM project_keywords WHERE project_id = ? ORDER BY palabra",
        (project_id,),
    ).fetchall()
    return [row["palabra"] for row in rows]


def replace_products(
    conn: sqlite3.Connection,
    project_id: int,
    products: list[str],
    product_type: str,
) -> bool:
    current = fetch_products(conn, project_id, product_type)
    incoming = sorted({clean_text(product) for product in products if clean_text(product)})
    if current == incoming:
        return False

    conn.execute(
        "DELETE FROM project_products WHERE project_id = ? AND tipo = ?",
        (project_id, product_type),
    )
    for product in incoming:
        conn.execute(
            "INSERT INTO project_products (project_id, tipo, producto) VALUES (?, ?, ?)",
            (project_id, product_type, product),
        )
    return True


def replace_keywords(conn: sqlite3.Connection, project_id: int, keywords: list[str]) -> bool:
    current = fetch_keywords(conn, project_id)
    incoming = sorted({clean_text(keyword) for keyword in keywords if clean_text(keyword)})
    if current == incoming:
        return False

    conn.execute("DELETE FROM project_keywords WHERE project_id = ?", (project_id,))
    for keyword in incoming:
        conn.execute(
            "INSERT INTO project_keywords (project_id, palabra) VALUES (?, ?)",
            (project_id, keyword),
        )
    return True


def insert_project(
    conn: sqlite3.Connection,
    project: dict[str, Any],
    next_id: int,
    now: str,
) -> None:
    payload = {column: project.get(column) for column in ADMIN_COLUMNS}
    payload.update(classification_payload(project, now))
    payload["id"] = next_id

    columns = ["id", *ADMIN_COLUMNS, *CLASSIFICATION_COLUMNS]
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO projects ({', '.join(columns)}) VALUES ({placeholders})",
        [payload.get(column) for column in columns],
    )
    replace_products(conn, next_id, project.get("productos_propuestos", []), "propuesto")
    replace_products(conn, next_id, project.get("productos_logrados", []), "logrado")
    replace_keywords(conn, next_id, project.get("palabras_clave", []))


def update_project(
    conn: sqlite3.Connection,
    existing: dict[str, Any],
    incoming: dict[str, Any],
    now: str,
    *,
    update_proposed_products: bool,
    update_achieved_products: bool,
    update_protection: bool,
) -> tuple[bool, bool, bool]:
    updates: dict[str, Any] = {}

    for column in ADMIN_COLUMNS:
        if column == "proteccion_producto" and not update_protection:
            continue
        old_value = normalize_for_compare(existing.get(column))
        new_value = normalize_for_compare(incoming.get(column))
        if old_value != new_value:
            updates[column] = incoming.get(column)

    category_changed = False
    reviewed = bool(existing.get("clasificacion_revisada"))
    if should_autoclassify(existing):
        updates.update(classification_payload(incoming, now))
        category_changed = True

    proposed_products_changed = False
    if update_proposed_products:
        proposed_products_changed = replace_products(
            conn,
            int(existing["id"]),
            incoming.get("productos_propuestos", []),
            "propuesto",
        )
    achieved_products_changed = False
    if update_achieved_products:
        achieved_products_changed = replace_products(
            conn,
            int(existing["id"]),
            incoming.get("productos_logrados", []),
            "logrado",
        )
    keywords_changed = replace_keywords(
        conn,
        int(existing["id"]),
        incoming.get("palabras_clave", []),
    )

    if updates:
        assignments = ", ".join(f"{column} = ?" for column in updates)
        conn.execute(
            f"UPDATE projects SET {assignments} WHERE id = ?",
            [*updates.values(), existing["id"]],
        )

    return bool(
        updates
        or proposed_products_changed
        or achieved_products_changed
        or keywords_changed
    ), category_changed, reviewed


def export_dashboard_json(conn: sqlite3.Connection) -> None:
    product_rows = conn.execute(
        "SELECT project_id, tipo, producto FROM project_products ORDER BY producto"
    ).fetchall()
    keyword_rows = conn.execute(
        "SELECT project_id, palabra FROM project_keywords ORDER BY palabra"
    ).fetchall()
    proposed_products: dict[int, list[str]] = {}
    achieved_products: dict[int, list[str]] = {}
    products: dict[int, set[str]] = {}
    for row in product_rows:
        project_id = row["project_id"]
        product = row["producto"]
        products.setdefault(project_id, set()).add(product)
        if row["tipo"] == "logrado":
            achieved_products.setdefault(project_id, []).append(product)
        else:
            proposed_products.setdefault(project_id, []).append(product)
    keywords: dict[int, list[str]] = {}
    for row in keyword_rows:
        keywords.setdefault(row["project_id"], []).append(row["palabra"])

    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    records = []
    for row in rows:
        project = row_to_dict(row)
        records.append(
            {
                "id": project["id"],
                "codigo_hermes": project.get("codigo_hermes") or "",
                "nombre": project.get("nombre") or "",
                "objetivo": project.get("objetivo") or "",
                "departamento": project.get("departamento") or "",
                "facultad": project.get("facultad") or "",
                "año_inicio": project.get("año_inicio"),
                "año_fin": project.get("año_fin"),
                "estado": project.get("estado") or "",
                "ods_principal": project.get("ods_principal") or "",
                "proteccion_producto": project.get("proteccion_producto") or "",
                "grupo_de_investigacion": project.get("grupo_de_investigacion") or "",
                "macrocategoria_id": project.get("macrocategoria_id") or "M00",
                "macrocategoria": project.get("macrocategoria") or "Sin asignar",
                "subcategoria_id": project.get("subcategoria_id") or "M00-S00",
                "subcategoria": project.get("subcategoria") or "Sin asignar",
                "palabras_clave": keywords.get(project["id"], []),
                "productos_propuestos": proposed_products.get(project["id"], []),
                "productos_logrados": achieved_products.get(project["id"], []),
                "productos_esperados": sorted(products.get(project["id"], set())),
            }
        )

    DASHBOARD_JSON.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_ml_dataset(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, codigo_hermes, nombre, objetivo, resumen, area_ocde,
               tipo_proyecto, proteccion_producto, texto_ml, macrocategoria_id, subcategoria_id
        FROM projects
        ORDER BY id
        """
    ).fetchall()
    records = [row_to_dict(row) for row in rows]
    pd.DataFrame(records).to_csv(ML_DATASET, index=False)


def sync_projects(projects: pd.DataFrame, dry_run: bool = False) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    update_proposed_products = bool(projects.attrs.get("has_proposed_products", True))
    update_achieved_products = bool(projects.attrs.get("has_achieved_products", True))
    update_protection = bool(projects.attrs.get("has_protection", True))
    summary = {
        "archivo_procesado": None,
        "fecha_actualizacion": now,
        "proyectos_en_excel": int(len(projects)),
        "actualiza_productos_propuestos": update_proposed_products,
        "actualiza_productos_logrados": update_achieved_products,
        "actualiza_proteccion_producto": update_protection,
        "proyectos_sin_codigo": 0,
        "proyectos_nuevos": 0,
        "proyectos_actualizados": 0,
        "proyectos_sin_cambios": 0,
        "proyectos_autoclasificados": 0,
        "clasificaciones_revisadas_conservadas": 0,
        "errores": [],
        "advertencias": [],
        "dry_run": dry_run,
    }
    if not update_proposed_products:
        summary["advertencias"].append(
            "El Excel no trae columna de producto propuesto; se conservan los valores existentes."
        )
    if not update_achieved_products:
        summary["advertencias"].append(
            "El Excel no trae columna de producto logrado; se conservan los valores existentes."
        )
    if not update_protection:
        summary["advertencias"].append(
            "El Excel no trae columna de susceptible de protección; se conservan los valores existentes."
        )

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        ensure_database_schema(conn)

        existing_rows = conn.execute("SELECT * FROM projects").fetchall()
        existing_by_code = {
            clean_text(row["codigo_hermes"]): row_to_dict(row)
            for row in existing_rows
            if clean_text(row["codigo_hermes"])
        }
        next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM projects").fetchone()[0]

        try:
            for project in projects.to_dict("records"):
                code = clean_text(project.get("codigo_hermes"))
                if not code:
                    summary["proyectos_sin_codigo"] += 1
                    continue

                if code not in existing_by_code:
                    insert_project(conn, project, next_id, now)
                    next_id += 1
                    summary["proyectos_nuevos"] += 1
                    summary["proyectos_autoclasificados"] += 1
                    continue

                changed, category_changed, reviewed = update_project(
                    conn,
                    existing_by_code[code],
                    project,
                    now,
                    update_proposed_products=update_proposed_products,
                    update_achieved_products=update_achieved_products,
                    update_protection=update_protection,
                )
                if changed:
                    summary["proyectos_actualizados"] += 1
                else:
                    summary["proyectos_sin_cambios"] += 1
                if category_changed:
                    summary["proyectos_autoclasificados"] += 1
                if reviewed:
                    summary["clasificaciones_revisadas_conservadas"] += 1

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
                export_dashboard_json(conn)
                export_ml_dataset(conn)
        except Exception:
            conn.rollback()
            raise

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Actualiza la base de proyectos desde el reporte Excel oficial."
    )
    parser.add_argument(
        "excel_file",
        nargs=None,
        type=Path,
        help="Ruta del Excel a procesar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula el resumen sin guardar cambios en la base.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    excel_file = args.excel_file.resolve()
    if not excel_file.exists():
        raise FileNotFoundError(f"No existe el archivo: {excel_file}")

    projects = load_report(excel_file)
    summary = sync_projects(projects, dry_run=args.dry_run)
    summary["archivo_procesado"] = str(excel_file)

    if not args.dry_run:
        SUMMARY_FILE.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
