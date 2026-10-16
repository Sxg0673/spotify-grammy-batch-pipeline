"""Reconciliación de la fuente Grammy: CSV original vs tabla grammy_source.grammy_awards.

Evidencia del taller (§6.2): conteo de filas y reconciliación con el CSV.
Tres niveles: (1) conteos, (2) estadísticos por columna, (3) contenido fila a fila.
Se ejecuta dentro del contenedor de Airflow como etl_user (solo lectura sobre la fuente).
El JSON se imprime por stdout; el resumen, por stderr. Sale con código 1 si algo difiere.
"""
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

CSV_PATH = Path(os.environ.get("PIPELINE_DATA_DIR", "/opt/airflow/data")) / "raw" / "the_grammy_awards.csv"
COLS = ["year", "title", "published_at", "updated_at", "category", "nominee", "artist", "workers", "img", "winner"]
TS_COLS = {"published_at", "updated_at"}

# Valores medidos en el profiling (notebooks/data_profiling.ipynb, celdas 5 y 6)
EXPECTED = {
    "rows": 4810,
    "nulls": {"year": 0, "title": 0, "published_at": 0, "updated_at": 0, "category": 0,
              "nominee": 6, "artist": 1840, "workers": 2190, "img": 1367, "winner": 0},
    "distinct": {"year": 62, "title": 62, "published_at": 4, "updated_at": 10, "category": 638,
                 "nominee": 4131, "artist": 1658, "workers": 2366, "img": 1463, "winner": 1},
    "year_min": 1958, "year_max": 2019, "winner_true": 4810,
    "sha256_prefix": "bae3d6613c",
}


def _utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def canon_csv_row(row):
    out = []
    for c in COLS:
        v = row[c]
        if v == "":
            out.append(None)
        elif c == "year":
            out.append(int(v))
        elif c in TS_COLS:
            out.append(_utc_iso(datetime.fromisoformat(v)))
        elif c == "winner":
            out.append(v == "True")
        else:
            out.append(v)
    return out


def canon_db_row(row):
    out = []
    for c, v in zip(COLS, row):
        out.append(_utc_iso(v) if (c in TS_COLS and v is not None) else v)
    return out


def row_hash(canon):
    return hashlib.sha256(json.dumps(canon, ensure_ascii=False).encode("utf-8")).hexdigest()


def csv_stats(canon_rows):
    stats = {"rows": len(canon_rows), "nulls": {}, "distinct": {}}
    for i, c in enumerate(COLS):
        vals = [r[i] for r in canon_rows]
        stats["nulls"][c] = sum(v is None for v in vals)
        stats["distinct"][c] = len({v for v in vals if v is not None})
    years = [r[0] for r in canon_rows if r[0] is not None]
    stats["year_min"], stats["year_max"] = min(years), max(years)
    stats["winner_true"] = sum(r[9] is True for r in canon_rows)
    return stats


def table_stats(cur):
    parts = ["count(*)"]
    for c in COLS:
        parts += [f"count(*) FILTER (WHERE {c} IS NULL)", f"count(DISTINCT {c})"]
    parts += ["min(year)", "max(year)", "count(*) FILTER (WHERE winner)"]
    text_cols = [c for c in COLS if c not in TS_COLS | {"year", "winner"}]
    parts.append("(" + " + ".join(f"count(*) FILTER (WHERE {c} = '')" for c in text_cols) + ")")
    cur.execute("SELECT " + ", ".join(parts) + " FROM grammy_awards")
    r = cur.fetchone()
    stats = {"rows": r[0], "nulls": {}, "distinct": {}}
    for i, c in enumerate(COLS):
        stats["nulls"][c] = r[1 + 2 * i]
        stats["distinct"][c] = r[2 + 2 * i]
    k = 1 + 2 * len(COLS)
    stats["year_min"], stats["year_max"], stats["winner_true"], stats["empty_strings"] = r[k], r[k + 1], r[k + 2], r[k + 3]
    return stats


def main():
    checks = []

    def check(name, expected, csv_v, table_v):
        checks.append({"check": name, "expected": expected, "csv": csv_v, "table": table_v,
                       "ok": csv_v == expected and table_v == expected})

    raw = CSV_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    csv_canon = [canon_csv_row(r) for r in rows]
    cs = csv_stats(csv_canon)

    conn = psycopg2.connect(host=os.environ["DATA_PG_HOST"], port=os.environ["DATA_PG_PORT"],
                            user=os.environ["DATA_PG_USER"], password=os.environ["DATA_PG_PASSWORD"],
                            dbname=os.environ["SOURCE_DB_NAME"])
    try:
        cur = conn.cursor()
        ts = table_stats(cur)
        cur.execute("SELECT " + ", ".join(COLS) + " FROM grammy_awards ORDER BY id")
        db_canon = [canon_db_row(r) for r in cur.fetchall()]
    finally:
        conn.close()

    # Nivel 1 y 2: conteos y estadísticos, contra el profiling y entre sí
    check("filas", EXPECTED["rows"], cs["rows"], ts["rows"])
    for c in COLS:
        check(f"nulos.{c}", EXPECTED["nulls"][c], cs["nulls"][c], ts["nulls"][c])
        check(f"distintos.{c}", EXPECTED["distinct"][c], cs["distinct"][c], ts["distinct"][c])
    check("year_min", EXPECTED["year_min"], cs["year_min"], ts["year_min"])
    check("year_max", EXPECTED["year_max"], cs["year_max"], ts["year_max"])
    check("winner_true", EXPECTED["winner_true"], cs["winner_true"], ts["winner_true"])
    checks.append({"check": "cadenas_vacias_en_tabla", "expected": 0, "csv": None,
                   "table": ts["empty_strings"], "ok": ts["empty_strings"] == 0})
    checks.append({"check": "sha256_csv_prefijo", "expected": EXPECTED["sha256_prefix"],
                   "csv": sha[:10], "table": None, "ok": sha.startswith(EXPECTED["sha256_prefix"])})

    # Nivel 3: contenido fila a fila (multiconjunto de hashes + orden de carga)
    csv_hashes = [row_hash(r) for r in csv_canon]
    db_hashes = [row_hash(r) for r in db_canon]
    diff_csv, diff_db = Counter(csv_hashes) - Counter(db_hashes), Counter(db_hashes) - Counter(csv_hashes)
    checks.append({"check": "filas_solo_en_csv", "expected": 0, "csv": sum(diff_csv.values()), "table": None,
                   "ok": not diff_csv})
    checks.append({"check": "filas_solo_en_tabla", "expected": 0, "csv": None, "table": sum(diff_db.values()),
                   "ok": not diff_db})
    checks.append({"check": "mismo_orden_de_carga", "expected": True, "csv": None,
                   "table": csv_hashes == db_hashes, "ok": csv_hashes == db_hashes})

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "csv_file": CSV_PATH.name, "csv_sha256": sha,
        "table": "grammy_source.grammy_awards", "db_user": os.environ["DATA_PG_USER"],
        "all_ok": all(c["ok"] for c in checks), "checks": checks,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    failed = [c["check"] for c in checks if not c["ok"]]
    print(f"Reconciliación: {len(checks) - len(failed)}/{len(checks)} comprobaciones OK"
          + (f" | FALLAN: {failed}" if failed else ""), file=sys.stderr)
    sys.exit(0 if report["all_ok"] else 1)


if __name__ == "__main__":
    main()
