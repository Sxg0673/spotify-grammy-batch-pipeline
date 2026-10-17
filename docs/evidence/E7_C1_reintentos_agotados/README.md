# E7 Test C1: reintentos agotados con la base caída

## Escenario
`postgres-data` se detiene antes del Trigger (`E7_C1_db_detenida.png`) y permanece caído toda la ventana.
Run `manual__2026-10-17T07:12:02.170878+00:00` (DAG v2). Política: `extract_grammys` y `load_dw` tienen
retries=3 con espera de 30 s (`docs/dag_design.md`, sección 3).

## Resultado observado
- `extract_grammys`: 4 intentos (1 + 3 reintentos), todos con `OperationalError: could not translate host name
  "postgres-data" to address`. Inicios (UTC): 07:12:02.99, 07:12:36.62, 07:13:08.01 y 07:13:39.95,
  separados por 33.6, 31.4 y 31.9 s (30 s de espera más la duración del intento).
- `extract_spotify` (9.7 s) y `validate_spotify_raw` (19.0 s): success con un solo intento.
- `validate_grammys_raw`, `transform_and_integrate`, `validate_prepared` y `load_dw`: upstream_failed, 0 intentos.
- Run en failed tras 1:41. El DW conserva los conteos previos (`dw_despues_de_falla.txt`).

## Qué demuestra
El reintento es selectivo: solo se reintenta la tarea con acceso a la base de datos y solo hasta el límite configurado;
después el pipeline falla de forma clara y no avanza sobre datos incompletos.

## Archivos
- `E7_C1_db_detenida.png`, `E7_C1_graph.png`, `E7_C1_grid.png` (Try 4 en `extract_grammys`), `E7_C1_intentos.png` (4 intentos fallidos).
- `extract_grammys_attempt1.log` a `attempt4.log`: log de cada intento.
