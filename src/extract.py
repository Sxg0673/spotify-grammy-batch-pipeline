"""Extracción de las fuentes (taller §6.7; patrón de la Activity 3).

Cada función lee su fuente, verifica las columnas requeridas (contrato, D12), selecciona
solo esas columnas, escribe un archivo raw en data/work/<run_id>/raw/ junto con su metadata
y devuelve solo la ruta: las tareas intercambian rutas, no DataFrames.
No limpia ni transforma: los problemas de calidad deben llegar intactos a la compuerta raw.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError

from src import schemas as s
from src.errors import SourceContractError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PIPELINE_DATA_DIR", PROJECT_ROOT / "data"))
DEFAULT_SPOTIFY_PATH = DATA_DIR / "raw" / "spotify_dataset.csv"
DEFAULT_GRAMMY_TABLE = "grammy_awards"

RAW_DTYPES = {"spotify": s.SPOTIFY_RAW_DTYPES, "grammy": s.GRAMMY_RAW_DTYPES}


# ---------------------------------------------------------
# Rutas de la corrida (X1)
# ---------------------------------------------------------

def safe_run_id(run_id):
    """Los run_id de Airflow traen ':' y '+'; se reemplaza todo lo que no sea seguro en una ruta."""
    return re.sub(r"[^A-Za-z0-9_.-]", "-", run_id)


def run_dir(run_id):
    directory = DATA_DIR / "work" / safe_run_id(run_id)
    (directory / "raw").mkdir(parents=True, exist_ok=True)
    return directory


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_raw(df, run_id, source, origin):
    directory = run_dir(run_id) / "raw"
    out_path = directory / f"{source}_raw.csv"
    df.to_csv(out_path, index=False)
    metadata = {
        "source": source,
        "run_id": run_id,
        "extracted_at_utc": _now_utc(),
        "origin": origin,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "output": str(out_path),
    }
    (directory / f"{source}_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(f"[extract] {source}: {len(df)} filas -> {out_path}")
    return str(out_path)


def _check_columns(available, required, origin_description):
    missing = [c for c in required if c not in available]
    if missing:
        raise SourceContractError(f"{origin_description}: faltan columnas requeridas {missing}")


# ---------------------------------------------------------
# Spotify (CSV)
# ---------------------------------------------------------

def extract_spotify(run_id, source_path=DEFAULT_SPOTIFY_PATH):
    source_path = Path(source_path)
    if not source_path.exists():
        raise SourceContractError(f"No existe el archivo fuente de Spotify: {source_path}")

    header = pd.read_csv(source_path, nrows=0).columns
    _check_columns(header, s.SPOTIFY_RAW_COLUMNS, f"Spotify ({source_path.name})")

    try:
        df = pd.read_csv(source_path, usecols=s.SPOTIFY_RAW_COLUMNS, dtype=s.SPOTIFY_RAW_DTYPES)
    except (ValueError, TypeError) as exc:
        raise SourceContractError(f"Spotify ({source_path.name}): un valor no coincide con su tipo declarado: {exc}") from exc

    df = df[s.SPOTIFY_RAW_COLUMNS]
    origin = {"type": "csv", "path": str(source_path),
              "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()}
    return _write_raw(df, run_id, "spotify", origin)


# ---------------------------------------------------------
# Grammy (PostgreSQL, base fuente grammy_source)
# ---------------------------------------------------------

def _source_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DATA_PG_USER"],
        password=os.environ["DATA_PG_PASSWORD"],
        host=os.environ.get("DATA_PG_HOST", "localhost"),
        port=int(os.environ.get("DATA_PG_PORT", "5432")),
        database=os.environ["SOURCE_DB_NAME"],
    )
    return create_engine(url)


def extract_grammys(run_id, table=DEFAULT_GRAMMY_TABLE):
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", table):
        raise SourceContractError(f"Nombre de tabla no válido: {table!r}")

    engine = _source_engine()
    try:
        with engine.connect() as conn:
            try:
                header = pd.read_sql(text(f"SELECT * FROM {table} LIMIT 0"), conn).columns
            except ProgrammingError as exc:
                raise SourceContractError(f"Grammy: no existe o no es legible la tabla {table!r}") from exc
            _check_columns(header, s.GRAMMY_RAW_COLUMNS, f"Grammy (tabla {table})")
            query = f"SELECT {', '.join(s.GRAMMY_RAW_COLUMNS)} FROM {table} ORDER BY id"
            df = pd.read_sql(text(query), conn)
    finally:
        engine.dispose()

    try:
        df = df.astype(s.GRAMMY_RAW_DTYPES)
    except (ValueError, TypeError) as exc:
        raise SourceContractError(f"Grammy (tabla {table}): un valor no coincide con su tipo declarado: {exc}") from exc

    origin = {"type": "postgresql", "database": os.environ["SOURCE_DB_NAME"], "table": table, "query": query}
    return _write_raw(df, run_id, "grammy", origin)


# ---------------------------------------------------------
# Lectura de archivos raw (la usan validation y transform)
# ---------------------------------------------------------

def read_raw(path, source):
    return pd.read_csv(path, dtype=RAW_DTYPES[source])
