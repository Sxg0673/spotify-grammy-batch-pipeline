# E7 Test C2: recuperación tras reintentos

## Escenario
Se detiene `postgres-data`, se lanza el DAG y a los 45 s se ejecuta `docker compose start postgres-data`
(`E7_C2_db_reinicio.png`). Run `manual__2026-10-17T07:25:03.766394+00:00` (DAG v2).

## Resultado observado
- `extract_grammys`: 3 intentos. Inicios (UTC): 07:25:04.89, 07:25:38.13 y 07:26:09.94 (33.2 y 31.8 s entre sí).
  Los intentos 1 y 2 fallaron con `could not translate host name "postgres-data"`; el intento 3 extrajo 4,810 filas.
- Las otras 6 tareas tuvieron un solo intento. El run termina en success con 2:23 de duración (51 s más que un run sin fallas, 1:32).
- La recarga del DW dejó los mismos conteos (`dw_despues_de_recuperacion.txt`) y `load_report.json` solo difiere del
  rerun en `run_id` y `loaded_at_utc`.

## Qué demuestra
Una falla transitoria de la base se absorbe con los reintentos configurados sin intervención sobre el DAG y sin efectos
duplicados en el DW.

## Archivos
- `E7_C2_db_reinicio.png`, `E7_C2_graph.png` (todo en success, `extract_grammys` con Try 3).
- `extract_grammys_attempt1.log` a `attempt3.log`, `load_report.json`, `dw_despues_de_recuperacion.txt`.
