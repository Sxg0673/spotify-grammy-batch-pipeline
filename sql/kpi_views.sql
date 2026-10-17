-- Vistas de KPI del Data Warehouse (music_dw), una por requisito analítico (R1 a R4).
-- Se ejecuta como admin después de sql/dw_roles.sql. Repetible: elimina y recrea las vistas.
-- El dashboard (rol dashboard_user) solo tiene SELECT sobre las vistas v_kpi_*, no sobre las tablas.
\set ON_ERROR_STOP on

BEGIN;

DROP VIEW IF EXISTS v_kpi_resumen;
DROP VIEW IF EXISTS v_kpi_r4_tramos;
DROP VIEW IF EXISTS v_kpi_r4_artista;
DROP VIEW IF EXISTS v_kpi_r3_colaboracion;
DROP VIEW IF EXISTS v_artista_colaboracion;
DROP VIEW IF EXISTS v_kpi_r2_genero;
DROP VIEW IF EXISTS v_kpi_r1_decada;
DROP VIEW IF EXISTS v_song_artist;

-- Base: una fila por canción única y artista. Popularidad = máximo entre versiones (D8);
-- medidas de audio y colaboración tomadas de la versión representativa.
CREATE VIEW v_song_artist AS
WITH pop AS (
    SELECT t.song_bk, f.artist_key, MAX(f.popularity) AS popularity
    FROM fact_track_artist f
    JOIN dim_track t ON t.track_key = f.track_key
    GROUP BY t.song_bk, f.artist_key
)
SELECT t.song_bk,
       f.artist_key,
       t.track_key AS rep_track_key,
       p.popularity,
       f.danceability,
       f.energy,
       f.valence,
       f.acousticness,
       f.tempo::double precision AS tempo,
       f.n_artists,
       f.is_collaboration
FROM fact_track_artist f
JOIN dim_track t ON t.track_key = f.track_key AND t.is_song_representative
JOIN pop p ON p.song_bk = t.song_bk AND p.artist_key = f.artist_key;

-- Base: % de colaboración por artista, solo con al menos 5 canciones (D11).
CREATE VIEW v_artista_colaboracion AS
SELECT sa.artist_key,
       COUNT(*) AS canciones,
       100.0 * COUNT(*) FILTER (WHERE sa.is_collaboration) / COUNT(*) AS pct_colaboracion,
       EXISTS (SELECT 1 FROM fact_award fa WHERE fa.artist_key = sa.artist_key) AS premiado
FROM v_song_artist sa
GROUP BY sa.artist_key
HAVING COUNT(*) >= 5;

-- R1: vigencia y sonido de los artistas premiados por década del premio. Unidad de la mediana: canción única.
CREATE VIEW v_kpi_r1_decada AS
WITH artista_decada AS (
    SELECT DISTINCT fa.artist_key, y.decade
    FROM fact_award fa
    JOIN dim_year y ON y.year_key = fa.year_key
),
cancion_decada AS (
    SELECT DISTINCT ON (ad.decade, sa.song_bk)
           ad.decade, sa.song_bk, sa.popularity, sa.danceability, sa.energy,
           sa.valence, sa.acousticness, sa.tempo
    FROM artista_decada ad
    JOIN v_song_artist sa ON sa.artist_key = ad.artist_key
    ORDER BY ad.decade, sa.song_bk
),
artistas AS (
    SELECT decade, COUNT(*) AS artistas_premiados FROM artista_decada GROUP BY decade
)
SELECT c.decade,
       a.artistas_premiados,
       COUNT(*) AS canciones,
       ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY c.popularity))::numeric, 1) AS popularidad_mediana,
       ROUND(100.0 * COUNT(*) FILTER (WHERE c.popularity = 0) / COUNT(*), 2) AS pct_popularidad_cero,
       ROUND(AVG(c.danceability)::numeric, 3) AS danceability_media,
       ROUND(AVG(c.energy)::numeric, 3) AS energy_media,
       ROUND(AVG(c.valence)::numeric, 3) AS valence_media,
       ROUND(AVG(c.acousticness)::numeric, 3) AS acousticness_media,
       ROUND(AVG(c.tempo)::numeric, 1) AS tempo_medio
FROM cancion_decada c
JOIN artistas a ON a.decade = c.decade
GROUP BY c.decade, a.artistas_premiados;

-- R2: géneros de Spotify en los que aparecen los artistas premiados.
CREATE VIEW v_kpi_r2_genero AS
WITH premiados AS (
    SELECT DISTINCT artist_key FROM fact_award
),
membresia AS (
    SELECT g.genre_name AS genero, f.artist_key
    FROM premiados p
    JOIN fact_track_artist f ON f.artist_key = p.artist_key
    JOIN bridge_track_genre b ON b.track_key = f.track_key
    JOIN dim_genre g ON g.genre_key = b.genre_key
    GROUP BY g.genre_name, f.artist_key
),
conteo AS (
    SELECT genero, COUNT(*) AS artistas_premiados FROM membresia GROUP BY genero
),
cancion_genero AS (
    SELECT DISTINCT ON (g.genre_name, sa.song_bk)
           g.genre_name AS genero, sa.song_bk, sa.popularity
    FROM premiados p
    JOIN v_song_artist sa ON sa.artist_key = p.artist_key
    JOIN bridge_track_genre b ON b.track_key = sa.rep_track_key
    JOIN dim_genre g ON g.genre_key = b.genre_key
    ORDER BY g.genre_name, sa.song_bk
),
pop AS (
    SELECT genero,
           COUNT(*) AS canciones,
           ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY popularity))::numeric, 1) AS popularidad_mediana
    FROM cancion_genero
    GROUP BY genero
)
SELECT c.genero,
       c.artistas_premiados,
       ROUND(100.0 * c.artistas_premiados / (SELECT COUNT(*) FROM premiados), 2) AS pct_de_premiados,
       p.canciones,
       p.popularidad_mediana
FROM conteo c
LEFT JOIN pop p ON p.genero = c.genero;

-- R3: colaboración de los artistas premiados por década, con referencia de no premiados (mismo mínimo de 5 canciones).
CREATE VIEW v_kpi_r3_colaboracion AS
WITH artista_decada AS (
    SELECT DISTINCT fa.artist_key, y.decade
    FROM fact_award fa
    JOIN dim_year y ON y.year_key = fa.year_key
)
SELECT 'Premiados'::text AS grupo,
       ad.decade,
       COUNT(*) AS artistas,
       ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY ac.pct_colaboracion))::numeric, 2) AS mediana_pct_colaboracion
FROM artista_decada ad
JOIN v_artista_colaboracion ac ON ac.artist_key = ad.artist_key
GROUP BY ad.decade
UNION ALL
SELECT 'No premiados',
       NULL::smallint,
       COUNT(*),
       ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_colaboracion))::numeric, 2)
FROM v_artista_colaboracion
WHERE NOT premiado;

-- R4 (artista): premios atribuidos y popularidad mediana de sus canciones.
CREATE VIEW v_kpi_r4_artista AS
WITH premios AS (
    SELECT artist_key, SUM(award_count)::integer AS premios
    FROM fact_award
    GROUP BY artist_key
),
pop AS (
    SELECT artist_key,
           COUNT(*) AS canciones,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY popularity))::numeric AS pop_mediana
    FROM v_song_artist
    GROUP BY artist_key
)
SELECT a.artist_bk,
       a.artist_name AS artista,
       p.premios,
       CASE WHEN p.premios = 1 THEN '1'
            WHEN p.premios BETWEEN 2 AND 4 THEN '2-4'
            ELSE '5+' END AS tramo_premios,
       q.canciones,
       ROUND(q.pop_mediana, 2) AS popularidad_mediana
FROM premios p
JOIN dim_artist a ON a.artist_key = p.artist_key
JOIN pop q ON q.artist_key = p.artist_key;

-- R4 (tramos): popularidad mediana por tramo de premios y correlación premios-popularidad.
CREATE VIEW v_kpi_r4_tramos AS
SELECT tramo_premios,
       CASE tramo_premios WHEN '1' THEN 1 WHEN '2-4' THEN 2 ELSE 3 END AS orden,
       COUNT(*) AS artistas,
       ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY popularidad_mediana))::numeric, 1) AS popularidad_mediana,
       (SELECT ROUND(corr(premios, popularidad_mediana)::numeric, 3) FROM v_kpi_r4_artista) AS correlacion_premios_popularidad
FROM v_kpi_r4_artista
GROUP BY tramo_premios;

-- KPIs de una sola fila para las tarjetas del dashboard.
CREATE VIEW v_kpi_resumen AS
WITH top_genero AS (
    SELECT genero, pct_de_premiados
    FROM v_kpi_r2_genero
    ORDER BY artistas_premiados DESC, genero
    LIMIT 1
),
canciones_premiados AS (
    SELECT DISTINCT ON (sa.song_bk) sa.song_bk, sa.popularity
    FROM v_song_artist sa
    WHERE sa.artist_key IN (SELECT artist_key FROM fact_award)
    ORDER BY sa.song_bk
)
SELECT (SELECT COUNT(DISTINCT artist_key) FROM fact_award) AS artistas_premiados,
       (SELECT SUM(award_count) FROM fact_award) AS premios_atribuidos,
       (SELECT ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY popularity))::numeric, 1)
          FROM canciones_premiados) AS popularidad_mediana_premiados,
       (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE popularity = 0) / COUNT(*), 2)
          FROM canciones_premiados) AS pct_popularidad_cero_premiados,
       (SELECT genero FROM top_genero) AS genero_con_mas_premiados,
       (SELECT pct_de_premiados FROM top_genero) AS pct_genero_top,
       (SELECT ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_colaboracion))::numeric, 2)
          FROM v_artista_colaboracion WHERE premiado) AS mediana_pct_colaboracion_premiados,
       (SELECT ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_colaboracion))::numeric, 2)
          FROM v_artista_colaboracion WHERE NOT premiado) AS mediana_pct_colaboracion_no_premiados,
       (SELECT ROUND(corr(premios, popularidad_mediana)::numeric, 3) FROM v_kpi_r4_artista) AS correlacion_premios_popularidad;

GRANT SELECT ON v_kpi_resumen, v_kpi_r1_decada, v_kpi_r2_genero, v_kpi_r3_colaboracion,
                v_kpi_r4_artista, v_kpi_r4_tramos TO dashboard_user;

COMMIT;
