# Arquitectura del pipeline

## 1. Vista conceptual

~~~mermaid
flowchart LR
    subgraph FUENTES["Fuentes"]
        CSV["Spotify CSV<br/>114,000 filas<br/>data/raw"]
        SRC[("PostgreSQL grammy_source<br/>tabla grammy_awards<br/>4,810 filas")]
    end

    subgraph AIRFLOW["Apache Airflow 3.1.8 en Docker"]
        EX["Extracción<br/>extract_spotify<br/>extract_grammys"]
        VR{{"Validación raw<br/>GX: spotify_raw_suite<br/>grammy_raw_suite"}}
        TR["Transformación e integración<br/>transform_and_integrate"]
        VP{{"Validación preparada<br/>GX: 8 suites por tabla<br/>+ prepared_checks_suite"}}
        LD["Carga<br/>load_dw<br/>una sola transacción"]
    end

    subgraph WORK["Área de trabajo por run<br/>data/work/run_id"]
        RAW["raw/"]
        VAL["validation/"]
        PREP["prepared/"]
    end

    subgraph DW["PostgreSQL music_dw"]
        MODEL[("Modelo dimensional<br/>fact_award, fact_track_artist<br/>5 dimensiones + bridge_track_genre")]
        VIEWS["Vistas de KPI<br/>v_kpi_*"]
    end

    GX[("Contexto GX persistente<br/>gx/")]
    BI["Tableau Desktop<br/>dashboard_user, solo lectura"]
    STOP["Run detenido<br/>AirflowFailException"]

    CSV --> EX
    SRC -->|"etl_user, solo lectura"| EX
    EX --> RAW
    RAW --> VR
    VR -->|"pasa o warning"| TR
    VR -->|"falla critical"| STOP
    TR --> PREP
    PREP --> VP
    VP -->|"pasa o warning"| LD
    VP -->|"falla critical"| STOP
    LD --> MODEL
    MODEL --> VIEWS
    VIEWS --> BI
    VR -.-> VAL
    VP -.-> VAL
    GX -.-> VR
    GX -.-> VP
~~~

Cómo se lee:

- Las dos fuentes se extraen por separado. La fuente Grammy vive en su propia base y el pipeline la lee con un usuario de solo lectura.
- Cada run trabaja en su propia carpeta `data/work/<run_id>`, con los datos crudos, los resultados de validación y los datos preparados. Así un run no pisa a otro y cada uno deja su evidencia.
- Hay dos compuertas de calidad con Great Expectations: una sobre los datos crudos y otra sobre los datos preparados. Una falla `critical` detiene el run antes de tocar el DW. Una falla `warning` deja continuar y queda registrada.
- La carga reemplaza el contenido del DW en una sola transacción. Si falla, el DW queda como estaba.
- Tableau solo lee las vistas `v_kpi_*`, que fijan las reglas de cálculo en SQL.

## 2. Estructura del DAG

DAG `reliable_music_pipeline`: ejecución manual (`schedule=None`) con los parámetros `spotify_source` y `grammy_table`.

~~~mermaid
flowchart LR
    ES["extract_spotify"] --> VS{{"validate_spotify_raw"}}
    EG["extract_grammys<br/>retries=3, 30 s"] --> VG{{"validate_grammys_raw"}}
    VS --> T["transform_and_integrate"]
    VG --> T
    T --> VPR{{"validate_prepared"}}
    VPR --> L["load_dw<br/>retries=3, 30 s"]
~~~

| Tarea | Qué hace | Deja en el área del run | Reintentos |
| --- | --- | --- | --- |
| `extract_spotify` | Lee el CSV de Spotify y verifica su contrato de columnas | `raw/` | 1, a los 10 s |
| `extract_grammys` | Lee la tabla `grammy_awards` de la fuente PostgreSQL | `raw/` | 3, cada 30 s |
| `validate_spotify_raw` | Ejecuta la suite raw de Spotify y aplica la política de severidad | `validation/` | 1, a los 10 s |
| `validate_grammys_raw` | Ejecuta la suite raw de Grammy y aplica la política de severidad | `validation/` | 1, a los 10 s |
| `transform_and_integrate` | Limpia, armoniza, cruza las fuentes y arma las tablas del modelo | `prepared/` y reporte de transformación | 1, a los 10 s |
| `validate_prepared` | Ejecuta las suites de la capa preparada | `validation/` | 1, a los 10 s |
| `load_dw` | Recarga el DW en una sola transacción | reporte de carga | 3, cada 30 s |

Los errores deterministas (contrato de la fuente, contrato de transformación, falla de calidad `critical` e integridad de carga) se convierten en `AirflowFailException` y no se reintentan, porque repetir no cambia el resultado. Solo las tareas que dependen de una base de datos tienen reintentos amplios. Detalle en `docs/dag_design.md`.

## 3. Despliegue

- Todo corre con Docker Compose. Airflow usa su propia base de metadatos.
- El contenedor `postgres-data` aloja dos bases: `grammy_source` (fuente) y `music_dw` (DW).
- El Triggerer no se despliega porque el DAG no usa tareas diferibles. Por eso la vista de salud de Airflow lo marca en rojo (EV-02).
- Las credenciales viven en `.env`, que no se versiona. `.env.example` tiene la plantilla.

## 4. Decisiones de arquitectura

| Decisión | Motivo |
| --- | --- |
| Fuente Grammy en PostgreSQL separado del DW | Simula una fuente operacional real y obliga a extraer por conexión, con usuario de solo lectura |
| Carpeta de trabajo por run | Aislamiento entre ejecuciones y evidencia trazable de cada run |
| Validación antes y después de transformar | Detecta problemas de origen y errores propios de la transformación por separado |
| Severidad critical, warning e info | No todo problema de calidad debe detener el pipeline. Ver `docs/quality_rules.md` |
| Carga con TRUNCATE y recarga en una transacción | Repetir un run no duplica datos (recarga segura) y una falla no deja el DW a medias |
| Vistas de KPI y rol de solo lectura para BI | Reglas de cálculo versionadas y mínimo privilegio para el dashboard |
