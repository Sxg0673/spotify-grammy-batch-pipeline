"""Transformación e integración (docs/transformation_design.md).

Aplica reglas de ingeniería documentadas (pasos S1-S7, G1-G5 e integración) sobre los
archivos raw ya validados y escribe un CSV por tabla del modelo, con llaves de negocio,
más transform_report.json. Ninguna regla existe para que una validación pase.
"""
import json
import re
import unicodedata
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src import schemas as s
from src.errors import TransformContractError
from src.extract import NA_KW, read_raw, run_dir

SEPARATORS = re.compile(r"\s*(?:,|&|\band\b|\bwith\b|\bfeaturing\b|\bfeat\b\.?)\s*")  # D4
EXCLUSION_LIST = {"various artists", "original cast"}                                 # D13
NEW_ARTIST_MARK = "new artist"                                                       # D2
SPOTIFY_CONSTANT_COLUMNS = ["artists", "track_name", "danceability", "energy",
                            "valence", "acousticness", "tempo"]                      # S3


# ---------------------------------------------------------
# Normalización común (D4)
# ---------------------------------------------------------

def normalize(value):
    """Minúsculas, sin tildes, sin espacios en los bordes y con espacios internos colapsados."""
    if value is None or pd.isna(value):
        return None
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_series(series):
    mapping = {u: normalize(u) for u in series.dropna().unique()}
    return series.map(mapping)


def _strip_parens(text):
    return re.sub(r"\s+", " ", re.sub(r"[()]", "", text)).strip()


def _display_names(pairs, key, name):
    """Nombre para mostrar = escritura más frecuente; empate -> orden alfabético (D17, D18)."""
    counts = pairs.groupby([key, name]).size().reset_index(name="n")
    counts = counts.sort_values([key, "n", name], ascending=[True, False, True])
    return counts.drop_duplicates(key)[[key, name]].reset_index(drop=True)


# ---------------------------------------------------------
# Rama Spotify: S1-S7
# ---------------------------------------------------------

def transform_spotify(df, report):
    r = report["spotify"]
    r["filas_entrada"] = int(len(df))

    # S1 (D14): sin artists no se puede identificar ni integrar
    mask = df["artists"].fillna("").str.strip() == ""
    r["excl_sin_artists"] = int(mask.sum())
    df = df[~mask]

    # S2 (D6): duplicados exactos
    dup = df.duplicated()
    r["excl_duplicados"] = int(dup.sum())
    df = df[~dup]

    # S3 (D7): una fila por track_id; solo género y popularidad pueden variar
    distinct = df.groupby("track_id")[SPOTIFY_CONSTANT_COLUMNS].nunique(dropna=False)
    inconsistent = distinct.gt(1).any(axis=1)
    r["pistas_inconsistentes"] = int(inconsistent.sum())
    if r["pistas_inconsistentes"]:
        cols = distinct.columns[distinct.gt(1).any()].tolist()
        raise TransformContractError(
            f"S3: {r['pistas_inconsistentes']} track_id tienen valores distintos en {cols}; "
            "el supuesto de la fuente (solo varían género y popularidad) no se cumple")
    tracks = df.groupby("track_id", as_index=False).agg(
        **{c: (c, "first") for c in SPOTIFY_CONSTANT_COLUMNS}, popularity=("popularity", "max"))
    bridge = (df[["track_id", "track_genre"]].dropna().drop_duplicates()
              .rename(columns={"track_genre": "genre_name"}))
    r["pistas"] = int(len(tracks))

    # S4 (D9): sin análisis de audio -> variables no definidas en nulo
    no_audio = (tracks["tempo"] == 0) & (tracks["danceability"] == 0) & (tracks["valence"] == 0)
    tracks["audio_analyzed"] = ~no_audio
    tracks.loc[no_audio, s.AUDIO_UNDEFINED_COLUMNS] = np.nan
    r["audio_no_analizado"] = int(no_audio.sum())

    # S5 (D4, D10): separar artistas, recortar, normalizar
    pairs = tracks[["track_id", "artists"]].copy()
    pairs["artist_name"] = pairs["artists"].str.split(";")
    pairs = pairs.explode("artist_name")
    pairs["artist_name"] = pairs["artist_name"].str.strip()
    pairs = pairs[pairs["artist_name"].notna() & (pairs["artist_name"] != "")]
    pairs["artist_bk"] = normalize_series(pairs["artist_name"])

    # S7 (D17): nombre para mostrar, antes de deduplicar
    artist_names = _display_names(pairs, "artist_bk", "artist_name")

    pairs = pairs.drop_duplicates(["track_id", "artist_bk"])
    n_artists = pairs.groupby("track_id")["artist_bk"].nunique().rename("n_artists")
    keep = tracks["track_id"].isin(n_artists.index)
    r["pistas_sin_artista_valido"] = int((~keep).sum())
    tracks = tracks[keep].merge(n_artists, left_on="track_id", right_index=True)
    tracks["is_collaboration"] = tracks["n_artists"] > 1

    # S6 (D8): consolidar versiones de una canción
    artist_key = pairs.groupby("track_id")["artist_bk"].apply(lambda x: ";".join(sorted(set(x))))
    tracks["song_bk"] = tracks["track_id"].map(artist_key) + "|" + normalize_series(tracks["track_name"]).fillna("")
    ordered = tracks.sort_values(["song_bk", "popularity", "track_id"], ascending=[True, False, True])
    representatives = set(ordered.drop_duplicates("song_bk")["track_id"])
    tracks["is_song_representative"] = tracks["track_id"].isin(representatives)
    r["canciones"] = int(tracks["song_bk"].nunique())

    measures = ["track_id", "popularity", "danceability", "energy", "valence",
                "acousticness", "tempo", "n_artists", "is_collaboration"]
    fact_track_artist = pairs[["track_id", "artist_bk"]].merge(tracks[measures], on="track_id")
    r["filas_pista_artista"] = int(len(fact_track_artist))
    r["artistas"] = int(len(artist_names))

    return {
        "dim_track": tracks,
        "bridge_track_genre": bridge[bridge["track_id"].isin(tracks["track_id"])],
        "fact_track_artist": fact_track_artist,
        "artist_names": artist_names,
    }


# ---------------------------------------------------------
# Rama Grammy: G1-G5
# ---------------------------------------------------------

def transform_grammys(df, report):
    r = report["grammy"]
    r["filas_entrada"] = int(len(df))

    # G1 (D1): 2019 contaminado con nominados
    excluded = (df["year"] > s.PREPARED_YEAR_MAX).fillna(False)
    r["excl_2019"] = int(excluded.sum())
    df = df[~excluded].copy()

    # G4 (D18, D2): categorías normalizadas y bandera New Artist
    df["category_bk"] = normalize_series(df["category"])
    df["is_new_artist"] = df["category_bk"].str.contains(NEW_ARTIST_MARK, regex=False)
    dim_category = _display_names(df.rename(columns={"category": "category_name"}), "category_bk", "category_name")
    dim_category = dim_category.merge(df.groupby("category_bk", as_index=False)["is_new_artist"].first(), on="category_bk")

    # G5 (D16): década
    dim_year = pd.DataFrame({"year": sorted(df["year"].dropna().unique())})
    dim_year["decade"] = (dim_year["year"] // 10) * 10

    # G2 (D2): en categorías New Artist el artista es el nominee
    recover = df["artist"].isna() & df["is_new_artist"] & df["nominee"].notna()
    df.loc[recover, "artist"] = df.loc[recover, "nominee"]
    r["recuperadas_new_artist"] = int(recover.sum())

    # G3 (D3): filas no atribuibles
    empty = df["artist"].isna() & df["nominee"].isna()
    r["excl_fila_vacia"] = int(empty.sum())
    df = df[~empty]
    no_artist = df["artist"].isna()
    r["excl_sin_artista"] = int(no_artist.sum())
    df = df[~no_artist]
    various = df["artist"].map(lambda a: _strip_parens(normalize(a)) == "various artists")
    r["excl_various_artists"] = int(various.sum())
    df = df[~various]
    no_nominee = df["nominee"].isna()
    r["excl_sin_nominee"] = int(no_nominee.sum())
    df = df[~no_nominee]

    r["filas_atribuibles"] = int(len(df))
    return df[["year", "category_bk", "nominee", "artist"]], dim_category, dim_year


# ---------------------------------------------------------
# Integración (D4, D13)
# ---------------------------------------------------------

def _match(artist, spotify_keys):
    key = normalize(artist)
    if not key or _strip_parens(key) in EXCLUSION_LIST:
        return []
    if key in spotify_keys:                                            # paso 1
        return [key]
    parts = [p.strip() for p in SEPARATORS.split(key)]                 # paso 2
    parts = [p for p in parts if p and _strip_parens(p) not in EXCLUSION_LIST]  # paso 3
    if parts and all(p in spotify_keys for p in parts):                # paso 4
        return list(dict.fromkeys(parts))
    return []                                                          # paso 5


def match_artists(awards, spotify_keys, report):
    r = report["integracion"]
    rows, unmatched = [], 0
    for award in awards.itertuples(index=False):
        artists = _match(award.artist, spotify_keys)
        if not artists:
            unmatched += 1
            continue
        rows.extend((award.year, award.category_bk, award.nominee, a) for a in artists)

    fact = pd.DataFrame(rows, columns=["year", "category_bk", "nominee", "artist_bk"])
    dup = fact.duplicated()
    r["pares_duplicados"] = int(dup.sum())
    fact = fact[~dup].copy()
    fact["award_count"] = 1

    attributable = len(awards)
    r["filas_emparejadas"] = int(attributable - unmatched)
    r["filas_sin_coincidencia"] = int(unmatched)
    r["tasa_emparejamiento"] = round((attributable - unmatched) / attributable, 4) if attributable else 0.0
    r["filas_premio_artista"] = int(len(fact))
    r["artistas_premiados"] = int(fact["artist_bk"].nunique())
    return fact


# ---------------------------------------------------------
# Orquestación del módulo
# ---------------------------------------------------------

SORT_KEYS = {
    "dim_artist": ["artist_bk"], "dim_year": ["year"], "dim_category": ["category_bk"],
    "dim_genre": ["genre_name"], "dim_track": ["track_id"],
    "bridge_track_genre": ["track_id", "genre_name"],
    "fact_award": ["year", "category_bk", "nominee", "artist_bk"],
    "fact_track_artist": ["track_id", "artist_bk"],
}


def run_transform(run_id, spotify_raw_path, grammy_raw_path):
    """Ejecuta la transformación completa y devuelve la ruta de la carpeta prepared/."""
    report = {"run_id": run_id, "spotify": {}, "grammy": {}, "integracion": {}, "salidas": {}}

    spotify = transform_spotify(read_raw(spotify_raw_path, "spotify"), report)
    awards, dim_category, dim_year = transform_grammys(read_raw(grammy_raw_path, "grammy"), report)
    fact_award = match_artists(awards, set(spotify["fact_track_artist"]["artist_bk"]), report)

    dim_artist = spotify["artist_names"].copy()
    dim_artist["is_awarded"] = dim_artist["artist_bk"].isin(fact_award["artist_bk"])   # D15
    tables = {
        "dim_artist": dim_artist,
        "dim_year": dim_year,
        "dim_category": dim_category,
        "dim_genre": spotify["bridge_track_genre"][["genre_name"]].drop_duplicates(),
        "dim_track": spotify["dim_track"],
        "bridge_track_genre": spotify["bridge_track_genre"],
        "fact_award": fact_award,
        "fact_track_artist": spotify["fact_track_artist"],
    }

    out_dir = run_dir(run_id) / "prepared"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df = (df[s.PREPARED_COLUMNS[name]].astype(s.PREPARED_DTYPES[name])
              .sort_values(SORT_KEYS[name]).reset_index(drop=True))
        df.to_csv(out_dir / f"{name}.csv", index=False)
        report["salidas"][name] = int(len(df))

    report["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (out_dir / "transform_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    i = report["integracion"]
    print(f"[transform] pistas {report['spotify']['pistas']} | artistas {report['spotify']['artistas']} | "
          f"premios atribuibles {report['grammy']['filas_atribuibles']} | emparejados {i['filas_emparejadas']} "
          f"({i['tasa_emparejamiento']:.2%}) | artistas premiados {i['artistas_premiados']}")
    for name, n in report["salidas"].items():
        print(f"  {name}: {n} filas")
    return str(out_dir)


def read_prepared(prepared_dir, table):
    return pd.read_csv(f"{prepared_dir}/{table}.csv", dtype=s.PREPARED_DTYPES[table], **NA_KW)
