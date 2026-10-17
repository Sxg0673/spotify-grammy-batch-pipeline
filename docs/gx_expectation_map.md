# Mapa de expectativas de GX a reglas de calidad

Generado por `src/gx_setup.py` desde las suites registradas en `gx/`. No editar a mano.

| Suite | Rule ID | Expectativa | Columna(s) | Parámetros | Severidad | Requerimientos |
|---|---|---|---|---|---|---|
| `spotify_raw_suite` | DQ-S01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `spotify_raw_suite` | DQ-S01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `spotify_raw_suite` | DQ-S02 | `ExpectColumnValuesToNotBeNull` | track_id | mostly=1 | critical | R1-R4 |
| `spotify_raw_suite` | DQ-S03 | `ExpectCompoundColumnsToBeUnique` | track_id, track_genre | mostly=0.99 | warning | R1-R4 |
| `spotify_raw_suite` | DQ-S04 | `ExpectColumnValuesToBeBetween` | popularity | min_value=0.0, max_value=100.0, mostly=1 | critical | R1,R4 |
| `spotify_raw_suite` | DQ-S05 | `ExpectColumnValuesToBeBetween` | danceability | min_value=0.0, max_value=1.0, mostly=1 | critical | R1 |
| `spotify_raw_suite` | DQ-S05 | `ExpectColumnValuesToBeBetween` | energy | min_value=0.0, max_value=1.0, mostly=1 | critical | R1 |
| `spotify_raw_suite` | DQ-S05 | `ExpectColumnValuesToBeBetween` | valence | min_value=0.0, max_value=1.0, mostly=1 | critical | R1 |
| `spotify_raw_suite` | DQ-S05 | `ExpectColumnValuesToBeBetween` | acousticness | min_value=0.0, max_value=1.0, mostly=1 | critical | R1 |
| `spotify_raw_suite` | DQ-S06 | `ExpectColumnValuesToBeBetween` | tempo | min_value=0.0, mostly=1 | critical | R1 |
| `spotify_raw_suite` | DQ-S07 | `ExpectColumnValuesToNotBeNull` | artists | mostly=0.99 | warning | R1-R4 |
| `spotify_raw_suite` | DQ-S08 | `ExpectColumnValuesToNotBeNull` | track_genre | mostly=0.99 | warning | R2 |
| `spotify_raw_suite` | DQ-S09 | `ExpectColumnValuesToBeBetween` | tempo | min_value=0.0, strict_min=True, mostly=0.99 | info | R1 |
| `spotify_raw_suite` | DQ-S10 | `ExpectColumnValuesToBeBetween` | popularity | min_value=1.0, mostly=0.8 | info | R1,R4 |
| `grammy_raw_suite` | DQ-G01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `grammy_raw_suite` | DQ-G01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `grammy_raw_suite` | DQ-G02 | `ExpectColumnValuesToNotBeNull` | year | mostly=1 | critical | R1,R3 |
| `grammy_raw_suite` | DQ-G02 | `ExpectColumnValuesToBeBetween` | year | min_value=1958.0, max_value=2019.0, mostly=1 | critical | R1,R3 |
| `grammy_raw_suite` | DQ-G03 | `ExpectColumnValuesToNotBeNull` | category | mostly=1 | critical | R1-R4 |
| `grammy_raw_suite` | DQ-G04 | `ExpectColumnValuesToNotBeNull` | winner | mostly=1 | critical | R1,R3,R4 |
| `grammy_raw_suite` | DQ-G04 | `ExpectColumnValuesToBeInSet` | winner | value_set=[True], mostly=1 | critical | R1,R3,R4 |
| `grammy_raw_suite` | DQ-G05 | `ExpectCompoundColumnsToBeUnique` | year, category, nominee | mostly=1 | critical | R4 |
| `grammy_raw_suite` | DQ-G06 | `ExpectCompoundColumnsToBeUnique` | year, category | mostly=0.95 | warning | R1,R3,R4 |
| `grammy_raw_suite` | DQ-G07 | `ExpectColumnValuesToNotBeNull` | artist | mostly=0.5 | warning | R1-R4 |
| `grammy_raw_suite` | DQ-G08 | `ExpectColumnValuesToNotBeNull` | nominee | mostly=0.99 | warning | R1,R3,R4 |
| `dim_artist_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `dim_artist_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `dim_artist_suite` | DQ-P02 | `ExpectColumnValuesToNotBeNull` | artist_bk | mostly=1 | critical | R1-R4 |
| `dim_artist_suite` | DQ-P02 | `ExpectColumnValuesToBeUnique` | artist_bk | mostly=1 | critical | R1-R4 |
| `dim_year_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `dim_year_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `dim_year_suite` | DQ-P02 | `ExpectColumnValuesToNotBeNull` | year | mostly=1 | critical | R1-R4 |
| `dim_year_suite` | DQ-P02 | `ExpectColumnValuesToBeUnique` | year | mostly=1 | critical | R1-R4 |
| `dim_year_suite` | DQ-P05 | `ExpectColumnValuesToBeBetween` | year | min_value=1958.0, max_value=2018.0, mostly=1 | critical | R1,R3 |
| `dim_year_suite` | DQ-P05 | `ExpectColumnValuesToBeInSet` | decade | value_set=[1950, 1960, 1970, 1980, 1990, 2000, 2010], mostly=1 | critical | R1,R3 |
| `dim_category_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `dim_category_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `dim_category_suite` | DQ-P02 | `ExpectColumnValuesToNotBeNull` | category_bk | mostly=1 | critical | R1-R4 |
| `dim_category_suite` | DQ-P02 | `ExpectColumnValuesToBeUnique` | category_bk | mostly=1 | critical | R1-R4 |
| `dim_genre_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `dim_genre_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `dim_genre_suite` | DQ-P02 | `ExpectColumnValuesToNotBeNull` | genre_name | mostly=1 | critical | R1-R4 |
| `dim_genre_suite` | DQ-P02 | `ExpectColumnValuesToBeUnique` | genre_name | mostly=1 | critical | R1-R4 |
| `dim_track_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `dim_track_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `dim_track_suite` | DQ-P02 | `ExpectColumnValuesToNotBeNull` | track_id | mostly=1 | critical | R1-R4 |
| `dim_track_suite` | DQ-P02 | `ExpectColumnValuesToBeUnique` | track_id | mostly=1 | critical | R1-R4 |
| `bridge_track_genre_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `bridge_track_genre_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `bridge_track_genre_suite` | DQ-P03 | `ExpectCompoundColumnsToBeUnique` | track_id, genre_name | mostly=1 | critical | R1-R4 |
| `fact_award_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `fact_award_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `fact_award_suite` | DQ-P03 | `ExpectCompoundColumnsToBeUnique` | year, category_bk, nominee, artist_bk | mostly=1 | critical | R1-R4 |
| `fact_award_suite` | DQ-P05 | `ExpectColumnValuesToBeBetween` | year | min_value=1958.0, max_value=2018.0, mostly=1 | critical | R1,R3 |
| `fact_track_artist_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `fact_track_artist_suite` | DQ-P01 | `ExpectTableRowCountToBeBetween` | (tabla) | min_value=1 | critical | R1-R4 |
| `fact_track_artist_suite` | DQ-P03 | `ExpectCompoundColumnsToBeUnique` | track_id, artist_bk | mostly=1 | critical | R1-R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToNotBeNull` | popularity | mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | popularity | min_value=0.0, max_value=100.0, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToNotBeNull` | energy | mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | energy | min_value=0.0, max_value=1.0, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToNotBeNull` | acousticness | mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | acousticness | min_value=0.0, max_value=1.0, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | danceability | min_value=0.0, max_value=1.0, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | valence | min_value=0.0, max_value=1.0, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P06 | `ExpectColumnValuesToBeBetween` | tempo | min_value=0.0, strict_min=True, mostly=1 | critical | R1,R4 |
| `fact_track_artist_suite` | DQ-P08 | `ExpectColumnValuesToBeBetween` | n_artists | min_value=1.0, mostly=1 | critical | R3 |
| `prepared_checks_suite` | DQ-P01 | `ExpectTableColumnsToMatchSet` | (tabla) | - | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_fact_award_year | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_fact_award_category | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_fact_award_artist | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_fact_track_artist_track | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_fact_track_artist_artist | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_bridge_track | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P04 | `ExpectColumnValuesToBeBetween` | orphans_bridge_genre | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P07 | `ExpectColumnValuesToBeBetween` | audio_partial_nulls | min_value=0.0, max_value=0.0, mostly=1 | critical | R1 |
| `prepared_checks_suite` | DQ-P08 | `ExpectColumnValuesToBeBetween` | collaboration_mismatches | min_value=0.0, max_value=0.0, mostly=1 | critical | R3 |
| `prepared_checks_suite` | DQ-P09 | `ExpectColumnValuesToBeBetween` | songs_without_single_representative | min_value=0.0, max_value=0.0, mostly=1 | critical | R1,R3,R4 |
| `prepared_checks_suite` | DQ-P10 | `ExpectColumnValuesToBeBetween` | awarded_mismatches | min_value=0.0, max_value=0.0, mostly=1 | critical | R1-R4 |
| `prepared_checks_suite` | DQ-P11 | `ExpectColumnValuesToBeBetween` | match_rate | min_value=0.4, mostly=1 | warning | R1-R4 |
