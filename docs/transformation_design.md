# Diseño de transformación e integración

Implementa: `src/transform.py`. Decisiones (Dn): `notebooks/data_profiling.ipynb`. Reglas de calidad: `docs/quality_rules.md`. Modelo destino: `docs/dimensional_model.md`.

Principio: la transformación aplica reglas de ingeniería conocidas y justificadas por evidencia o contrato. Ninguna regla existe para que una validación pase.

## 1. Entradas y salidas

| | Ubicación | Contenido |
|---|---|---|
| Entrada | `data/work/<run_id>/raw/` | Raw de Spotify y Grammy ya validados (solo columnas requeridas, D12) |
| Salida | `data/work/<run_id>/prepared/` | Un CSV por tabla del modelo, con llaves de negocio (la carga asigna las llaves sustitutas) |
| Reporte | `data/work/<run_id>/prepared/transform_report.json` | Filas de entrada y salida, exclusiones por motivo y estadísticas de emparejamiento |

| Archivo | Columnas |
|---|---|
| `dim_artist.csv` | `artist_bk`, `artist_name`, `is_awarded` |
| `dim_year.csv` | `year`, `decade` |
| `dim_category.csv` | `category_bk`, `category_name`, `is_new_artist` |
| `dim_genre.csv` | `genre_name` |
| `dim_track.csv` | `track_id`, `track_name`, `song_bk`, `is_song_representative`, `audio_analyzed` |
| `bridge_track_genre.csv` | `track_id`, `genre_name` |
| `fact_award.csv` | `year`, `category_bk`, `nominee`, `artist_bk`, `award_count` |
| `fact_track_artist.csv` | `track_id`, `artist_bk`, `popularity`, `danceability`, `energy`, `valence`, `acousticness`, `tempo`, `n_artists`, `is_collaboration` |

## 2. Normalización común (D4)

`normalizar(texto)`: recortar bordes, minúsculas, quitar tildes (Unicode NFKD sin marcas combinantes) y colapsar espacios internos. Se usa en las llaves de artista, canción y categoría. Nunca se aplica a los nombres para mostrar.

## 3. Rama Spotify

| Paso | Regla y justificación | Campos afectados | Antes → después | Manejo de excepciones | Impacto analítico |
|---|---|---|---|---|---|
| S1 | Descartar filas sin `artists` (D14): no son identificables ni integrables | Fila completa | 114,000 → 113,999 | Se cuentan como `excl_sin_artists` | Todos los requerimientos |
| S2 | Eliminar duplicados exactos (D6): copias idénticas | Fila completa | −450 filas | Se cuentan como `excl_duplicados` | Evita doble conteo |
| S3 | Consolidar a una fila por `track_id` (D7): `popularity` = máximo; los géneros pasan al puente | `popularity`, `track_genre` | Grano pista × género → grano pista (89,740) más `bridge_track_genre` | Si cualquier otro atributo varía dentro de un `track_id`, la transformación falla con un error explícito: el supuesto de la fuente dejó de cumplirse | Medida única por pista (R1, R4); R2 vía el puente |
| S4 | `audio_analyzed = false` cuando `tempo`, `danceability` y `valence` son 0 a la vez; esas tres pasan a nulo (D9) | `tempo`, `danceability`, `valence` | 157 pistas marcadas | Filas con solo algunas de las tres en 0 conservan sus valores | El perfil sonoro de R1 excluye medidas no definidas |
| S5 | Separar `artists` por `;`, recortar (D10) y normalizar (D4); `n_artists` = artistas distintos; `is_collaboration` = `n_artists > 1` | `artists` → `artist_bk` | Grano pista → pista × artista | Las partes vacías se descartan; un artista repetido en la misma pista se cuenta una vez | Integración (todos); colaboración (R3) |
| S6 | `song_bk` = artistas normalizados ordenados alfabéticamente y unidos por `;`, más `|`, más `track_name` normalizado. Versión representativa = mayor `popularity`; empate → menor `track_id` (D8) | `song_bk`, `is_song_representative` | Una pista representativa por canción | Determinista: el mismo dato siempre elige la misma versión | Popularidad por canción (R1, R4); R3 sin reediciones |
| S7 | Nombre para mostrar = escritura más frecuente del artista en las pistas; empate → orden alfabético (D17) | `artist_name` | Una fila por `artist_bk` | Determinista | Etiquetas del dashboard |

## 4. Rama Grammy

| Paso | Regla y justificación | Campos afectados | Antes → después | Manejo de excepciones | Impacto analítico |
|---|---|---|---|---|---|
| G1 | Excluir el año 2019 (D1): `winner` contaminado con nominados | Fila completa | −433 filas | Se cuentan como `excl_2019` | R1, R3, R4 |
| G2 | En categorías cuyo nombre normalizado contiene "new artist", si `artist` es nulo se toma `nominee` (D2) | `artist` | Se recupera el artista de Best New Artist | Si también `nominee` es nulo, la fila sigue sin artista | R1, R3, R4 |
| G3 | Excluir filas no atribuibles (D3): totalmente vacías, `(Various Artists)` y sin artista después de G2 | Fila completa | Se excluyen | Se cuentan por motivo: `excl_fila_vacia`, `excl_various_artists`, `excl_sin_artista` | Solo entran premios con intérprete |
| G4 | `category_bk` = categoría normalizada; nombre para mostrar = escritura más frecuente, empate → alfabético (D18); `is_new_artist` (D2) | `category` | 638 escrituras → 629 categorías | Determinista | Contexto del premio |
| G5 | `decade` = `(year // 10) * 10` (D16) | `year` → `decade` | Década derivada | `year` ya está validado como entero en rango (DQ-G02) | R1, R3 |

## 5. Integración (contrato)

### Algoritmo de emparejamiento (D4, D13)

1. Si la clave normalizada completa del artista Grammy existe entre los artistas de Spotify, se acredita a ese artista.
2. Si no, se separa por `,` `&` `and` `with` `feat.` `featuring`.
3. Se quitan las partes de la lista de exclusión (`various artists`, `original cast`), ignorando paréntesis.
4. Se acepta solo si queda al menos una parte y todas coinciden; el premio se acredita a cada participante.
5. En otro caso, la fila se cuenta como `sin_coincidencia`.

### Contrato

| Elemento | Definición |
|---|---|
| Llave de integración | `artist` de Grammy (después de G2) normalizado ↔ cada artista de Spotify (después de S5) normalizado (`artist_bk`) |
| Cardinalidad | Premio → 0..N artistas; artista → 0..N premios y 1..N pistas. La relación N:N premio–artista se resuelve en el grano de `fact_award` |
| Preprocesamiento | Normalización común (sección 2), separadores de Grammy y lista de exclusión |
| Registros sin coincidencia | No entran al DW; se cuentan en `transform_report.json` y en el log (`sin_coincidencia`) |
| Coincidencias duplicadas | Cada `artist_bk` es una sola fila de `dim_artist` por construcción. Un mismo par (premio, artista) repetido se deduplica y se cuenta (`pares_duplicados`) |
| Salidas | `fact_award` (grano: premio × artista); `is_awarded = true` para los artistas presentes en `fact_award` (D15) |
| Supuestos | El nombre normalizado identifica a un artista; Spotify es una muestra (1,000 pistas por género) |
| Limitaciones | Homónimos con distinta capitalización se fusionan (RK08); b2 descarta colaboraciones con participantes ausentes de Spotify; la cobertura varía por década (22 %–40 %) |
| Evidencia esperada | Profiling: E2 = 1,310 filas, b2 agrega 138 (celdas 37 y 52). Cada corrida reporta su tasa real (DQ-P11) |

## 6. Construcción de las tablas

| Tabla | Origen |
|---|---|
| `dim_artist` | Todos los `artist_bk` de S5, con S7 y `is_awarded` |
| `dim_track` | Pistas de S3, con S4 y S6 |
| `dim_genre` | Géneros distintos de S3 |
| `bridge_track_genre` | Pares (pista, género) de S3 |
| `dim_year` | Años de Grammy después de G1 |
| `dim_category` | Categorías de Grammy después de G1, con G4 |
| `fact_track_artist` | Pares (pista, artista) de S5, con las medidas de S3 y S4 |
| `fact_award` | Resultado de la integración |

El mínimo de 5 canciones de R3 (D11) no se aplica aquí: es un filtro del KPI y se aplica en la consulta analítica. El DW conserva el dato atómico.

## 7. Reporte de transformación (`transform_report.json`)

- `spotify`: `filas_entrada`, `excl_sin_artists`, `excl_duplicados`, `pistas`, `pistas_inconsistentes`, `audio_no_analizado`, `filas_pista_artista`, `canciones`, `artistas`.
- `grammy`: `filas_entrada`, `excl_2019`, `recuperadas_new_artist`, `excl_fila_vacia`, `excl_various_artists`, `excl_sin_artista`, `filas_atribuibles`.
- `integracion`: `filas_emparejadas`, `filas_sin_coincidencia`, `tasa_emparejamiento`, `filas_premio_artista`, `pares_duplicados`, `artistas_premiados`.
- `salidas`: filas por archivo.
