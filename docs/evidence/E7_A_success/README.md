# E7 Test A: ejecución exitosa

## Escenario
Corrida manual `manual__2026-10-16T17:49:00.513553+00:00` (DAG v1) con los parámetros por defecto
(`spotify_dataset.csv` y `grammy_awards`). Las horas de la interfaz están en hora de Bogotá (UTC-5).

## Resultado observado
- 7 tareas en `success`, todas con un solo intento. Duración total: 3:39 (12:49:01 a 12:52:41).
- Extracción: 114,000 filas de Spotify y 4,810 de Grammy.
- Compuerta raw de Spotify: sin fallas, acción CONTINUE.
- Compuerta raw de Grammy: falla la regla DQ-G06 (severidad warning) en 495 filas (10.291%), asociada al año 2019
  (decisión D1 en `docs/quality_rules.md`). Acción: CONTINUE WITH WARNING. No bloquea, como define la política.
- Transformación (`transform_report.json`): 89,740 pistas, 29,796 artistas, 81,165 canciones, 433 premios de 2019 excluidos,
  57 recuperados por "New Artist", 59 de "Various Artists" excluidos, 1,600 sin artista excluidos, 2,712 filas atribuibles,
  1,342 emparejadas (49.48%), 560 artistas premiados.
- Validación preparada: sin fallas críticas. DQ-P11 (tasa de emparejamiento, warning con umbral de 40%) se cumple con 49.48%.
- Carga (`load_report.json`): dim_artist 29,796; dim_year 61; dim_category 628; dim_genre 114; dim_track 89,740;
  bridge_track_genre 113,549; fact_award 1,478; fact_track_artist 123,424.
  Controles: popularidad media 33.4471 y energía media 0.626952.
- Analítica (consultas y dashboard sobre el DW): pendiente, se documenta con E8.

## Qué demuestra cada archivo
- `E7_A_graph.png`: las 7 tareas y sus dependencias terminan en success.
- `E7_A_grid.png`: cada tarea tuvo un solo intento (Try 1) y se ven sus duraciones.
- `E7_A_grammy_gate_warning.png`: log de la compuerta de Grammy con DQ-G06 en warning y la acción CONTINUE WITH WARNING.
  La línea `ERROR - Calculating Metrics` es la barra de progreso de GX registrada como ERROR en esta corrida;
  se corrigió después (0 apariciones en los logs de validación del run del 17-oct 07:25).
- `E7_A_load_dw_log.png`: conteos por tabla y controles de la carga.
- `validation/*.json`, `transform_report.json`, `load_report.json`, `*_metadata.json`: resultados completos de GX,
  conciliación de la transformación y resumen de la carga.
