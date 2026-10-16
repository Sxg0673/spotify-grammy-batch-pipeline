"""Carga al Data Warehouse (taller §6.10 y §7.3).

Estrategia de rerun seguro: truncar y cargar en UNA transacción (reemplazo controlado,
el equivalente en base de datos al "sobrescribir" de la Activity 3):
- Un rerun con la misma entrada deja el DW idéntico, sin duplicados.
- Si algo falla a mitad de la carga, la transacción se deshace y el DW conserva la carga anterior.
Las dimensiones se cargan primero; los hechos traducen llaves de negocio a llaves sustitutas.
Las llaves sustitutas NO se reinician: etl_user no es dueño de las secuencias (mínimo privilegio).
Cada recarga asigna llaves nuevas; conteos, medidas y relaciones quedan idénticos.
"""
import json
import os
from datetime import datetime, timezone

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src import schemas as s
from src.errors import LoadIntegrityError
from src.extract import run_dir
from src.transform import read_prepared

# (tabla, columnas que se insertan, llave de negocio, llave sustituta)
DIMENSIONS = [
    ("dim_artist", ["artist_bk", "artist_name", "is_awarded"], "artist_bk", "artist_key"),
    ("dim_year", ["year", "decade"], "year", "year_key"),
    ("dim_category", ["category_bk", "category_name", "is_new_artist"], "category_bk", "category_key"),
    ("dim_genre", ["genre_name"], "genre_name", "genre_key"),
    ("dim_track", ["track_id", "track_name", "song_bk", "is_song_representative", "audio_analyzed"], "track_id", "track_key"),
]
ALL_TABLES = ["fact_track_artist", "fact_award", "bridge_track_genre",
              "dim_track", "dim_genre", "dim_category", "dim_year", "dim_artist"]


def _connect():
    return psycopg2.connect(
        host=os.environ.get("DATA_PG_HOST", "localhost"),
        port=int(os.environ.get("DATA_PG_PORT", "5432")),
        user=os.environ["DATA_PG_USER"],
        password=os.environ["DATA_PG_PASSWORD"],
        dbname=os.environ["DW_DB_NAME"],
    )


def _records(df):
    """Filas como tuplas de tipos de Python; los nulos de pandas pasan a None."""
    columns = [df[c].tolist() for c in df.columns]
    return [tuple(None if (v is None or v is pd.NA or (isinstance(v, float) and v != v)) else v for v in row)
            for row in zip(*columns)]


def _insert(cur, table, df):
    execute_values(cur, f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES %s",
                   _records(df), page_size=5000)


def _key_map(cur, table, business_key, surrogate_key):
    cur.execute(f"SELECT {business_key}, {surrogate_key} FROM {table}")
    return dict(cur.fetchall())


def _to_keys(series, mapping, description):
    keys = series.map(mapping)
    missing = int(keys.isna().sum())
    if missing:
        raise LoadIntegrityError(f"{description}: {missing} valores sin llave en su dimensión")
    return keys.astype("int64")


def _controls(cur):
    """Medidas de control para comparar antes y después de un rerun (§7.3)."""
    cur.execute("""
        SELECT (SELECT count(*) FROM fact_award),
               (SELECT sum(award_count) FROM fact_award),
               (SELECT count(*) FROM dim_artist WHERE is_awarded),
               (SELECT round(avg(popularity)::numeric, 4) FROM fact_track_artist),
               (SELECT round(avg(energy)::numeric, 6) FROM fact_track_artist)
    """)
    r = cur.fetchone()
    return {"fact_award_filas": r[0], "premios_totales": r[1], "artistas_premiados": r[2],
            "popularidad_media": float(r[3]), "energia_media": float(r[4])}


def run_load(run_id, prepared_dir):
    """Carga los archivos preparados en music_dw y devuelve un resumen pequeño (apto para XCom)."""
    tables = {name: read_prepared(prepared_dir, name) for name in s.PREPARED_COLUMNS}

    conn = _connect()
    try:
        with conn:  # psycopg2: confirma al salir sin error; deshace ante cualquier excepción
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE {', '.join(ALL_TABLES)}")

                keys = {}
                for table, columns, business_key, surrogate_key in DIMENSIONS:
                    _insert(cur, table, tables[table][columns])
                    keys[table] = _key_map(cur, table, business_key, surrogate_key)

                bridge = tables["bridge_track_genre"]
                _insert(cur, "bridge_track_genre", pd.DataFrame({
                    "track_key": _to_keys(bridge["track_id"], keys["dim_track"], "bridge.track_id"),
                    "genre_key": _to_keys(bridge["genre_name"], keys["dim_genre"], "bridge.genre_name"),
                }))

                fa = tables["fact_award"]
                _insert(cur, "fact_award", pd.DataFrame({
                    "year_key": _to_keys(fa["year"], keys["dim_year"], "fact_award.year"),
                    "category_key": _to_keys(fa["category_bk"], keys["dim_category"], "fact_award.category_bk"),
                    "artist_key": _to_keys(fa["artist_bk"], keys["dim_artist"], "fact_award.artist_bk"),
                    "nominee": fa["nominee"],
                    "award_count": fa["award_count"],
                }))

                fta = tables["fact_track_artist"]
                measures = ["popularity", "danceability", "energy", "valence", "acousticness",
                            "tempo", "n_artists", "is_collaboration"]
                _insert(cur, "fact_track_artist", pd.concat([pd.DataFrame({
                    "track_key": _to_keys(fta["track_id"], keys["dim_track"], "fact_track_artist.track_id"),
                    "artist_key": _to_keys(fta["artist_bk"], keys["dim_artist"], "fact_track_artist.artist_bk"),
                }), fta[measures]], axis=1))

                # Verificación antes de confirmar: el DW debe tener exactamente lo preparado
                loaded = {}
                for table in ALL_TABLES:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    loaded[table] = cur.fetchone()[0]
                diffs = {t: (loaded[t], len(tables[t])) for t in ALL_TABLES if loaded[t] != len(tables[t])}
                if diffs:
                    raise LoadIntegrityError(f"Conteos cargados distintos de los preparados (cargado, preparado): {diffs}")
                controls = _controls(cur)
    finally:
        conn.close()

    report = {"run_id": run_id, "loaded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "strategy": "truncate-and-load en una transacción", "rows": loaded, "controls": controls}
    report_path = run_dir(run_id) / "load_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"[load] carga confirmada en {os.environ['DW_DB_NAME']}")
    for table in reversed(ALL_TABLES):
        print(f"  {table}: {loaded[table]} filas")
    print(f"  controles: {controls}")
    return {"rows": loaded, "controls": controls, "report_path": str(report_path)}
