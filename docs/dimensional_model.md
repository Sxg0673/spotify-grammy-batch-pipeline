# Modelo dimensional

Fuente del modelo: `docs/dimensional_model.dbml` (código DBML, renderizable en dbdiagram.io).
Decisiones referenciadas (Dn): registro de decisiones en `notebooks/data_profiling.ipynb`.

![Modelo dimensional](dimensional_model.png)

## 1. Procesos de negocio

El modelo representa dos procesos de negocio distintos, conectados únicamente por el artista:

| Proceso | Fuente | Tabla de hechos |
|---|---|---|
| Reconocimiento Grammy de artistas (1958–2018) | Grammy (PostgreSQL fuente) | `fact_award` |
| Catálogo actual de los artistas en Spotify | Spotify (CSV) | `fact_track_artist` |

### Por qué dos tablas de hechos (constelación)

- Cada proceso tiene un grano distinto: un premio es un evento con año y categoría; una pista es un elemento de catálogo con medidas de popularidad y sonido.
- Forzar un único hecho obligaría a guardar medidas dentro de una dimensión (métricas de Spotify como atributos del artista) o a tratar los premios como atributos, sin poder contarlos como hechos.
- Los requerimientos cruzan ambos procesos a través de la dimensión conformada `dim_artist` (drill-across).
- Estructura resultante: dos estrellas que comparten `dim_artist`, con un brazo copo de nieve `dim_track → bridge_track_genre → dim_genre`, consecuencia del grano pista × género de la fuente.

## 2. Grano de las tablas de hechos

| Hecho | Una fila representa | Consecuencia |
|---|---|---|
| `fact_award` | Un premio Grammy (año, categoría, nominado) acreditado a un artista emparejado con Spotify, entre 1958 y 2018 | Un premio compartido por N artistas genera N filas (D4) |
| `fact_track_artist` | La participación de un artista en una pista única de Spotify (`track_id`), después de eliminar duplicados (D6), consolidar la popularidad (D7) y descartar pistas sin artista (D14) | Las medidas de una pista se repiten por cada artista participante; los análisis a nivel de pista deben contar `track_key` distintos |

## 3. Dimensiones

| Dimensión | Llave de negocio | Atributos | Uso |
|---|---|---|---|
| `dim_artist` (conformada) | `artist_bk`: nombre normalizado (D4, D10) | `artist_name` (D17), `is_awarded` (D15) | R1–R4. Incluye todos los artistas de Spotify; los premiados se marcan con `is_awarded` |
| `dim_year` | `year` | `decade` (D16) | R1, R3 |
| `dim_category` | `category_bk`: nombre normalizado (D18) | `category_name` (D18), `is_new_artist` (D2) | Contexto del premio; R4 |
| `dim_track` | `track_id` | `track_name`, `song_bk`, `is_song_representative` (D8), `audio_analyzed` (D9) | R1, R3, R4 |
| `dim_genre` | `genre_name` | — | R2 |
| `bridge_track_genre` | (`track_key`, `genre_key`) | — | R2: relación muchos a muchos pista–género |

## 4. Medidas

| Hecho | Medida | Tipo | Regla |
|---|---|---|---|
| `fact_award` | `award_count` | Aditiva | Siempre 1; se suma para contar premios por artista, década o categoría |
| `fact_track_artist` | `popularity` | No aditiva | Máximo por `track_id` (D7); los KPI usan la mediana sobre versiones representativas (D8) |
| `fact_track_artist` | `danceability`, `energy`, `valence`, `acousticness`, `tempo` | No aditivas | Se promedian; `danceability`, `valence` y `tempo` son nulas si `audio_analyzed = false` (D9) |
| `fact_track_artist` | `n_artists` | No aditiva | Número de artistas de la pista |
| `fact_track_artist` | `is_collaboration` | Indicador | `n_artists > 1`; su promedio por artista es el % de colaboración (R3) |

## 5. Llaves y relaciones

- Llaves sustitutas enteras (`*_key`) en todas las dimensiones; las llaves de negocio (`*_bk`, `track_id`, `year`, `genre_name`) tienen restricción `UNIQUE`.
- Los hechos referencian dimensiones solo por llaves sustitutas (llaves foráneas).
- Unicidad del grano en los hechos:
  - `fact_award`: (`year_key`, `category_key`, `nominee`, `artist_key`).
  - `fact_track_artist`: (`track_key`, `artist_key`).
- Estas restricciones impiden duplicar filas en una recarga y son la base de la estrategia de rerun seguro (§7.3, por definir).

| Relación | Cardinalidad |
|---|---|
| `dim_year` → `fact_award` | 1 a N |
| `dim_category` → `fact_award` | 1 a N |
| `dim_artist` → `fact_award` | 1 a N |
| `dim_artist` → `fact_track_artist` | 1 a N |
| `dim_track` → `fact_track_artist` | 1 a N |
| `dim_track` ↔ `dim_genre` (vía `bridge_track_genre`) | N a N |

## 6. Cómo responde el modelo a cada requerimiento

| Req. | Pregunta | Recorrido en el modelo |
|---|---|---|
| R1 | ¿Qué tan vigentes y cómo suenan hoy los artistas premiados de cada década? | `fact_award` + `dim_year` dan los pares artista–década; se cruzan por `dim_artist` con `fact_track_artist` filtrado a `is_song_representative`: mediana de popularidad, % de ceros y promedios de sonido por década |
| R2 | ¿En qué géneros se ubican los artistas premiados? | `dim_artist` (`is_awarded`) → `fact_track_artist` → `dim_track` → `bridge_track_genre` → `dim_genre`: artistas distintos por género y mediana de popularidad |
| R3 | ¿Qué tan colaborativos son los artistas premiados según la época? | `fact_track_artist` sobre versiones representativas: % de `is_collaboration` por artista con mínimo 5 canciones (D11); se cruza con las décadas de `fact_award` |
| R4 | ¿Más premios implican más popularidad hoy? | Suma de `award_count` por artista en `fact_award` (tramos 1, 2–4, 5+) cruzada con la mediana de popularidad de `fact_track_artist` |

## 7. Alcance y exclusiones

- Los artistas de Grammy que no se emparejan con Spotify no entran al DW; su conteo por motivo se registra en las métricas de cada corrida (D3).
- El año 2019 no entra al DW (D1).
- Las categorías cuyo premio no es del intérprete solo aparecen si su fila tiene un artista atribuible (D2–D4).

## 8. Capa de consumo: vistas de KPI

El modelo no cambia para el dashboard. Encima de él, `sql/kpi_views.sql` define vistas que fijan las reglas de cálculo en SQL versionado, de modo que la herramienta de BI solo lee resultados.

| Vista | Una fila por | Regla que aplica |
| --- | --- | --- |
| `v_song_artist` | canción × artista | Popularidad = máximo entre versiones (D8); audio de la versión representativa |
| `v_artista_colaboracion` | artista con al menos 5 canciones | % de canciones en colaboración (D11) y marca de premiado |
| `v_kpi_r1_decada` | década del premio | Popularidad mediana, % con popularidad 0 y perfil sonoro de los premiados, contando cada canción una vez |
| `v_kpi_r2_genero` | género | Artistas premiados, su % sobre el total de premiados, canciones y popularidad mediana |
| `v_kpi_r3_colaboracion` | grupo y década | Mediana del % de colaboración: premiados por década y no premiados como referencia |
| `v_kpi_r4_artista` | artista premiado | Premios, tramo de premios y popularidad mediana |
| `v_kpi_r4_tramos` | tramo de premios | Artistas, popularidad mediana y correlación entre premios y popularidad |
| `v_kpi_resumen` | fila única | Los valores de las cuatro tarjetas de KPI |

`dashboard_user` solo tiene `SELECT` sobre las seis vistas `v_kpi_*`. Las vistas intermedias y las tablas del modelo no son accesibles para ese rol. Uso y evidencias en `docs/dashboard/README.md`.
