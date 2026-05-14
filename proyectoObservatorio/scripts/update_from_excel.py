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


RAW_REPORT = BASE_DIR / "data" / "raw" / "reporteProyectoCoordinacionBasProductos.xlsx"
SUMMARY_FILE = BASE_DIR / "data" / "processed" / "last_update_summary.json"
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
        "objetivo_general",
        "ods_principal",
        "resumen",
        "tipo_de_producto_propuesto",
        "tipo_de_producto_logrado",
        "nombre_de_producto_logrado",
        "es_suceptible_de_proteccion_producto",
        "es_suceptible_de_proteccion___producto",
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
    return build_projects(grouped)


def ensure_database_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
    migrations = {
        "clasificacion_origen": "ALTER TABLE projects ADD COLUMN clasificacion_origen TEXT DEFAULT 'sin_asignar'",
        "clasificacion_confianza": "ALTER TABLE projects ADD COLUMN clasificacion_confianza REAL",
        "clasificacion_revisada": "ALTER TABLE projects ADD COLUMN clasificacion_revisada INTEGER DEFAULT 0",
        "clasificacion_actualizada_en": "ALTER TABLE projects ADD COLUMN clasificacion_actualizada_en TEXT",
        "proteccion_producto": "ALTER TABLE projects ADD COLUMN proteccion_producto TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            conn.execute(statement)


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


def fetch_products(conn: sqlite3.Connection, project_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT producto FROM project_products WHERE project_id = ? ORDER BY producto",
        (project_id,),
    ).fetchall()
    return [row["producto"] for row in rows]


def replace_products(conn: sqlite3.Connection, project_id: int, products: list[str]) -> bool:
    current = fetch_products(conn, project_id)
    incoming = sorted({clean_text(product) for product in products if clean_text(product)})
    if current == incoming:
        return False

    conn.execute("DELETE FROM project_products WHERE project_id = ?", (project_id,))
    for product in incoming:
        conn.execute(
            "INSERT INTO project_products (project_id, producto) VALUES (?, ?)",
            (project_id, product),
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
    replace_products(conn, next_id, project.get("productos_esperados", []))


def update_project(
    conn: sqlite3.Connection,
    existing: dict[str, Any],
    incoming: dict[str, Any],
    now: str,
) -> tuple[bool, bool, bool]:
    updates: dict[str, Any] = {}

    for column in ADMIN_COLUMNS:
        old_value = normalize_for_compare(existing.get(column))
        new_value = normalize_for_compare(incoming.get(column))
        if old_value != new_value:
            updates[column] = incoming.get(column)

    category_changed = False
    reviewed = bool(existing.get("clasificacion_revisada"))
    if should_autoclassify(existing):
        updates.update(classification_payload(incoming, now))
        category_changed = True

    products_changed = replace_products(
        conn,
        int(existing["id"]),
        incoming.get("productos_esperados", []),
    )

    if updates:
        assignments = ", ".join(f"{column} = ?" for column in updates)
        conn.execute(
            f"UPDATE projects SET {assignments} WHERE id = ?",
            [*updates.values(), existing["id"]],
        )

    return bool(updates or products_changed), category_changed, reviewed


def export_dashboard_json(conn: sqlite3.Connection) -> None:
    product_rows = conn.execute(
        "SELECT project_id, producto FROM project_products ORDER BY producto"
    ).fetchall()
    products: dict[int, list[str]] = {}
    for row in product_rows:
        products.setdefault(row["project_id"], []).append(row["producto"])

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
                "macrocategoria_id": project.get("macrocategoria_id") or "M00",
                "macrocategoria": project.get("macrocategoria") or "Sin asignar",
                "subcategoria_id": project.get("subcategoria_id") or "M00-S00",
                "subcategoria": project.get("subcategoria") or "Sin asignar",
                "palabras_clave": [],
                "productos_esperados": products.get(project["id"], []),
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
               tipo_proyecto, texto_ml, macrocategoria_id, subcategoria_id
        FROM projects
        ORDER BY id
        """
    ).fetchall()
    records = [row_to_dict(row) for row in rows]
    pd.DataFrame(records).to_csv(ML_DATASET, index=False)


def sync_projects(projects: pd.DataFrame, dry_run: bool = False) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "archivo_procesado": None,
        "fecha_actualizacion": now,
        "proyectos_en_excel": int(len(projects)),
        "proyectos_sin_codigo": 0,
        "proyectos_nuevos": 0,
        "proyectos_actualizados": 0,
        "proyectos_sin_cambios": 0,
        "proyectos_autoclasificados": 0,
        "clasificaciones_revisadas_conservadas": 0,
        "errores": [],
        "dry_run": dry_run,
    }

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
        nargs="?",
        type=Path,
        default=RAW_REPORT,
        help=f"Ruta del Excel a procesar. Por defecto: {RAW_REPORT}",
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
