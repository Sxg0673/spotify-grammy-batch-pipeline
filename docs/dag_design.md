# Diseño del DAG

Implementa: `dags/reliable_music_pipeline.py`. Airflow 3.1.8, TaskFlow (`airflow.sdk`).
Patrón base: Activity 3, Apéndice A. El DAG solo orquesta; la lógica vive en `src/`.

## 1. Estructura

    extract_spotify -> validate_spotify_raw --+
                                              +-> transform_and_integrate -> validate_prepared -> load_dw
    extract_grammys -> validate_grammys_raw --+

| Tarea | Función | Entrada | Salida (XCom) |
|---|---|---|---|
| `extract_spotify` | `src.extract.extract_spotify` | Parámetro `spotify_source` | Ruta del raw |
| `extract_grammys` | `src.extract.extract_grammys` | Parámetro `grammy_table` | Ruta del raw |
| `validate_spotify_raw` | `src.validation.run_raw_gate` | Ruta del raw | Resumen de la compuerta |
| `validate_grammys_raw` | `src.validation.run_raw_gate` | Ruta del raw | Resumen de la compuerta |
| `transform_and_integrate` | `src.transform.run_transform` | Las dos rutas raw; depende con `>>` de ambas compuertas raw | Ruta de `prepared/` |
| `validate_prepared` | `src.validation.run_prepared_gate` | Ruta de `prepared/` | Resumen de la compuerta |
| `load_dw` | `src.load.run_load` | Ruta de `prepared/`; depende con `>>` de `validate_prepared` | Conteos y controles |

- Interfaces: las tareas intercambian rutas y resúmenes pequeños, nunca DataFrames (§6.11).
- Datos por corrida: `data/work/<run_id>/` (raw, validation, prepared, reportes).
- Dependencias de control: la transformación no se ejecuta si alguna compuerta raw falla; la carga no se ejecuta si la compuerta preparada falla. Las tareas bloqueadas quedan en `upstream_failed`.

## 2. Configuración

| Parámetro | Valor | Justificación |
|---|---|---|
| `schedule` | `None` | Corridas manuales e inspeccionables, como en la práctica de clase |
| `catchup` | `False` | Sin ejecuciones retroactivas |
| `max_active_runs` | `1` | La carga vacía y recarga el DW; dos corridas a la vez podrían intercalarse |
| Importaciones | Dentro de cada tarea | El archivo del DAG se analiza con frecuencia; importar pandas y GX al inicio lo haría lento |
| `params.spotify_source` | `spotify_dataset.csv` (por defecto) o `spotify_dataset_bad.csv` | Activa la falla controlada del Test B sin editar el DAG; cada corrida queda registrada con su configuración |
| `params.grammy_table` | `grammy_awards` (por defecto) o `grammy_awards_bad` | Ídem, para la fuente Grammy |

## 3. Política de fallas y reintentos (§6.11)

| Condición | Tipo | Respuesta del pipeline | ¿Reintento? | Justificación |
|---|---|---|---|---|
| Falta archivo, tabla o columna; tipo imposible (`SourceContractError`) | Determinista, contrato | Falla la tarea; lo siguiente queda bloqueado | No | La misma entrada vuelve a fallar |
| Falla `critical` en una compuerta (`CriticalQualityError`) | Determinista, calidad | Falla la compuerta tras guardar la evidencia; lo siguiente queda bloqueado | No | Como DQ02 en la Activity 3 (Step 23): repetir reproduce la falla |
| Falla `warning` o `info` en una compuerta | Calidad | Se registra en log y JSON; continúa | — | Política de severidad (`docs/gx_design.md`) |
| Supuesto de la transformación roto (`TransformContractError`) | Determinista | Falla la tarea | No | Repetir no cambia los datos |
| Llave huérfana o conteo distinto en la carga (`LoadIntegrityError`) | Determinista | Se deshace la transacción; falla | No | El DW conserva la carga anterior |
| PostgreSQL no disponible o conexión cortada (`extract_grammys`, `load_dw`) | Transitorio, operacional | Reintento | Sí: 3 intentos, cada 30 s | Un reinicio del contenedor tarda segundos y su healthcheck revisa cada 10 s; 90 s cubren la recuperación sin ocultar una caída real. Reintentar la carga es seguro: es transaccional e idempotente |
| Falla de infraestructura del executor: tarea terminada por SIGKILL o sin heartbeat (incidente del 16-oct-2026, run `18:24:52`) | Transitorio, operacional | Reintento | Sí: 1 intento, tras 10 s (`default_args`, tareas locales) | El incidente no se reprodujo en el rerun medido (pico de 1,023 MiB sobre 4.8 GiB en el scheduler; causa probable: contención de CPU en el API server, no confirmada). Un solo reintento cubre una falla puntual sin ocultar una falla persistente; los errores deterministas no se reintentan porque van como `AirflowFailException` |
| Error en tareas locales (archivos, GX, transformación) | Local | Falla | No | Sin red de por medio: un fallo es de código o de datos, y reintentar lo repetiría |

Mecanismo: Airflow reintenta cualquier excepción salvo `AirflowFailException`. Cada tarea convierte las cuatro excepciones deterministas de `src/errors.py` en `AirflowFailException`; las tareas con acceso a base de datos tienen `retries=3` (cada 30 s) y las demás `retries=1` (cada 10 s) mediante `default_args`.

## 4. Observabilidad (§6.11)

| Pregunta | Dónde se responde |
|---|---|
| ¿Qué corrió? | DAG Run, `run_id` y parámetros (impresos al inicio de cada extracción) |
| ¿Cuándo? | Fechas de la DAG Run y de cada tarea en la interfaz; `extracted_at_utc`, `validated_at_utc` y `loaded_at_utc` en los reportes |
| ¿Funcionó? | Estados de la DAG Run y de las tareas; conteos en el log de cada tarea y en los reportes |
| ¿Dónde falló? | Primera tarea en `failed`; las siguientes en `upstream_failed` |
| ¿Por qué? | Mensaje de la excepción en el log (regla y ruta de la evidencia); `*_summary.json` de GX |
| ¿Qué pasó después? | Reintento (intentos visibles en la interfaz), parada o continuación con advertencia según la política |

## 5. Rerun seguro (§7.3)

La carga vacía y recarga las 8 tablas en una sola transacción: un rerun con la misma entrada deja el DW idéntico (mismos conteos y medidas de control); una carga que falla a mitad se deshace y el DW conserva la carga anterior. Las llaves sustitutas no se reinician (`etl_user` no es dueño de las secuencias), así que cada carga asigna llaves nuevas; las llaves de negocio son las estables.
