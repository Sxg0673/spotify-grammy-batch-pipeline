-- Preparación de la fuente operacional de Grammy (taller §6.2).
-- Se ejecuta como admin sobre grammy_source. Es repetible: recrea la tabla y recarga el CSV.
-- La tabla copia las 10 columnas del CSV; el pipeline selecciona las que necesita (D12).
-- Sin NOT NULL ni UNIQUE en columnas de negocio: la calidad la evalúan las compuertas de GX.
\set ON_ERROR_STOP on

BEGIN;

DROP TABLE IF EXISTS grammy_awards;

CREATE TABLE grammy_awards (
    id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    year         smallint,
    title        text,
    published_at timestamptz,
    updated_at   timestamptz,
    category     text,
    nominee      text,
    artist       text,
    workers      text,
    img          text,
    winner       boolean
);

\copy grammy_awards (year, title, published_at, updated_at, category, nominee, artist, workers, img, winner) FROM '/data/raw/the_grammy_awards.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

COMMIT;
