# Dashboard analítico (E8)

El dashboard responde los cuatro requisitos analíticos (R1 a R4) con 4 KPIs y 6 visualizaciones. Todas consultan el Data Warehouse `music_dw`; ninguna lee archivos CSV.

- Libro de Tableau: `docs/dashboard/music_dw_dashboard.twb`
- Imagen exportada: `docs/dashboard/dashboard.png`
- Vistas que consume: `sql/kpi_views.sql`
- Rol de solo lectura: `sql/dw_roles.sql`

## 1. Conexión al Data Warehouse

| Parámetro | Valor |
| --- | --- |
| Herramienta | Tableau Desktop, conector PostgreSQL |
| Tipo de conexión | En vivo (sin extracto) |
| Servidor y puerto | `localhost:5432` (contenedor `postgres-data`) |
| Base de datos | `music_dw` |
| Usuario | `dashboard_user`, solo lectura |
| Contraseña | No se versiona. Está en `.env` como `DASHBOARD_PASSWORD` y Tableau la pide al abrir el libro |

`dashboard_user` solo tiene `SELECT` sobre las seis vistas `v_kpi_*`. Si consulta una tabla del modelo, por ejemplo `fact_award`, recibe `permission denied` (EV-34). El libro declara una sola conexión a `music_dw` con ese usuario y solo referencia las seis vistas (EV-36).

**Por qué vistas y no las tablas del modelo.** Varias métricas dependen de reglas que en SQL quedan explícitas y verificables, y en Tableau quedarían repartidas en cálculos de la herramienta:

- La unidad es la canción única: una canción con varias versiones en `dim_track` cuenta una vez, con la popularidad máxima entre versiones (D8) y el audio de su versión representativa.
- R3 solo considera artistas con al menos 5 canciones (D11).
- Las medianas, los porcentajes y la correlación se calculan en la base de datos.

Tableau solo presenta resultados, y cada valor del dashboard se puede comprobar con una consulta a la vista. Las vistas no se ven afectadas por la recarga del DAG (TRUNCATE no las elimina), así que el dashboard refleja cada carga nueva sin cambios.

## 2. Trazabilidad requisito, DW y visualización (§8.1)

| Requisito analítico | Elemento del DW / consulta | KPI / visualización |
| --- | --- | --- |
| R1. Vigencia y sonido por época | `fact_award` + `dim_year` (década del premio) + `fact_track_artist` + `dim_track`. Vistas `v_song_artist`, `v_kpi_r1_decada` y `v_kpi_resumen` | KPI R1: popularidad mediana de los premiados y % de sus canciones con popularidad 0. R1a: popularidad mediana (barras) y % de canciones con popularidad 0 (línea) por década. R1b: perfil sonoro (danceability, energy, valence, acousticness) por década |
| R2. Géneros de los premiados | `fact_award` + `dim_artist` + `fact_track_artist` + `bridge_track_genre` + `dim_genre`. Vistas `v_kpi_r2_genero` y `v_kpi_resumen` | KPI R2: género con más artistas premiados y su porcentaje. R2: top 15 géneros por artistas premiados |
| R3. Colaboración por década | `fact_track_artist` (`is_collaboration`) + `dim_artist` + `fact_award`. Vistas `v_artista_colaboracion`, `v_kpi_r3_colaboracion` y `v_kpi_resumen` | KPI R3: mediana del % de colaboración por artista, premiados frente a no premiados. R3: barras por década con el grupo de no premiados como referencia |
| R4. Intensidad del reconocimiento | `fact_award` + `v_song_artist`. Vistas `v_kpi_r4_artista`, `v_kpi_r4_tramos` y `v_kpi_resumen` | KPI R4: correlación entre premios y popularidad. R4a: popularidad mediana por tramo de premios (1, 2 a 4, 5 o más). R4b: dispersión de premios y popularidad por artista |

## 3. Comprobación de valores

Cada valor del dashboard coincide con la salida de las vistas guardada en `docs/evidence/E8_kpi/kpi_views_verificacion.txt`. Tableau muestra la coma como separador decimal por la configuración regional del equipo.

| Indicador | Dashboard | Vista |
| --- | --- | --- |
| Popularidad mediana de premiados | 47,00 | 47.0 |
| % de canciones con popularidad 0 | 10,78 % | 10.78 |
| Género con más premiados | rock, 12,14 % | rock, 12.14 |
| Colaboración mediana, premiados / no premiados | 23,53 % / 33,33 % | 23.53 / 33.33 |
| Correlación premios y popularidad | -0,006 | -0.006 |
| Puntos en R4b | 560 marcas | 560 artistas premiados |
| Suma de premios en R4b | 1.478 | 1,478 premios atribuidos |

## 4. Lectura de resultados

- **R1.** La popularidad mediana no crece de forma continua con la cercanía de la década: es alta en los premiados de 1960 y 2010 (54), cae en 1980 (24) y es mínima en 1950 (2). El % de canciones con popularidad 0 baja de 42.11 % (1950) a 7.36 % (1990). El sonido cambia de forma clara: acousticness baja de 0.79 a 0.32, energy sube de 0.32 a 0.61 y danceability de 0.50 a 0.57.
- **R2.** Rock es el género con más artistas premiados (68, el 12.14 % de 560), seguido de soul y country. El corte del top 15 no tiene empates: los puestos 13 a 15 tienen 31 artistas y el puesto 16 tiene 30.
- **R3.** Los premiados colaboran menos que los no premiados (mediana de 23.53 % frente a 33.33 %), salvo los premiados de la década de 2010 (42.62 %).
- **R4.** No hay relación entre la cantidad de premios y la popularidad actual: la correlación es -0.006 y las medianas por tramo son parecidas (44.5, 49.0 y 41.0).

## 5. Limitaciones

- La década de 1950 tiene pocos artistas (11 en R1 y 3 en R3). Sus valores no deben leerse como tendencia.
- La popularidad es la que reporta Spotify en el dataset, no la del momento del premio.
- Solo entran los artistas premiados que se cruzaron con Spotify. La cobertura del cruce está documentada en la integración.
- Los porcentajes de R2 no suman 100 %: un artista puede tener varios géneros.
- La correlación de Pearson mide relación lineal. La dispersión de R4b tampoco muestra un patrón no lineal visible.
- La conexión es en vivo: para abrir el libro, el contenedor `postgres-data` debe estar levantado y el DW cargado.

## 6. Cómo abrir el dashboard

1. Levantar los servicios con `docker compose up -d` y confirmar que el DW tiene datos (una ejecución exitosa del DAG).
2. Si el rol o las vistas no existen, ejecutar `sql/dw_roles.sql` y después `sql/kpi_views.sql` contra `music_dw` como administrador. Los comandos están en el README principal.
3. Abrir `docs/dashboard/music_dw_dashboard.twb` en Tableau Desktop e ingresar `dashboard_user` con el valor de `DASHBOARD_PASSWORD`.

## 7. Evidencias

EV-33 a EV-37 en `docs/evidence/README.md`.
