from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
DB_FILE = BASE_DIR / "data" / "processed" / "proyectos.db"
CATEGORIES_FILE = BASE_DIR / "data" / "dashboard" / "categorias.json"
UPLOAD_DIR = BASE_DIR / "data" / "processed" / "uploads"

app = FastAPI(title="Observatorio UNAL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectIn(BaseModel):
    codigo_hermes: str | None = None
    nombre: str = Field(min_length=1)
    objetivo: str = Field(min_length=1)
    departamento: str = Field(min_length=1)
    facultad: str | None = None
    año_inicio: int
    año_fin: int | None = None
    estado: str = Field(min_length=1)
    ods_principal: str | None = None
    proteccion_producto: str | None = None
    macrocategoria_id: str = Field(min_length=1)
    macrocategoria: str = Field(min_length=1)
    subcategoria_id: str = Field(min_length=1)
    subcategoria: str = Field(min_length=1)
    palabras_clave: list[str] = Field(default_factory=list)
    productos_esperados: list[str] = Field(default_factory=list)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_classification_columns(conn)
    return conn


def ensure_classification_columns(conn: sqlite3.Connection) -> None:
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
    conn.commit()


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value and value != "—" else None


def project_text(project: ProjectIn) -> str:
    parts = [
        project.nombre,
        project.objetivo,
        project.ods_principal or "",
        project.proteccion_producto or "",
        " ".join(project.palabras_clave),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def row_to_project(row: sqlite3.Row, products: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "codigo_hermes": row["codigo_hermes"] or "",
        "nombre": row["nombre"],
        "objetivo": row["objetivo"] or "",
        "departamento": row["departamento"] or "",
        "facultad": row["facultad"] or "",
        "año_inicio": row["año_inicio"],
        "año_fin": row["año_fin"],
        "estado": row["estado"] or "",
        "ods_principal": row["ods_principal"] or "",
        "proteccion_producto": row["proteccion_producto"] or "",
        "macrocategoria_id": row["macrocategoria_id"] or "M00",
        "macrocategoria": row["macrocategoria"] or "Sin asignar",
        "subcategoria_id": row["subcategoria_id"] or "M00-S00",
        "subcategoria": row["subcategoria"] or "Sin asignar",
        "clasificacion_origen": row["clasificacion_origen"] or "sin_asignar",
        "clasificacion_confianza": row["clasificacion_confianza"],
        "clasificacion_revisada": bool(row["clasificacion_revisada"]),
        "clasificacion_actualizada_en": row["clasificacion_actualizada_en"],
        "palabras_clave": [],
        "productos_esperados": products or [],
    }


def fetch_products(conn: sqlite3.Connection) -> dict[int, list[str]]:
    products: dict[int, list[str]] = {}
    rows = conn.execute(
        "SELECT project_id, producto FROM project_products ORDER BY producto"
    ).fetchall()
    for row in rows:
        products.setdefault(row["project_id"], []).append(row["producto"])
    return products


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/categories")
def get_categories() -> Any:
    return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))


@app.get("/api/projects")
def get_projects() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
        products = fetch_products(conn)
    return [row_to_project(row, products.get(row["id"], [])) for row in rows]


@app.post("/api/projects", status_code=201)
def create_project(project: ProjectIn) -> dict[str, Any]:
    codigo = clean_optional(project.codigo_hermes)

    with get_conn() as conn:
        next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM projects").fetchone()[0]
        try:
            conn.execute(
                """
                INSERT INTO projects (
                  id, codigo_hermes, nombre, objetivo, resumen, departamento,
                  facultad, estado, ods_principal, area_ocde, tipo_proyecto,
                  proteccion_producto, año_inicio, año_fin, macrocategoria_id, macrocategoria,
                  subcategoria_id, subcategoria, clasificacion_origen,
                  clasificacion_confianza, clasificacion_revisada,
                  clasificacion_actualizada_en, texto_ml
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_id,
                    codigo,
                    project.nombre.strip(),
                    project.objetivo.strip(),
                    "",
                    project.departamento.strip(),
                    clean_optional(project.facultad) or "Ingeniería",
                    project.estado.strip(),
                    clean_optional(project.ods_principal) or "",
                    "",
                    "Registro manual",
                    clean_optional(project.proteccion_producto) or "",
                    project.año_inicio,
                    project.año_fin,
                    project.macrocategoria_id.strip(),
                    project.macrocategoria.strip(),
                    project.subcategoria_id.strip(),
                    project.subcategoria.strip(),
                    "manual",
                    1.0,
                    1,
                    datetime.now(timezone.utc).isoformat(),
                    project_text(project),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un proyecto con ese código HERMES.",
            ) from exc

        for product in project.productos_esperados:
            product = product.strip()
            if product:
                conn.execute(
                    "INSERT INTO project_products (project_id, producto) VALUES (?, ?)",
                    (next_id, product),
                )

        conn.commit()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (next_id,)).fetchone()
        products = [
            row["producto"]
            for row in conn.execute(
                "SELECT producto FROM project_products WHERE project_id = ? ORDER BY producto",
                (next_id,),
            )
        ]

    return row_to_project(row, products)


@app.post("/api/projects/import-excel")
async def import_projects_excel(
    dry_run: bool = Query(default=True),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debes subir un archivo Excel.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix or ".xlsx"

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=UPLOAD_DIR,
            delete=False,
        ) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        from scripts.update_from_excel import load_report, sync_projects

        projects = load_report(temp_path)
        summary = sync_projects(projects, dry_run=dry_run)
        summary["archivo_procesado"] = file.filename

        if not dry_run:
            with get_conn() as conn:
                rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
                products = fetch_products(conn)
            summary["projects"] = [
                row_to_project(row, products.get(row["id"], [])) for row in rows
            ]

        return summary
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo procesar el Excel: {exc}",
        ) from exc
    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")
