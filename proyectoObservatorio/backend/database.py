from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


DATABASE_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL)


class PostgresConnection:
    def __init__(self, url: str) -> None:
        import psycopg2
        from psycopg2.extras import DictCursor

        self._conn = psycopg2.connect(url, cursor_factory=DictCursor)

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] | None = None):
        cursor = self._conn.cursor()
        cursor.execute(sql.replace("?", "%s"), params)
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        self.close()


def get_connection(db_file: Path):
    if IS_POSTGRES:
        return PostgresConnection(DATABASE_URL or "")

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    return exc.__class__.__name__ in {"IntegrityError", "UniqueViolation"}


def table_columns(conn, table_name: str) -> set[str]:
    if IS_POSTGRES:
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchall()
        return {row["column_name"] for row in rows}

    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def ensure_database_schema(conn) -> None:
    if IS_POSTGRES:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id INTEGER PRIMARY KEY,
              codigo_hermes TEXT UNIQUE,
              nombre TEXT NOT NULL,
              objetivo TEXT,
              resumen TEXT,
              departamento TEXT,
              facultad TEXT,
              grupo_de_investigacion TEXT,
              estado TEXT,
              ods_principal TEXT,
              area_ocde TEXT,
              tipo_proyecto TEXT,
              proteccion_producto TEXT,
              año_inicio INTEGER,
              año_fin INTEGER,
              macrocategoria_id TEXT,
              macrocategoria TEXT,
              subcategoria_id TEXT,
              subcategoria TEXT,
              clasificacion_origen TEXT DEFAULT 'sin_asignar',
              clasificacion_confianza DOUBLE PRECISION,
              clasificacion_revisada INTEGER DEFAULT 0,
              clasificacion_actualizada_en TEXT,
              texto_ml TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_products (
              id SERIAL PRIMARY KEY,
              project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
              tipo TEXT NOT NULL DEFAULT 'esperado',
              producto TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_keywords (
              id SERIAL PRIMARY KEY,
              project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
              palabra TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_estado ON projects(estado)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_departamento ON projects(departamento)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_macro ON projects(macrocategoria_id)")
        conn.commit()
        return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY,
          codigo_hermes TEXT UNIQUE,
          nombre TEXT NOT NULL,
          objetivo TEXT,
          resumen TEXT,
          departamento TEXT,
          facultad TEXT,
          grupo_de_investigacion TEXT,
          estado TEXT,
          ods_principal TEXT,
          area_ocde TEXT,
          tipo_proyecto TEXT,
          proteccion_producto TEXT,
          año_inicio INTEGER,
          año_fin INTEGER,
          macrocategoria_id TEXT,
          macrocategoria TEXT,
          subcategoria_id TEXT,
          subcategoria TEXT,
          clasificacion_origen TEXT DEFAULT 'sin_asignar',
          clasificacion_confianza REAL,
          clasificacion_revisada INTEGER DEFAULT 0,
          clasificacion_actualizada_en TEXT,
          texto_ml TEXT
        )
        """
    )
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_estado ON projects(estado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_departamento ON projects(departamento)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_macro ON projects(macrocategoria_id)")
    conn.commit()
