# E7 Test B: fallo controlado de calidad

## Escenario
Corrida manual `manual__2026-10-17T06:32:28.193035+00:00` (DAG v2) con el parámetro
`spotify_source = spotify_dataset_bad.csv`. El archivo se genera con `src/make_bad_source.py` y es igual
al original salvo una fila con `popularity = 150`. El original no se modifica (sha256 prefijo `b202fa4990`).

## Resultado observado
- `extract_spotify`, `extract_grammys` y `validate_grammys_raw`: success.
- `validate_spotify_raw`: failed. Regla DQ-S04 (crítica), 1 fila inesperada (0.001%) en `popularity`.
  Log: `max severity failure: critical | acción: STOP`.
- `transform_and_integrate`, `validate_prepared`, `load_dw`: upstream_failed (nunca se ejecutaron).
- Duración total del run: 35 s.

## Por qué se detiene
La política de severidad define que una falla crítica detiene el pipeline. La excepción `CriticalQualityError`
se convierte en `AirflowFailException`, por lo que Airflow no la reintenta: la tarea tiene un solo intento
(`attempt=1.log`), aunque las tareas locales tienen `retries=1`. Repetir no cambia los datos.

## Qué se conservó
- La evidencia de GX se guarda antes de lanzar la excepción (`validation/spotify_raw_summary.json`).
- El DW no se modificó: conteos idénticos a la carga anterior (ver `dw_despues_de_falla.txt`).
- No existe la carpeta `prepared` del run, porque la transformación no corrió.

## Archivos
- `validate_spotify_raw_attempt1.log`: log del único intento.
- `validation/`: resúmenes y definiciones de validación de GX.
- `dw_despues_de_falla.txt`: conteos del DW tras la falla.
- `E7_B_trigger_params.png`, `E7_B_graph.png` y `E7_B_grid.png`: parámetro activado, Graph (falla en rojo, aguas abajo upstream_failed) y Grid (un intento en la tarea fallida).
