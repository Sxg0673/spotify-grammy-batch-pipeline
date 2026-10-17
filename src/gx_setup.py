"""Definición de Great Expectations en un contexto en archivo (gx/).

Crea o actualiza, de forma repetible: data source, assets, batch definitions, suites,
Validation Definitions y Checkpoints. Sigue el patrón de la práctica de clase
(candidate_validation.py): pandas data source -> dataframe asset -> whole dataframe batch
-> suite con severidades -> validation definition -> checkpoint (SUMMARY).
Diferencias (docs/gx_design.md): contexto persistente y Rule ID en el meta de cada expectativa.

Uso, dentro del contenedor:
    python -m src.gx_setup > docs/gx_expectation_map.md
El inventario se imprime por stderr y el mapa expectativa -> Rule ID por stdout.
"""
import json
import sys
from pathlib import Path

import great_expectations as gx
import great_expectations.expectations as gxe

from src import schemas as s

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_SOURCE_NAME = "music_pandas_source"
RESULT_FORMAT = {"result_format": "SUMMARY"}


def log(msg):
    print(msg, file=sys.stderr)


def meta(rule_id, layer, requirements):
    return {"rule_id": rule_id, "layer": layer, "requirements": requirements}


# ---------------------------------------------------------
# Expectativas por suite (docs/gx_design.md, sección 4)
# ---------------------------------------------------------

def spotify_raw_expectations():
    m = lambda rule, req: meta(rule, "raw", req)
    exps = [
        gxe.ExpectTableColumnsToMatchSet(column_set=s.SPOTIFY_RAW_COLUMNS, exact_match=True, severity="critical", meta=m("DQ-S01", "R1-R4")),
        gxe.ExpectTableRowCountToBeBetween(min_value=1, severity="critical", meta=m("DQ-S01", "R1-R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="track_id", severity="critical", meta=m("DQ-S02", "R1-R4")),
        gxe.ExpectCompoundColumnsToBeUnique(column_list=["track_id", "track_genre"], mostly=0.99, severity="warning", meta=m("DQ-S03", "R1-R4")),
        gxe.ExpectColumnValuesToBeBetween(column="popularity", min_value=0, max_value=100, severity="critical", meta=m("DQ-S04", "R1,R4")),
    ]
    for col in ["danceability", "energy", "valence", "acousticness"]:
        exps.append(gxe.ExpectColumnValuesToBeBetween(column=col, min_value=0, max_value=1, severity="critical", meta=m("DQ-S05", "R1")))
    exps += [
        gxe.ExpectColumnValuesToBeBetween(column="tempo", min_value=0, severity="critical", meta=m("DQ-S06", "R1")),
        gxe.ExpectColumnValuesToNotBeNull(column="artists", mostly=0.99, severity="warning", meta=m("DQ-S07", "R1-R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="track_genre", mostly=0.99, severity="warning", meta=m("DQ-S08", "R2")),
        gxe.ExpectColumnValuesToBeBetween(column="tempo", min_value=0, strict_min=True, mostly=0.99, severity="info", meta=m("DQ-S09", "R1")),
        gxe.ExpectColumnValuesToBeBetween(column="popularity", min_value=1, mostly=0.80, severity="info", meta=m("DQ-S10", "R1,R4")),
    ]
    return exps


def grammy_raw_expectations():
    m = lambda rule, req: meta(rule, "raw", req)
    return [
        gxe.ExpectTableColumnsToMatchSet(column_set=s.GRAMMY_RAW_COLUMNS, exact_match=True, severity="critical", meta=m("DQ-G01", "R1-R4")),
        gxe.ExpectTableRowCountToBeBetween(min_value=1, severity="critical", meta=m("DQ-G01", "R1-R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="year", severity="critical", meta=m("DQ-G02", "R1,R3")),
        gxe.ExpectColumnValuesToBeBetween(column="year", min_value=s.YEAR_MIN, max_value=s.RAW_YEAR_MAX, severity="critical", meta=m("DQ-G02", "R1,R3")),
        gxe.ExpectColumnValuesToNotBeNull(column="category", severity="critical", meta=m("DQ-G03", "R1-R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="winner", severity="critical", meta=m("DQ-G04", "R1,R3,R4")),
        gxe.ExpectColumnValuesToBeInSet(column="winner", value_set=[True], severity="critical", meta=m("DQ-G04", "R1,R3,R4")),
        gxe.ExpectCompoundColumnsToBeUnique(column_list=["year", "category", "nominee"], severity="critical", meta=m("DQ-G05", "R4")),
        gxe.ExpectCompoundColumnsToBeUnique(column_list=["year", "category"], mostly=0.95, severity="warning", meta=m("DQ-G06", "R1,R3,R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="artist", mostly=0.50, severity="warning", meta=m("DQ-G07", "R1-R4")),
        gxe.ExpectColumnValuesToNotBeNull(column="nominee", mostly=0.99, severity="warning", meta=m("DQ-G08", "R1,R3,R4")),
    ]


def prepared_expectations(table):
    m = lambda rule, req: meta(rule, "prepared", req)
    exps = [
        gxe.ExpectTableColumnsToMatchSet(column_set=s.PREPARED_COLUMNS[table], exact_match=True, severity="critical", meta=m("DQ-P01", "R1-R4")),
        gxe.ExpectTableRowCountToBeBetween(min_value=1, severity="critical", meta=m("DQ-P01", "R1-R4")),
    ]
    if table in s.DIMENSION_KEYS:
        key = s.DIMENSION_KEYS[table]
        exps += [
            gxe.ExpectColumnValuesToNotBeNull(column=key, severity="critical", meta=m("DQ-P02", "R1-R4")),
            gxe.ExpectColumnValuesToBeUnique(column=key, severity="critical", meta=m("DQ-P02", "R1-R4")),
        ]
    if table in s.GRAINS:
        exps.append(gxe.ExpectCompoundColumnsToBeUnique(column_list=s.GRAINS[table], severity="critical", meta=m("DQ-P03", "R1-R4")))
    if table in ("dim_year", "fact_award"):
        exps.append(gxe.ExpectColumnValuesToBeBetween(column="year", min_value=s.YEAR_MIN, max_value=s.PREPARED_YEAR_MAX, severity="critical", meta=m("DQ-P05", "R1,R3")))
    if table == "dim_year":
        exps.append(gxe.ExpectColumnValuesToBeInSet(column="decade", value_set=s.DECADES, severity="critical", meta=m("DQ-P05", "R1,R3")))
    if table == "fact_track_artist":
        p06 = m("DQ-P06", "R1,R4")
        exps += [
            gxe.ExpectColumnValuesToNotBeNull(column="popularity", severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="popularity", min_value=0, max_value=100, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToNotBeNull(column="energy", severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="energy", min_value=0, max_value=1, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToNotBeNull(column="acousticness", severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="acousticness", min_value=0, max_value=1, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="danceability", min_value=0, max_value=1, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="valence", min_value=0, max_value=1, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="tempo", min_value=0, strict_min=True, severity="critical", meta=p06),
            gxe.ExpectColumnValuesToBeBetween(column="n_artists", min_value=1, severity="critical", meta=m("DQ-P08", "R3")),
        ]
    return exps


def prepared_checks_expectations():
    m = lambda rule, req: meta(rule, "prepared", req)
    exps = [
        gxe.ExpectTableColumnsToMatchSet(column_set=s.PREPARED_CHECK_COLUMNS, exact_match=True, severity="critical", meta=m("DQ-P01", "R1-R4")),
    ]
    for check_col, *_ in s.FOREIGN_KEYS:
        exps.append(gxe.ExpectColumnValuesToBeBetween(column=check_col, min_value=0, max_value=0, severity="critical", meta=m("DQ-P04", "R1-R4")))
    exps += [
        gxe.ExpectColumnValuesToBeBetween(column="audio_partial_nulls", min_value=0, max_value=0, severity="critical", meta=m("DQ-P07", "R1")),
        gxe.ExpectColumnValuesToBeBetween(column="collaboration_mismatches", min_value=0, max_value=0, severity="critical", meta=m("DQ-P08", "R3")),
        gxe.ExpectColumnValuesToBeBetween(column="songs_without_single_representative", min_value=0, max_value=0, severity="critical", meta=m("DQ-P09", "R1,R3,R4")),
        gxe.ExpectColumnValuesToBeBetween(column="awarded_mismatches", min_value=0, max_value=0, severity="critical", meta=m("DQ-P10", "R1-R4")),
        gxe.ExpectColumnValuesToBeBetween(column="match_rate", min_value=s.MIN_MATCH_RATE, severity="warning", meta=m("DQ-P11", "R1-R4")),
    ]
    return exps


# ---------------------------------------------------------
# Registro en el contexto
# ---------------------------------------------------------

def get_context():
    return gx.get_context(mode="file", project_root_dir=str(PROJECT_ROOT))


def upsert(factory, obj):
    if hasattr(factory, "add_or_update"):
        return factory.add_or_update(obj)
    try:
        factory.delete(obj.name)
    except Exception:
        pass
    return factory.add(obj)


def get_data_source(ctx):
    try:
        return ctx.data_sources.get(DATA_SOURCE_NAME)
    except Exception:
        return ctx.data_sources.add_pandas(name=DATA_SOURCE_NAME)


def _signature(expectations):
    """Configuración de las expectativas sin identificadores (GX los regenera al guardar),
    ordenada (el orden de guardado de GX no es el de definición)."""
    firmas = []
    for expectation in expectations:
        try:
            config = expectation.configuration.to_json_dict()
        except AttributeError:
            config = expectation.model_dump(mode="json")
        config.pop("id", None)
        firmas.append(json.dumps(config, sort_keys=True, default=str))
    return sorted(firmas)


def register(ctx, data_source, asset_name, expectations, with_checkpoint):
    # Data Asset y Batch Definition (DataFrame completo, como en clase)
    try:
        asset = data_source.get_asset(asset_name)
    except Exception:
        asset = data_source.add_dataframe_asset(name=asset_name)
    batch_name = f"{asset_name}_batch"
    try:
        batch_definition = asset.get_batch_definition(batch_name)
    except Exception:
        batch_definition = asset.add_batch_definition_whole_dataframe(batch_name)

    # Expectation Suite: solo se reescribe si alguna regla cambió.
    # La suite guardada se lee ANTES de construir la nueva: en GX, agregar expectativas
    # a una suite con el mismo nombre las suma a la guardada.
    suite_name = f"{asset_name}_suite"
    try:
        existing = ctx.suites.get(suite_name)
    except Exception:
        existing = None
    if existing is not None and _signature(existing.expectations) == _signature(expectations):
        suite, status = existing, "sin cambios"
    else:
        new_suite = gx.ExpectationSuite(name=suite_name)
        for expectation in expectations:
            new_suite.add_expectation(expectation)
        suite = upsert(ctx.suites, new_suite)
        status = "actualizada" if existing is not None else "creada"

    # Validation Definition
    validation_definition = upsert(
        ctx.validation_definitions,
        gx.ValidationDefinition(name=f"{asset_name}_validation_definition", data=batch_definition, suite=suite),
    )

    message = f"{asset_name}: suite {status} ({len(suite.expectations)} expectativas), validation definition registrada"

    # Checkpoint (solo compuertas raw; ver docs/gx_design.md, sección 2)
    if with_checkpoint:
        upsert(ctx.checkpoints, gx.Checkpoint(
            name=f"{asset_name}_checkpoint",
            validation_definitions=[validation_definition],
            actions=[],
            result_format=RESULT_FORMAT,
        ))
        message += ", checkpoint registrado"
    log(message)


# ---------------------------------------------------------
# Mapa expectativa -> Rule ID (evidencia §6.6)
# ---------------------------------------------------------

def _columns(expectation):
    if "Table" in type(expectation).__name__:
        return "(tabla)"
    for attr in ("column", "column_list"):
        value = getattr(expectation, attr, None)
        if value:
            return ", ".join(value) if isinstance(value, (list, tuple)) else str(value)
    return "-"


def _params(expectation):
    parts = []
    for attr in ("min_value", "max_value", "strict_min", "value_set", "mostly"):
        value = getattr(expectation, attr, None)
        if value is not None and value is not False:
            parts.append(f"{attr}={value}")
    return ", ".join(parts) or "-"


def expectation_map(ctx, asset_names):
    lines = [
        "# Mapa de expectativas de GX a reglas de calidad",
        "",
        "Generado por `src/gx_setup.py` desde las suites registradas en `gx/`. No editar a mano.",
        "",
        "| Suite | Rule ID | Expectativa | Columna(s) | Parámetros | Severidad | Requerimientos |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in asset_names:
        suite = ctx.suites.get(f"{name}_suite")
        for e in suite.expectations:
            m = e.meta or {}
            severity = getattr(e.severity, "value", e.severity)
            lines.append(f"| `{suite.name}` | {m.get('rule_id', '-')} | `{type(e).__name__}` | {_columns(e)} | {_params(e)} | {severity} | {m.get('requirements', '-')} |")
    return "\n".join(lines)


def main():
    ctx = get_context()
    data_source = get_data_source(ctx)
    log(f"Contexto GX: {PROJECT_ROOT / 'gx'} | data source: {data_source.name}")

    plan = [("spotify_raw", spotify_raw_expectations(), True),
            ("grammy_raw", grammy_raw_expectations(), True)]
    plan += [(table, prepared_expectations(table), False) for table in s.PREPARED_COLUMNS]
    plan += [("prepared_checks", prepared_checks_expectations(), False)]

    for asset_name, expectations, with_checkpoint in plan:
        register(ctx, data_source, asset_name, expectations, with_checkpoint)

    log(f"Inventario: {len(list(ctx.suites.all()))} suites | "
        f"{len(list(ctx.validation_definitions.all()))} validation definitions | "
        f"{len(list(ctx.checkpoints.all()))} checkpoints")
    print(expectation_map(ctx, [p[0] for p in plan]))


if __name__ == "__main__":
    main()
