"""Pipeline batch confiable: Spotify (CSV) + Grammy (PostgreSQL) -> Data Warehouse (music_dw).

Workshop-2, ETL. Apache Airflow 3.1.8 con TaskFlow (airflow.sdk).
Patrón base: Activity 3, Apéndice A (tareas que intercambian rutas, compuertas con >>).
Diseño: docs/dag_design.md. La lógica vive en src/; el DAG solo orquesta.

    extract_spotify -> validate_spotify_raw --+
                                              +-> transform_and_integrate -> validate_prepared -> load_dw
    extract_grammys -> validate_grammys_raw --+

Fallas deterministas (contrato, calidad critical, integridad): AirflowFailException, sin reintento.
Fallas transitorias de base de datos (extract_grammys, load_dw): 3 reintentos cada 30 s.
"""
from datetime import timedelta

import pendulum
from airflow.exceptions import AirflowFailException
from airflow.sdk import Param, dag, get_current_context, task

DB_RETRIES = {"retries": 3, "retry_delay": timedelta(seconds=30)}


def _run(fn, *args):
    """Ejecuta una función de src/ y convierte las fallas deterministas en fallas sin reintento."""
    from src.errors import (CriticalQualityError, LoadIntegrityError,
                            SourceContractError, TransformContractError)
    try:
        return fn(*args)
    except (SourceContractError, TransformContractError, CriticalQualityError, LoadIntegrityError) as exc:
        raise AirflowFailException(f"{type(exc).__name__}: {exc}") from exc


def _run_id():
    return get_current_context()["run_id"]


@dag(
    dag_id="reliable_music_pipeline",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    params={
        "spotify_source": Param(
            "spotify_dataset.csv", type="string",
            enum=["spotify_dataset.csv", "spotify_dataset_bad.csv"],
            description="Archivo de Spotify en data/raw. El valor _bad activa la falla controlada (Test B)."),
        "grammy_table": Param(
            "grammy_awards", type="string",
            enum=["grammy_awards", "grammy_awards_bad"],
            description="Tabla de Grammy en grammy_source. El valor _bad activa la falla controlada (Test B)."),
    },
    tags=["etl", "gx", "reliable-pipeline", "workshop-2"],
    doc_md=__doc__,
)
def reliable_music_pipeline():

    # ======================================================================
    # STAGE 1 - EXTRACT
    # ======================================================================
    @task
    def extract_spotify():
        from src.extract import DATA_DIR, extract_spotify as run
        context = get_current_context()
        source = DATA_DIR / "raw" / context["params"]["spotify_source"]
        print(f"[batch] run_id={context['run_id']} | spotify_source={source}")
        return _run(run, context["run_id"], source)

    @task(**DB_RETRIES)
    def extract_grammys():
        from src.extract import extract_grammys as run
        context = get_current_context()
        table = context["params"]["grammy_table"]
        print(f"[batch] run_id={context['run_id']} | grammy_table={table}")
        return _run(run, context["run_id"], table)

    # ======================================================================
    # STAGE 2 - RAW VALIDATION GATES
    # ======================================================================
    @task
    def validate_spotify_raw(raw_path):
        from src.validation import run_raw_gate
        return _run(run_raw_gate, _run_id(), "spotify", raw_path)

    @task
    def validate_grammys_raw(raw_path):
        from src.validation import run_raw_gate
        return _run(run_raw_gate, _run_id(), "grammy", raw_path)

    # ======================================================================
    # STAGE 3 - TRANSFORM AND INTEGRATE
    # ======================================================================
    @task
    def transform_and_integrate(spotify_raw_path, grammy_raw_path):
        from src.transform import run_transform
        return _run(run_transform, _run_id(), spotify_raw_path, grammy_raw_path)

    # ======================================================================
    # STAGE 4 - PREPARED VALIDATION GATE
    # ======================================================================
    @task
    def validate_prepared(prepared_dir):
        from src.validation import run_prepared_gate
        return _run(run_prepared_gate, _run_id(), prepared_dir)

    # ======================================================================
    # STAGE 5 - LOAD
    # ======================================================================
    @task(**DB_RETRIES)
    def load_dw(prepared_dir):
        from src.load import run_load
        return _run(run_load, _run_id(), prepared_dir)

    # ======================================================================
    # BUILD THE WORKFLOW
    # ======================================================================
    spotify_raw = extract_spotify()
    grammy_raw = extract_grammys()
    spotify_gate = validate_spotify_raw(spotify_raw)
    grammy_gate = validate_grammys_raw(grammy_raw)

    prepared_dir = transform_and_integrate(spotify_raw, grammy_raw)
    # La transformación solo procede si ambas compuertas raw cumplen la política
    [spotify_gate, grammy_gate] >> prepared_dir

    prepared_gate = validate_prepared(prepared_dir)
    loaded = load_dw(prepared_dir)
    # La carga solo procede si la compuerta preparada cumple la política
    prepared_gate >> loaded


reliable_music_pipeline()
