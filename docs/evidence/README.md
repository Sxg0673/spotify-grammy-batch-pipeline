# Registro de evidencias de confiabilidad (§7.4)

Las horas de la interfaz de Airflow están en hora de Bogotá (UTC-5). Los logs guardados están en UTC.

| Evidence ID | Run / Task | Artifact or Path | What It Proves | Related Policy / Rule |
| --- | --- | --- | --- | --- |
| EV-01 | Entorno | `docs/evidence/E1_airflow_version.txt` | Airflow 3.1.8 en la imagen del proyecto | `Dockerfile`, `requirements.txt` |
| EV-02 | Entorno | `docs/evidence/E1_airflow_health.png` | MetaDatabase, Scheduler y Dag Processor sanos; el Triggerer aparece en rojo porque el proyecto no usa tareas diferibles y no despliega ese servicio | `docker-compose.yaml` |
| EV-03 | Fuente Grammy | `docs/evidence/E2_source_load.txt` | Tabla `grammy_awards` cargada (4,810 filas, años 1958-2019) y `etl_user` con solo lectura | `sql/source_setup.sql`, roles |
| EV-04 | Fuente Grammy | `docs/evidence/E2_source_reconciliation.json` | Conciliación del CSV contra la tabla fuente (29 verificaciones) | Preparación de la fuente (§6.2) |
| EV-05 | DW | `docs/evidence/E3_dw_schema.txt` | Esquema del DW creado con PK, UNIQUE y FK | `sql/dw_schema.sql` |
| EV-06 | A / DAG run | `docs/evidence/E7_A_success/E7_A_graph.png` | Las 7 tareas terminan en success | Test A |
| EV-07 | A / DAG run | `docs/evidence/E7_A_success/E7_A_grid.png` | Un solo intento por tarea y duraciones por tarea | Test A, `docs/dag_design.md` |
| EV-08 | A / validate_spotify_raw | `docs/evidence/E7_A_success/validation/spotify_raw_summary.json` | Compuerta de Spotify sin fallas, acción CONTINUE | DQ-S01 a DQ-S10 |
| EV-09 | A / validate_grammys_raw | `docs/evidence/E7_A_success/validation/grammy_raw_summary.json` y `docs/evidence/E7_A_success/E7_A_grammy_gate_warning.png` | Warning DQ-G06 no bloquea (CONTINUE WITH WARNING) | Política de severidad, DQ-G06 |
| EV-10 | A / transform_and_integrate | `docs/evidence/E7_A_success/transform_report.json` | Conciliación de la transformación (descartes, emparejamiento 49.48%) | D1 a D18, DQ-P11 |
| EV-11 | A / validate_prepared | `docs/evidence/E7_A_success/validation/prepared_summary.json` | Capa preparada sin fallas críticas | DQ-P01 a DQ-P11 |
| EV-12 | A / load_dw | `docs/evidence/E7_A_success/load_report.json` y `docs/evidence/E7_A_success/E7_A_load_dw_log.png` | Conteos por tabla y controles de la carga | Carga transaccional |
| EV-13 | Rerun / DAG run | `docs/evidence/E7_rerun/E7_rerun_graph.png` | El rerun con la misma entrada termina en success | §7.3 |
| EV-14 | Rerun / load_dw | `docs/evidence/E7_rerun/load_report.json` | Mismos conteos y controles que el Test A (solo cambian run_id y hora) | §7.3, TRUNCATE y carga |
| EV-15 | Rerun / transform | `docs/evidence/E7_rerun/transform_report.json` | Misma transformación y reconciliación que el Test A | §7.3 |
| EV-16 | Rerun / DW | `docs/evidence/E7_rerun/duplicados_dimensiones.txt` | Sin duplicados en las llaves de negocio de las dimensiones | UNIQUE en `sql/dw_schema.sql` |
| EV-17 | Rerun / entorno | `docs/evidence/E7_rerun/docker_stats.txt` | Consumo de recursos durante el run (pico del scheduler 1,023 MiB de 4.8 GiB) | Diagnóstico del incidente |
| EV-18 | B / DAG run | `docs/evidence/E7_B_failure/E7_B_trigger_params.png` | Se activó la falla con `spotify_dataset_bad.csv` | Test B |
| EV-19 | B / DAG run | `docs/evidence/E7_B_failure/E7_B_graph.png` y `docs/evidence/E7_B_failure/E7_B_grid.png` | validate_spotify_raw falla y las tareas aguas abajo quedan upstream_failed; un solo intento | Test B, política de reintentos |
| EV-20 | B / validate_spotify_raw | `docs/evidence/E7_B_failure/validation/spotify_raw_summary.json` | Resultado de GX: DQ-S04 crítica fallida, acción STOP | DQ-S04 |
| EV-21 | B / validate_spotify_raw | `docs/evidence/E7_B_failure/validate_spotify_raw_attempt1.log` | Log de la tarea fallida y conversión a AirflowFailException | Política de severidad |
| EV-22 | B / DW | `docs/evidence/E7_B_failure/dw_despues_de_falla.txt` | El DW queda intacto tras la falla | Bloqueo de la carga |
| EV-23 | B / explicación | `docs/evidence/E7_B_failure/README.md` | Regla que bloquea y comportamiento aguas abajo | §7.2 |
| EV-24 | C1 / DAG run | `docs/evidence/E7_C1_reintentos_agotados/E7_C1_graph.png` y `docs/evidence/E7_C1_reintentos_agotados/E7_C1_grid.png` | Solo extract_grammys se reintenta (Try 4); el resto, un intento o ninguno | Retries en tareas con base de datos |
| EV-25 | C1 / extract_grammys | `docs/evidence/E7_C1_reintentos_agotados/E7_C1_intentos.png` y `docs/evidence/E7_C1_reintentos_agotados/extract_grammys_attempt4.log` | Cuatro intentos fallidos y error de conexión a `postgres-data` | retries=3, retry_delay 30 s |
| EV-26 | C1 / DW | `docs/evidence/E7_C1_reintentos_agotados/dw_despues_de_falla.txt` | El DW conserva sus conteos tras agotar los reintentos | Carga no ejecutada |
| EV-27 | C1 / explicación | `docs/evidence/E7_C1_reintentos_agotados/README.md` | Intervalos entre intentos de unos 31 a 34 s | `docs/dag_design.md` sección 3 |
| EV-28 | C2 / DAG run | `docs/evidence/E7_C2_recuperacion/E7_C2_graph.png` | El run termina en success con extract_grammys en Try 3 | Reintento selectivo |
| EV-29 | C2 / entorno | `docs/evidence/E7_C2_recuperacion/E7_C2_db_reinicio.png` | La base se levanta durante la ventana de reintentos | Reintento selectivo |
| EV-30 | C2 / extract_grammys | `docs/evidence/E7_C2_recuperacion/extract_grammys_attempt3.log` | El intento 3 extrae 4,810 filas tras dos fallos | retries=3, retry_delay 30 s |
| EV-31 | C2 / load_dw | `docs/evidence/E7_C2_recuperacion/load_report.json` y `docs/evidence/E7_C2_recuperacion/dw_despues_de_recuperacion.txt` | La recarga tras la recuperación no duplica ni altera el DW | §7.3 |
| EV-32 | Incidente | `docs/evidence/E7_incident_executor_sigkill.txt` y `docs/evidence/E7_incident_executor_sigkill.png` | Run del 16-oct con validate_grammys_raw sin arrancar por SIGKILL del executor; causa no confirmada; no se reprodujo con medición | `default_args` retries=1 |
