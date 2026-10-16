"""Crea la fuente alterada para el Test B (taller §7.2) sin modificar la original.

Patrón de la Activity 3 (Apéndice B): copiar la fuente e inyectar una violación determinista.
Condición: popularity = 150 en la primera fila -> viola DQ-S04 (Critical; contrato de Spotify 0-100).

Uso, en el contenedor:  python -m src.make_bad_source
"""
import pandas as pd

from src.extract import DATA_DIR, DEFAULT_SPOTIFY_PATH, NA_KW

BAD_PATH = DATA_DIR / "raw" / "spotify_dataset_bad.csv"


def main():
    # Todo como texto: el resto del archivo queda idéntico al original
    df = pd.read_csv(DEFAULT_SPOTIFY_PATH, dtype=str, **NA_KW)
    first = df.index[0]
    before = df.loc[first, "popularity"]
    df.loc[first, "popularity"] = "150"
    df.to_csv(BAD_PATH, index=False)
    print(f"Fuente alterada: {BAD_PATH}")
    print(f"Fila {first} (track_id {df.loc[first, 'track_id']}): popularity {before} -> 150 (viola DQ-S04)")
    print("La fuente original no se modificó.")


if __name__ == "__main__":
    main()
