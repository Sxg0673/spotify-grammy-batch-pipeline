"""Compuertas de validación con Great Expectations (taller §6.6, §6.7 y §6.9).

Sigue el patrón de la práctica de clase (candidate_validation.py, Activity 3): ejecutar la
validación, recorrer cada resultado, obtener la máxima severidad fallida y decidir la acción.
La evidencia se guarda siempre ANTES de aplicar la política, para que una corrida fallida
deje su resultado (docs/gx_design.md).
"""
import json
from datetime import datetime, timezone

from great_expectations.expectations.metadata_types import FailureSeverity

from src.errors import CriticalQualityError
from src.extract import read_raw, run_dir
from src.gx_setup import get_context

# Política de severidad (docs/gx_design.md, sección 3); etiquetas de la práctica de clase
ACTIONS = {
    FailureSeverity.CRITICAL: "STOP",
    FailureSeverity.WARNING: "CONTINUE WITH WARNING",
}


def decide(max_severity):
    """Ninguna falla o solo fallas info -> CONTINUE."""
    return ACTIONS.get(max_severity, "CONTINUE")


def _severity_name(severity):
    return getattr(severity, "value", severity)


# ---------------------------------------------------------
# Lectura de resultados (Steps 17 y 19 de la práctica)
# ---------------------------------------------------------

def summarize(validation_result):
    rows = []
    for result in validation_result.results:
        config = result.expectation_config
        kwargs = config.kwargs
        detail = result.result or {}
        rows.append({
            "rule_id": (config.meta or {}).get("rule_id"),
            "expectation": getattr(config, "type", None) or getattr(config, "expectation_type", None),
            "column": kwargs.get("column") or kwargs.get("column_list") or "(tabla)",
            "severity": _severity_name(config.severity),
            "success": bool(result.success),
            "unexpected_count": detail.get("unexpected_count"),
            "unexpected_percent": detail.get("unexpected_percent"),
            "partial_unexpected_list": (detail.get("partial_unexpected_list") or [])[:5],
        })
    return rows


def _print_summary(gate, rows, max_severity, action):
    print(f"\n[validation] {gate} | max severity failure: {_severity_name(max_severity)} | acción: {action}")
    for row in rows:
        percent = row["unexpected_percent"]
        percent = f"{percent:.3f}%" if isinstance(percent, (int, float)) else "-"
        print(f"  {row['rule_id']:<7} {row['severity']:<8} success={str(row['success']):<5} "
              f"{row['column']} | unexpected {row['unexpected_count']} ({percent})")


def _write_evidence(run_id, gate, validation_results, rows, max_severity, action, rows_validated):
    out_dir = run_dir(run_id) / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, result in validation_results.items():
        (out_dir / f"{name}.json").write_text(
            json.dumps(result.to_json_dict(), indent=2, ensure_ascii=False, default=str))
    summary = {
        "gate": gate,
        "run_id": run_id,
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_validated": rows_validated,
        "max_severity_failure": _severity_name(max_severity),
        "action": action,
        "expectations": rows,
    }
    summary_path = out_dir / f"{gate}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return str(summary_path)


def _enforce(gate, rows, max_severity, summary_path):
    """Política: critical bloquea. La evidencia ya está guardada cuando se lanza la excepción."""
    if max_severity == FailureSeverity.CRITICAL:
        failed = sorted({r["rule_id"] for r in rows if not r["success"] and r["severity"] == "critical"})
        raise CriticalQualityError(
            f"{gate}: falla crítica en {failed}. Procesamiento posterior bloqueado. Evidencia: {summary_path}")


# ---------------------------------------------------------
# Compuerta raw (Steps 20 y 21 de la práctica; validate_raw de la Activity 3)
# ---------------------------------------------------------

def run_raw_gate(run_id, source, raw_path):
    """Valida el archivo raw de una fuente con su Checkpoint y aplica la política.

    Devuelve un resumen pequeño (apto para XCom) o lanza CriticalQualityError.
    """
    gate = f"{source}_raw"
    df = read_raw(raw_path, source)

    context = get_context()
    checkpoint = context.checkpoints.get(f"{gate}_checkpoint")
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})
    validation_result = list(checkpoint_result.run_results.values())[0]

    max_severity = validation_result.get_max_severity_failure()
    action = decide(max_severity)
    rows = summarize(validation_result)

    summary_path = _write_evidence(run_id, gate, {f"{gate}_validation_definition": validation_result},
                                   rows, max_severity, action, rows_validated=len(df))
    _print_summary(gate, rows, max_severity, action)
    _enforce(gate, rows, max_severity, summary_path)

    return {"gate": gate, "action": action,
            "max_severity_failure": _severity_name(max_severity), "summary_path": summary_path}
