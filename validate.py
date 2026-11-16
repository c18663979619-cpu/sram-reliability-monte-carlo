"""Quantify numerical agreement; run after the unittest suite."""
import json
from pathlib import Path
import numpy as np
from sram_model import sample_thresholds, snm_batch, snm_reference

ROOT = Path(__file__).resolve().parent


def validate():
    # Separate validation draw, plus explicit nominal/mismatched examples.
    rows = np.vstack([sample_thresholds(64, seed=2026), [.4]*4, [.31, .48, .47, .32]])
    result = []
    for vdd in [.7, 1., 1.1]:
        ref = np.array([snm_reference(t, vdd)[0] for t in rows])
        errors = {}
        for grid in [501, 1001, 2001]:
            a = snm_batch(rows, vdd, diagonal_points=grid)
            errors[str(grid)] = float(np.max(np.abs(a-ref))*1000)
        result.append({"vdd_v": vdd, "max_abs_error_mv_by_diagonal_points": errors})
    passed = all(r["max_abs_error_mv_by_diagonal_points"]["1001"] < .01 for r in result)
    report = {"reference": "per-cell analytic VTC inversion, 48 bisections, 20001 diagonal points",
              "sample_count": len(rows), "random_seed": 2026, "absolute_tolerance_mv": .01,
              "passed": passed, "checks": result,
              "scope": "Numerical agreement within the same behavioral model; no physical calibration."}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data/numerical_validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if not passed: raise AssertionError("Numerical tolerance exceeded")


if __name__ == '__main__':
    validate()
