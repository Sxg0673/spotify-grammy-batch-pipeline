# Reglas de calidad de datos

Estado: capas raw y preparada definidas.

Fuente de evidencia: `notebooks/data_profiling.ipynb` (los números entre paréntesis son celdas del notebook; RS/RK/RG/RX son los riesgos registrados en él).

## Política de severidad

| Severidad | Significado | Acción del pipeline | Severidad en GX |
|---|---|---|---|
| Critical | Rompe la identidad, el contrato o la estructura; continuar no es seguro | La tarea de validación falla y el procesamiento posterior se bloquea | `critical` |
| Warning | Reduce la cobertura o la representatividad de un requerimiento; la transformación lo maneja | Se registra en el log y en el resultado de validación; el pipeline continúa | `warning` |
| Informational | Señal de monitoreo o tendencia | Se registra; nunca bloquea | `info` |

## Convenciones

- Prefijos de Rule ID: `DQ-S` (raw Spotify), `DQ-G` (raw Grammy), `DQ-P` (capa preparada).
- Una regla puede implementarse con una o más expectativas de GX; cada expectativa lleva su `rule_id` en `meta`.
- Las reglas cubren solo los atributos usados por R1–R4, más las reglas estructurales (decisión D12).
- Cada umbral se justifica por la evidencia del profiling, el contrato de la fuente o el requerimiento que protege, no por el resultado del lote actual.

## Capa raw: Spotify (`spotify_raw`)

| Rule ID | Atributo(s) | Dimensión | Regla | Métrica / umbral | Severidad | Justificación | Riesgo | Req. |
|---|---|---|---|---|---|---|---|---|
| DQ-S01 | Columnas requeridas | Estructura | El lote contiene exactamente las columnas requeridas y al menos 1 fila | 100 % | Critical | Sin estas columnas no se puede responder R1–R4 (D12) | RS01 | R1–R4 |
| DQ-S02 | `track_id` | Completitud | `track_id` nunca es nulo | 100 % | Critical | Identidad de la pista; 0 nulos observados (6) | RK01 | R1–R4 |
| DQ-S03 | `track_id`, `track_genre` | Unicidad | El grano de la fuente (pista × género) es único | ≤ 1 % de filas duplicadas | Warning | 0.39 % de duplicados exactos (45), eliminados por D6; el umbral detecta un crecimiento anómalo | RK02 | R1–R4 |
| DQ-S04 | `popularity` | Validez | Entre 0 y 100 | 100 % | Critical | Contrato de Spotify: popularidad 0–100 | RK03, RK04 | R1, R4 |
| DQ-S05 | `danceability`, `energy`, `valence`, `acousticness` | Validez | Entre 0 y 1 | 100 % | Critical | Contrato de Spotify: escala 0.0–1.0; hoy 100 % en rango (18) | RK10 | R1 |
| DQ-S06 | `tempo` | Validez | Mayor o igual a 0 | 100 % | Critical | Tempo estimado en BPM no puede ser negativo; el 0 se reserva para "sin análisis" (D9) | RK09 | R1 |
| DQ-S07 | `artists` | Completitud | `artists` no es nulo | ≥ 99 % | Warning | Sin artista no hay integración (D14); 1 nulo observado (10); perder más del 1 % cambiaría la cobertura por artista | RK05 | R1–R4 |
| DQ-S08 | `track_genre` | Completitud | `track_genre` no es nulo | ≥ 99 % | Warning | R2 requiere el género; 0 nulos observados (6) | RK11 | R2 |
| DQ-S09 | `tempo` | Monitoreo | Filas con análisis de audio (`tempo` > 0) | ≥ 99 % | Informational | 157 filas sin análisis, 0.14 % (48); monitorea D9 | RK09 | R1 |
| DQ-S10 | `popularity` | Monitoreo | Filas con `popularity` mayor que 0 | ≥ 80 % | Informational | 85.9 % hoy; con más del 20 % de ceros los KPI de vigencia pierden confiabilidad (51) | RK04 | R1, R4 |

## Capa raw: Grammy (`grammy_raw`)

| Rule ID | Atributo(s) | Dimensión | Regla | Métrica / umbral | Severidad | Justificación | Riesgo | Req. |
|---|---|---|---|---|---|---|---|---|
| DQ-G01 | Columnas requeridas | Estructura | El lote contiene exactamente las columnas requeridas y al menos 1 fila | 100 % | Critical | Sin estas columnas no se puede responder R1–R4 (D12) | RS01 | R1–R4 |
| DQ-G02 | `year` | Validez | Entero entre 1958 y el año de ejecución | 100 % | Critical | Primer año de la fuente: 1958 (21); un año fuera de rango rompe la década (D16) | RG06 | R1, R3 |
| DQ-G03 | `category` | Completitud | `category` nunca es nula | 100 % | Critical | Forma parte del grano del premio y la usa D2; 0 nulos observados (6) | RG03 | R1–R4 |
| DQ-G04 | `winner` | Validez | Solo toma el valor `True` | 100 % | Critical | Contrato semántico de la fuente: solo ganadores (15); la definición de premiado depende de él (D15) | RG01 | R1, R3, R4 |
| DQ-G05 | `year`, `category`, `nominee` | Unicidad | Un premio no se repite | 100 % | Critical | 0 duplicados observados (13); un duplicado inflaría el conteo de premios | RG04 | R4 |
| DQ-G06 | `year`, `category` | Consistencia | Una categoría por año casi siempre tiene un solo ganador | ≥ 95 % de filas únicas | Warning | Entre 1958 y 2018 los empates no pasan del 2.4 % de grupos por año (30); detecta lotes contaminados con nominados, como 2019. Se espera que falle con el lote actual; D1 lo resuelve | RG01 | R1, R3, R4 |
| DQ-G07 | `artist` | Completitud | `artist` no es nulo | ≥ 50 % | Warning | Los nulos son estructurales por categoría (33); hoy 61.75 %; por debajo del 50 % la mayoría de premios no sería atribuible | RG02 | R1–R4 |
| DQ-G08 | `nominee` | Completitud | `nominee` no es nulo | ≥ 99 % | Warning | 0.125 % nulo, 6 filas (34); D2 depende de `nominee` | RG03 | R1, R3, R4 |

## Capa preparada (`prepared`)

Valida los archivos de `data/work/<run_id>/prepared/` antes de la carga. Pregunta del gate (§6.9): ¿la transformación produjo datos aptos para cargar?

| Rule ID | Tabla(s) | Dimensión | Regla | Métrica / umbral | Severidad | Justificación | Req. |
|---|---|---|---|---|---|---|---|
| DQ-P01 | Todas | Estructura | Cada archivo tiene las columnas esperadas y al menos 1 fila | 100 % | Critical | Esquema del modelo (`docs/dimensional_model.md`) | R1–R4 |
| DQ-P02 | Dimensiones | Unicidad | Llaves de negocio únicas: `artist_bk`, `track_id`, `year`, `category_bk`, `genre_name` | 100 % | Critical | Invariante de D17, D18 y de S3 | R1–R4 |
| DQ-P03 | Hechos y puente | Unicidad | Grano único: (`year`, `category_bk`, `nominee`, `artist_bk`); (`track_id`, `artist_bk`); (`track_id`, `genre_name`) | 100 % | Critical | Invariante de D4, D6 y D7 | R1–R4 |
| DQ-P04 | Hechos y puente | Integridad | Toda llave de un hecho o del puente existe en su dimensión | 100 % | Critical | La carga exige integridad referencial | R1–R4 |
| DQ-P05 | `dim_year`, `fact_award` | Validez | `year` entre 1958 y 2018; `decade` en {1950, …, 2010} | 100 % | Critical | Invariante de D1 y D16 | R1, R3 |
| DQ-P06 | `fact_track_artist` | Validez | `popularity` entre 0 y 100; `energy` y `acousticness` no nulos y en [0, 1]; `danceability` y `valence` nulos o en [0, 1]; `tempo` nulo o > 0 | 100 % | Critical | Contrato de Spotify e invariantes de D7 y D9 | R1, R4 |
| DQ-P07 | `fact_track_artist` | Consistencia | `tempo`, `danceability` y `valence` son nulas a la vez o no nulas a la vez | 100 % | Critical | Invariante de D9 | R1 |
| DQ-P08 | `fact_track_artist` | Consistencia | `n_artists` ≥ 1 e `is_collaboration` = (`n_artists` > 1) | 100 % | Critical | Invariante de S5 | R3 |
| DQ-P09 | `dim_track` | Consistencia | Cada `song_bk` tiene exactamente una versión representativa | 100 % | Critical | Invariante de D8 | R1, R3, R4 |
| DQ-P10 | `dim_artist`, `fact_award` | Consistencia | Los artistas con `is_awarded` son exactamente los presentes en `fact_award` | 100 % | Critical | Invariante de D15 | R1–R4 |
| DQ-P11 | `transform_report.json` | Integración | Tasa de emparejamiento de filas Grammy atribuibles | ≥ 40 % | Warning | El profiling midió entre 44 % y 49 %; una caída indica una regresión en la normalización o en la separación de nombres. Se confirma con la primera corrida | R1–R4 |
