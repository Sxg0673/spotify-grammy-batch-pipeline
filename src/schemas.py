"""Contrato de columnas y constantes del pipeline (fuente única).

Lo usan gx_setup (expectativas), extract (selección de columnas, D12) y transform (salidas).
Referencias: docs/quality_rules.md, docs/transformation_design.md, docs/dimensional_model.md.
"""

# ---------------------------------------------------------
# Raw: solo las columnas requeridas por R1-R4 (D12)
# ---------------------------------------------------------
SPOTIFY_RAW_COLUMNS = [
    "track_id", "artists", "track_name", "track_genre", "popularity",
    "danceability", "energy", "valence", "acousticness", "tempo",
]
GRAMMY_RAW_COLUMNS = ["year", "category", "nominee", "artist", "winner"]

# ---------------------------------------------------------
# Contrato temporal
# ---------------------------------------------------------
YEAR_MIN = 1958
RAW_YEAR_MAX = 2019          # último año del contrato de la fuente (DQ-G02)
PREPARED_YEAR_MAX = 2018     # 2019 excluido (D1, DQ-P05)
DECADES = list(range(1950, 2020, 10))  # 1950..2010 (D16)

# ---------------------------------------------------------
# Capa preparada (docs/transformation_design.md, sección 1)
# ---------------------------------------------------------
PREPARED_COLUMNS = {
    "dim_artist": ["artist_bk", "artist_name", "is_awarded"],
    "dim_year": ["year", "decade"],
    "dim_category": ["category_bk", "category_name", "is_new_artist"],
    "dim_genre": ["genre_name"],
    "dim_track": ["track_id", "track_name", "song_bk", "is_song_representative", "audio_analyzed"],
    "bridge_track_genre": ["track_id", "genre_name"],
    "fact_award": ["year", "category_bk", "nominee", "artist_bk", "award_count"],
    "fact_track_artist": ["track_id", "artist_bk", "popularity", "danceability", "energy",
                          "valence", "acousticness", "tempo", "n_artists", "is_collaboration"],
}

# Llave de negocio de cada dimensión (DQ-P02)
DIMENSION_KEYS = {
    "dim_artist": "artist_bk",
    "dim_year": "year",
    "dim_category": "category_bk",
    "dim_genre": "genre_name",
    "dim_track": "track_id",
}

# Grano de hechos y puente (DQ-P03)
GRAINS = {
    "bridge_track_genre": ["track_id", "genre_name"],
    "fact_award": ["year", "category_bk", "nominee", "artist_bk"],
    "fact_track_artist": ["track_id", "artist_bk"],
}

# Relaciones para integridad referencial (DQ-P04):
# (columna de chequeo, tabla hija, columna hija, tabla padre, columna padre)
FOREIGN_KEYS = [
    ("orphans_fact_award_year", "fact_award", "year", "dim_year", "year"),
    ("orphans_fact_award_category", "fact_award", "category_bk", "dim_category", "category_bk"),
    ("orphans_fact_award_artist", "fact_award", "artist_bk", "dim_artist", "artist_bk"),
    ("orphans_fact_track_artist_track", "fact_track_artist", "track_id", "dim_track", "track_id"),
    ("orphans_fact_track_artist_artist", "fact_track_artist", "artist_bk", "dim_artist", "artist_bk"),
    ("orphans_bridge_track", "bridge_track_genre", "track_id", "dim_track", "track_id"),
    ("orphans_bridge_genre", "bridge_track_genre", "genre_name", "dim_genre", "genre_name"),
]

# Variables de audio no definidas cuando no hubo análisis (D9)
AUDIO_UNDEFINED_COLUMNS = ["tempo", "danceability", "valence"]

# DataFrame de chequeos entre filas y tablas (una fila, una columna por chequeo)
PREPARED_CHECK_COLUMNS = [fk[0] for fk in FOREIGN_KEYS] + [
    "audio_partial_nulls",                  # DQ-P07
    "collaboration_mismatches",             # DQ-P08
    "songs_without_single_representative",  # DQ-P09
    "awarded_mismatches",                   # DQ-P10
    "match_rate",                           # DQ-P11
]
MIN_MATCH_RATE = 0.40  # DQ-P11
