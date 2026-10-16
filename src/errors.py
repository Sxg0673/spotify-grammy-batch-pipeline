"""Excepciones del pipeline.

Separan fallas deterministas (no se reintentan) de fallas transitorias (sí se reintentan).
El DAG traduce estas excepciones en fallas sin reintento; un error de conexión a la base
de datos, en cambio, se propaga tal cual y Airflow lo reintenta según la política.
"""


class SourceContractError(Exception):
    """La fuente no cumple su contrato: falta el archivo o la tabla, falta una columna
    requerida o un valor no se puede leer con su tipo declarado. Repetir no lo corrige."""


class CriticalQualityError(Exception):
    """Una compuerta de validación encontró al menos una falla de severidad critical.
    Falla determinista: la misma entrada vuelve a fallar, así que no se reintenta."""


class TransformContractError(Exception):
    """Un supuesto de la transformación sobre la fuente dejó de cumplirse (p. ej. S3: un
    atributo distinto de género y popularidad varía dentro de un track_id). Determinista."""
