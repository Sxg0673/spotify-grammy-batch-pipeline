# Diseño de validación con Great Expectations

Implementa: `src/gx_setup.py` (definición) y `src/validation.py` (ejecución). Reglas: `docs/quality_rules.md`. GX Core 1.23.2.

Patrón base: el de la práctica de clase (Activity 3 y `candidate_validation.py`): data source de pandas, asset de DataFrame, batch definition del DataFrame completo, expectativas con `severity`, suite, Validation Definition, Checkpoint con `SUMMARY` y decisión por `get_max_severity_failure()`. Diferencia: el contexto es persistente (en archivo), como la propia práctica recomienda para proyectos mayores, y cada expectativa lleva su Rule ID.

## 1. Contexto

- Tipo: contexto en archivo, `gx.get_context(mode="file", project_root_dir=<raíz del proyecto>)`. Vive en `gx/`: localmente en el repo y en el contenedor en `/opt/airflow/gx` (carpeta montada).
- Se versiona `gx/` completo; el `.gitignore` que crea GX excluye `uncommitted/`.
- Ciclo de vida:
  - Definición: `src/gx_setup.py` crea o actualiza data source, assets, batch definitions, suites, Validation Definitions y Checkpoints a partir del código. Es idempotente (`add_or_update`). Se ejecuta una vez y cada vez que cambian las reglas.
  - Ejecución: las tareas del DAG solo cargan el contexto y ejecutan. No modifican definiciones, lo que permite que las dos compuertas raw corran en paralelo.
- Verificado con prueba de humo: contexto en carpeta montada, setup repetible, carga desde otro proceso, ejecución en paralelo y `meta` presente en el resultado.

## 2. Objetos

Data source único: `pandas_src`. Cada dataset tiene asset, batch definition (`<asset>_batch`), suite (`<asset>_suite`) y Validation Definition (`<asset>_vd`).

| Compuerta | Asset | Origen del DataFrame | Ejecución |
|---|---|---|---|
| Raw Spotify | `spotify_raw` | `data/work/<run_id>/raw/spotify_raw.csv` leído con tipos declarados | Checkpoint `spotify_raw_cp` |
| Raw Grammy | `grammy_raw` | `data/work/<run_id>/raw/grammy_raw.csv` leído con tipos declarados | Checkpoint `grammy_raw_cp` |
| Preparada | `dim_artist`, `dim_year`, `dim_category`, `dim_genre`, `dim_track`, `bridge_track_genre`, `fact_award`, `fact_track_artist` | Archivos de `data/work/<run_id>/prepared/` | `vd.run(...)` por tabla |
| Preparada | `prepared_checks` | DataFrame de una fila con métricas derivadas (ver sección 4) | `vd.run(...)` |

Por qué la compuerta preparada no usa un Checkpoint: un Checkpoint con varias Validation Definitions aplica el mismo DataFrame a todas (verificado), y cada tabla necesita el suyo. Se usa `vd.run`, la "ejecución controlada equivalente" que admite el taller (§6.6) y que usa la práctica de clase.

## 3. Política de severidad

La decisión de cada compuerta se toma con la máxima severidad fallida, nunca con `success`: `success` es falso en cuanto falla cualquier expectativa, incluso una Informational (verificado).

| Máxima severidad fallida | Acción | Estado en Airflow |
|---|---|---|
| Ninguna | Continúa | Éxito |
| `info` | Registra y continúa | Éxito |
| `warning` | Registra en log y en el resultado; continúa | Éxito |
| `critical` | Lanza excepción; bloquea el procesamiento posterior | Fallo, sin reintentos (falla determinista) |

En la compuerta preparada la decisión usa la máxima severidad entre las 9 validaciones.

## 4. Mapa de reglas a expectativas

Cada expectativa lleva `meta={"rule_id": ..., "layer": ..., "requirements": ...}`. Las expectativas de rango y de conjunto ignoran nulos, por eso las reglas que exigen completitud agregan una expectativa de no nulo.

### Raw Spotify (`spotify_raw_suite`)

| Rule ID | Expectativa(s) | Severidad |
|---|---|---|
| DQ-S01 | `ExpectTableColumnsToMatchSet` (columnas de D12, exactas); `ExpectTableRowCountToBeBetween(min_value=1)` | critical |
| DQ-S02 | `ExpectColumnValuesToNotBeNull(track_id)` | critical |
| DQ-S03 | `ExpectCompoundColumnsToBeUnique([track_id, track_genre], mostly=0.99)` | warning |
| DQ-S04 | `ExpectColumnValuesToBeBetween(popularity, 0, 100)` | critical |
| DQ-S05 | `ExpectColumnValuesToBeBetween(0, 1)` en `danceability`, `energy`, `valence`, `acousticness` | critical |
| DQ-S06 | `ExpectColumnValuesToBeBetween(tempo, min_value=0)` | critical |
| DQ-S07 | `ExpectColumnValuesToNotBeNull(artists, mostly=0.99)` | warning |
| DQ-S08 | `ExpectColumnValuesToNotBeNull(track_genre, mostly=0.99)` | warning |
| DQ-S09 | `ExpectColumnValuesToBeBetween(tempo, min_value=0, strict_min=True, mostly=0.99)` | info |
| DQ-S10 | `ExpectColumnValuesToBeBetween(popularity, min_value=1, mostly=0.80)` | info |

### Raw Grammy (`grammy_raw_suite`)

| Rule ID | Expectativa(s) | Severidad |
|---|---|---|
| DQ-G01 | `ExpectTableColumnsToMatchSet` (`year`, `category`, `nominee`, `artist`, `winner`); `ExpectTableRowCountToBeBetween(min_value=1)` | critical |
| DQ-G02 | `ExpectColumnValuesToNotBeNull(year)`; `ExpectColumnValuesToBeBetween(year, 1958, 2019)` | critical |
| DQ-G03 | `ExpectColumnValuesToNotBeNull(category)` | critical |
| DQ-G04 | `ExpectColumnValuesToNotBeNull(winner)`; `ExpectColumnValuesToBeInSet(winner, [True])` | critical |
| DQ-G05 | `ExpectCompoundColumnsToBeUnique([year, category, nominee])` | critical |
| DQ-G06 | `ExpectCompoundColumnsToBeUnique([year, category], mostly=0.95)` | warning (se espera que falle con el lote actual por 2019) |
| DQ-G07 | `ExpectColumnValuesToNotBeNull(artist, mostly=0.50)` | warning |
| DQ-G08 | `ExpectColumnValuesToNotBeNull(nominee, mostly=0.99)` | warning |

### Preparada (una suite por tabla)

| Rule ID | Tabla(s) | Expectativa(s) | Severidad |
|---|---|---|---|
| DQ-P01 | Las 8 | `ExpectTableColumnsToMatchSet` (columnas de `docs/transformation_design.md`); `ExpectTableRowCountToBeBetween(min_value=1)` | critical |
| DQ-P02 | Dimensiones | `ExpectColumnValuesToNotBeNull` y `ExpectColumnValuesToBeUnique` en la llave de negocio | critical |
| DQ-P03 | Hechos y puente | `ExpectCompoundColumnsToBeUnique` sobre el grano | critical |
| DQ-P05 | `dim_year`, `fact_award` | `ExpectColumnValuesToBeBetween(year, 1958, 2018)`; `ExpectColumnValuesToBeInSet(decade, [1950..2010])` | critical |
| DQ-P06 | `fact_track_artist` | `popularity` no nulo y entre 0 y 100; `energy` y `acousticness` no nulos y entre 0 y 1; `danceability` y `valence` entre 0 y 1; `tempo` con `strict_min` en 0 | critical |
| DQ-P08 | `fact_track_artist` | `ExpectColumnValuesToBeBetween(n_artists, min_value=1)` | critical |

### Reglas entre filas o entre tablas (`prepared_checks`)

GX Core valida un DataFrame a la vez. Las reglas que cruzan filas o tablas se calculan en `src/validation.py` como un DataFrame de una fila, con una columna por comprobación, y cada columna tiene su expectativa. Así siguen siendo expectativas de GX con su Rule ID.

| Rule ID | Columna | Cálculo | Expectativa | Severidad |
|---|---|---|---|---|
| DQ-P04 | `orphans_<relación>` (una por FK) | Filas del hecho o puente cuya llave no existe en su dimensión | `ExpectColumnValuesToBeBetween(0, 0)` | critical |
| DQ-P07 | `audio_partial_nulls` | Filas donde `tempo`, `danceability` y `valence` no son todas nulas ni todas no nulas | `ExpectColumnValuesToBeBetween(0, 0)` | critical |
| DQ-P08 | `collaboration_mismatches` | Filas donde `is_collaboration` ≠ (`n_artists` > 1) | `ExpectColumnValuesToBeBetween(0, 0)` | critical |
| DQ-P09 | `songs_without_single_representative` | `song_bk` con un número de versiones representativas distinto de 1 | `ExpectColumnValuesToBeBetween(0, 0)` | critical |
| DQ-P10 | `awarded_mismatches` | Diferencia simétrica entre artistas con `is_awarded` y artistas de `fact_award` | `ExpectColumnValuesToBeBetween(0, 0)` | critical |
| DQ-P11 | `match_rate` | `tasa_emparejamiento` de `transform_report.json` | `ExpectColumnValuesToBeBetween(min_value=0.40)` | warning |

## 5. Resultados y evidencia

Por cada validación, en `data/work/<run_id>/validation/`:
- `<vd>.json`: resultado completo de GX (`to_json_dict()`).
- `<compuerta>_summary.json`: por expectativa, `rule_id`, tipo, columna, severidad, éxito, `unexpected_count` y `unexpected_percent`; más la máxima severidad fallida y la acción tomada.

El log de la tarea imprime el mismo resumen, como en la práctica de clase. Las corridas de las pruebas A y B se copian a `docs/evidence/`.
