from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
DB_FILE = BASE_DIR / "data" / "processed" / "proyectos.db"
CATEGORIES_FILE = BASE_DIR / "data" / "dashboard" / "categorias.json"
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_PROJECTS_FILE = RAW_DIR / "reporteProyectoCoordinacionBas.xlsx"
RAW_PRODUCTS_FILE = RAW_DIR / "reporteProyectoCoordinacionBasProductos.xlsx"
PROCESS_SCRIPT = BASE_DIR / "scripts" / "process_raw_products.py"

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
    grupo_investigacion: str | None = None
    investigador_principal: str | None = None
    email_investigador_principal: str | None = None
    departamento: str = Field(min_length=1)
    facultad: str | None = None
    año_inicio: int
    año_fin: int | None = None
    estado: str = Field(min_length=1)
    ods_principal: str | None = None
    macrocategoria_id: str = Field(min_length=1)
    macrocategoria: str = Field(min_length=1)
    subcategoria_id: str = Field(min_length=1)
    subcategoria: str = Field(min_length=1)
    palabras_clave: list[str] = Field(default_factory=list)
    productos_esperados: list[str] = Field(default_factory=list)
    cantidad_de_producto: str | None = None
    cumplio_con_la_entrega_del_producto: str | None = None
    productos_logrados: list[str] = Field(default_factory=list)
    nombres_productos_logrados: list[str] = Field(default_factory=list)
    es_suceptible_de_proteccion_producto: str | None = None


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
        " ".join(project.palabras_clave),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def validate_excel_upload(upload: UploadFile) -> None:
    filename = upload.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail=f"El archivo {filename or 'sin nombre'} debe ser .xlsx.",
        )


async def save_excel_upload(upload: UploadFile, destination: Path) -> None:
    validate_excel_upload(upload)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    temp_destination = destination.with_suffix(destination.suffix + ".tmp")
    temp_destination.write_bytes(await upload.read())
    temp_destination.replace(destination)


def run_data_pipeline() -> str:
    result = subprocess.run(
        [sys.executable, str(PROCESS_SCRIPT)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=result.stderr.strip() or "No se pudo actualizar la base de datos.",
        )
    return result.stdout.strip()


def row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())

    def value(column: str, default: Any = "") -> Any:
        if column not in keys:
            return default
        return row[column] if row[column] is not None else default

    return {
        "id": value("id"),
        "codigo_hermes": value("codigo_hermes"),
        "nombre": value("nombre"),
        "objetivo": value("objetivo"),
        "grupo_investigacion": value("grupo_investigacion"),
        "investigador_principal": value("investigador_principal"),
        "email_investigador_principal": value("email_investigador_principal"),
        "departamento": value("departamento"),
        "facultad": value("facultad"),
        "año_inicio": value("año_inicio", None),
        "año_fin": value("año_fin", None),
        "estado": value("estado"),
        "ods_principal": value("ods_principal"),
        "macrocategoria_id": value("macrocategoria_id", "M00"),
        "macrocategoria": value("macrocategoria", "Sin asignar"),
        "subcategoria_id": value("subcategoria_id", "M00-S00"),
        "subcategoria": value("subcategoria", "Sin asignar"),
        "palabras_clave": split_multi_value(value("palabras_clave")),
        "productos_esperados": split_multi_value(value("productos_esperados")),
        "cantidad_de_producto": value("cantidad_de_producto"),
        "cumplio_con_la_entrega_del_producto": (
            value("cumplio_con_la_entrega_del_producto")
        ),
        "productos_logrados": split_multi_value(value("productos_logrados")),
        "nombres_productos_logrados": split_multi_value(
            value("nombres_productos_logrados")
        ),
        "subtipo_de_producto": value("subtipo_de_producto"),
        "enlace_o_link_del_producto": value("enlace_o_link_del_producto"),
        "fecha_de_entrega_del_producto_o_publicacion": (
            value("fecha_de_entrega_del_producto_o_publicacion")
        ),
        "es_suceptible_de_proteccion_producto": (
            value("es_suceptible_de_proteccion_producto")
        ),
        "lugar_de_deposito_del_producto": value("lugar_de_deposito_del_producto"),
        "objetivo_de_desarrollo_sostenible_producto": (
            value("objetivo_de_desarrollo_sostenible_producto")
        ),
        "area_ocde_productos": value("area_ocde_productos"),
    }


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
    return [row_to_project(row) for row in rows]


@app.post("/api/projects", status_code=201)
def create_project(project: ProjectIn) -> dict[str, Any]:
    codigo = clean_optional(project.codigo_hermes)

    with get_conn() as conn:
        next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM projects").fetchone()[0]
        try:
            conn.execute(
                """
                INSERT INTO projects (
                  id, codigo_hermes, nombre, objetivo, resumen,
                  grupo_investigacion, investigador_principal,
                  email_investigador_principal, departamento, facultad,
                  año_inicio, año_fin, estado, ods_principal, area_ocde,
                  tipo_proyecto, macrocategoria_id, macrocategoria, subcategoria_id,
                  subcategoria, palabras_clave, productos_esperados, cantidad_de_producto,
                  cumplio_con_la_entrega_del_producto, productos_logrados,
                  nombres_productos_logrados, subtipo_de_producto,
                  enlace_o_link_del_producto,
                  fecha_de_entrega_del_producto_o_publicacion,
                  es_suceptible_de_proteccion_producto,
                  lugar_de_deposito_del_producto,
                  objetivo_de_desarrollo_sostenible_producto, area_ocde_productos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_id,
                    codigo,
                    project.nombre.strip(),
                    project.objetivo.strip(),
                    "",
                    clean_optional(project.grupo_investigacion) or "",
                    clean_optional(project.investigador_principal) or "",
                    clean_optional(project.email_investigador_principal) or "",
                    project.departamento.strip(),
                    clean_optional(project.facultad) or "Ingeniería",
                    project.año_inicio,
                    project.año_fin,
                    project.estado.strip(),
                    clean_optional(project.ods_principal) or "",
                    "",
                    "Registro manual",
                    project.macrocategoria_id.strip(),
                    project.macrocategoria.strip(),
                    project.subcategoria_id.strip(),
                    project.subcategoria.strip(),
                    " ; ".join(project.palabras_clave),
                    " ; ".join(project.productos_esperados),
                    clean_optional(project.cantidad_de_producto) or "",
                    clean_optional(project.cumplio_con_la_entrega_del_producto) or "",
                    " ; ".join(project.productos_logrados),
                    " ; ".join(project.nombres_productos_logrados),
                    "",
                    "",
                    "",
                    clean_optional(project.es_suceptible_de_proteccion_producto) or "",
                    "",
                    "",
                    "",
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un proyecto con ese código HERMES.",
            ) from exc

        conn.commit()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (next_id,)).fetchone()

    return row_to_project(row)


@app.post("/api/import-data")
async def import_data(
    projects_file: UploadFile = File(...),
    products_file: UploadFile = File(...),
) -> dict[str, Any]:
    validate_excel_upload(projects_file)
    validate_excel_upload(products_file)
    await save_excel_upload(projects_file, RAW_PROJECTS_FILE)
    await save_excel_upload(products_file, RAW_PRODUCTS_FILE)
    output = run_data_pipeline()
    projects = get_projects()

    return {
        "message": "Base de datos actualizada correctamente.",
        "projects_count": len(projects),
        "pipeline_output": output,
        "projects": projects,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")
