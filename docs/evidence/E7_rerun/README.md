# E7 Rerun seguro (§7.3)

## Estrategia
Carga con TRUNCATE de las 8 tablas del DW y reinserción en una sola transacción (`src/load.py`). Si la carga falla,
la transacción se deshace y el DW conserva el estado anterior. No se usa RESTART IDENTITY porque `etl_user`
no es dueño de las secuencias: las llaves sustitutas siguen creciendo en cada carga (limitación documentada).
Las llaves de negocio, PK, UNIQUE y FK están en `sql/dw_schema.sql`.

## Escenario
Misma entrada que el Test A (parámetros por defecto). Run `manual__2026-10-17T05:54:39.225421+00:00` (DAG v1),
7 tareas en success, duración 1:32.

## Comparación antes y después
- Conteos del DW: idénticos en las 8 tablas (29,796 / 61 / 628 / 114 / 89,740 / 113,549 / 1,478 / 123,424).
- `load_report.json` y `transform_report.json` del rerun frente a los de `E7_A_success`: las únicas diferencias son
  `run_id` y la marca de tiempo; conteos y controles (popularidad media 33.4471, energía media 0.626952) no cambian.
- Duplicados en llaves de negocio de las dimensiones: 0 (`duplicados_dimensiones.txt`).

## Tras una corrida fallida o parcial
La carga es transaccional: un fallo dentro de `load_dw` deshace todo. La evidencia guardada cubre fallas aguas arriba:
en B y C1 el DW conserva los mismos conteos (`dw_despues_de_falla.txt` en cada carpeta), y C2 recarga tras recuperarse
y vuelve a dar los mismos conteos.

## Archivos
- `E7_rerun_graph.png`: el rerun termina en success.
- `docker_stats.txt`: consumo de los contenedores durante el rerun (pico del scheduler: 1,023 MiB sobre 4.8 GiB).
- `load_report.json`, `transform_report.json`, `*_metadata.json`, `validation/`: resultados del rerun.
