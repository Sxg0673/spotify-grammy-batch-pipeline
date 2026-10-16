-- Esquema del Data Warehouse (music_dw). Modelo: docs/dimensional_model.md y docs/dimensional_model.dbml
-- Se ejecuta como admin. Repetible: IF NOT EXISTS no modifica tablas ya creadas.
-- Las llaves sustitutas las asigna la base durante la carga; el pipeline entrega llaves de negocio.
-- Las restricciones son la última defensa. La calidad de los datos la validan las compuertas de GX antes de cargar.
\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS dim_artist (
    artist_key  integer GENERATED ALWAYS AS IDENTITY,
    artist_bk   varchar(255) NOT NULL,
    artist_name varchar(255) NOT NULL,
    is_awarded  boolean NOT NULL DEFAULT false,
    CONSTRAINT pk_dim_artist PRIMARY KEY (artist_key),
    CONSTRAINT uq_dim_artist_bk UNIQUE (artist_bk)
);

CREATE TABLE IF NOT EXISTS dim_year (
    year_key integer GENERATED ALWAYS AS IDENTITY,
    year     smallint NOT NULL,
    decade   smallint NOT NULL,
    CONSTRAINT pk_dim_year PRIMARY KEY (year_key),
    CONSTRAINT uq_dim_year_year UNIQUE (year)
);

CREATE TABLE IF NOT EXISTS dim_category (
    category_key  integer GENERATED ALWAYS AS IDENTITY,
    category_bk   varchar(255) NOT NULL,
    category_name varchar(255) NOT NULL,
    is_new_artist boolean NOT NULL DEFAULT false,
    CONSTRAINT pk_dim_category PRIMARY KEY (category_key),
    CONSTRAINT uq_dim_category_bk UNIQUE (category_bk)
);

CREATE TABLE IF NOT EXISTS dim_track (
    track_key              integer GENERATED ALWAYS AS IDENTITY,
    track_id               varchar(22) NOT NULL,
    track_name             text NOT NULL,
    song_bk                text NOT NULL,
    is_song_representative boolean NOT NULL,
    audio_analyzed         boolean NOT NULL,
    CONSTRAINT pk_dim_track PRIMARY KEY (track_key),
    CONSTRAINT uq_dim_track_id UNIQUE (track_id)
);

CREATE TABLE IF NOT EXISTS dim_genre (
    genre_key  integer GENERATED ALWAYS AS IDENTITY,
    genre_name varchar(100) NOT NULL,
    CONSTRAINT pk_dim_genre PRIMARY KEY (genre_key),
    CONSTRAINT uq_dim_genre_name UNIQUE (genre_name)
);

CREATE TABLE IF NOT EXISTS bridge_track_genre (
    track_key integer NOT NULL,
    genre_key integer NOT NULL,
    CONSTRAINT pk_bridge_track_genre PRIMARY KEY (track_key, genre_key),
    CONSTRAINT fk_bridge_track FOREIGN KEY (track_key) REFERENCES dim_track (track_key),
    CONSTRAINT fk_bridge_genre FOREIGN KEY (genre_key) REFERENCES dim_genre (genre_key)
);

CREATE TABLE IF NOT EXISTS fact_award (
    award_artist_key bigint GENERATED ALWAYS AS IDENTITY,
    year_key         integer NOT NULL,
    category_key     integer NOT NULL,
    artist_key       integer NOT NULL,
    nominee          varchar(500) NOT NULL,
    award_count      smallint NOT NULL DEFAULT 1,
    CONSTRAINT pk_fact_award PRIMARY KEY (award_artist_key),
    CONSTRAINT uq_fact_award_grain UNIQUE (year_key, category_key, nominee, artist_key),
    CONSTRAINT fk_fact_award_year FOREIGN KEY (year_key) REFERENCES dim_year (year_key),
    CONSTRAINT fk_fact_award_category FOREIGN KEY (category_key) REFERENCES dim_category (category_key),
    CONSTRAINT fk_fact_award_artist FOREIGN KEY (artist_key) REFERENCES dim_artist (artist_key)
);

CREATE TABLE IF NOT EXISTS fact_track_artist (
    track_artist_key bigint GENERATED ALWAYS AS IDENTITY,
    track_key        integer NOT NULL,
    artist_key       integer NOT NULL,
    popularity       smallint NOT NULL,
    danceability     double precision,
    energy           double precision NOT NULL,
    valence          double precision,
    acousticness     double precision NOT NULL,
    tempo            numeric(7,3),
    n_artists        smallint NOT NULL,
    is_collaboration boolean NOT NULL,
    CONSTRAINT pk_fact_track_artist PRIMARY KEY (track_artist_key),
    CONSTRAINT uq_fact_track_artist_grain UNIQUE (track_key, artist_key),
    CONSTRAINT fk_fta_track FOREIGN KEY (track_key) REFERENCES dim_track (track_key),
    CONSTRAINT fk_fta_artist FOREIGN KEY (artist_key) REFERENCES dim_artist (artist_key)
);

CREATE INDEX IF NOT EXISTS ix_fact_award_artist ON fact_award (artist_key);
CREATE INDEX IF NOT EXISTS ix_fact_track_artist_artist ON fact_track_artist (artist_key);
CREATE INDEX IF NOT EXISTS ix_bridge_track_genre_genre ON bridge_track_genre (genre_key);

COMMENT ON TABLE fact_award IS 'Grano: un premio Grammy (año, categoría, nominado) acreditado a un artista emparejado con Spotify. Un premio compartido por N artistas genera N filas.';
COMMENT ON TABLE fact_track_artist IS 'Grano: la participación de un artista en una pista única de Spotify. Las medidas de la pista se repiten por cada artista participante.';

COMMIT;
