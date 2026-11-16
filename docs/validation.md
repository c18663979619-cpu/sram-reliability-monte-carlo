# Numerical validation and revision record

Reviewed and executed on **16 November 2026** using Python 3.12.6, NumPy 2.3.5, and Matplotlib 3.10.7. These checks establish numerical behavior of the supplied implementation, not agreement with fabricated devices.

## Original baseline

The [original notebook at commit 14cfa37](https://github.com/c18663979619-cpu/sram-reliability-monte-carlo/blob/14cfa37a0bb26cf161bea8136c269e943ecd4e9e/sram-reliability-monte-carlo.ipynb) was run sequentially in a fresh process. It reproduced mean SNM 229.129681 mV, standard deviation 12.096212 mV, and 8/10,000 values below 180 mV at 1.0 V. The original source and outputs remain available in Git history.

## What changed and why

| Item | Original | Review revision |
|---|---|---|
| Model scope | Broad 6T/read/yield wording | Explicit behavioral inverter-pair study |
| Supply sweep | Fixed normalized VTC shape | Fixed physical gain 14 V⁻¹, consistent with the single-cell model |
| SNM lobe selection | Diagonal split at zero | Closed lobes bounded by three intersections |
| Grids | Multiple implicit 200/250/500-point settings | Centralized 1,001/4,097-point defaults |
| Numerical implementation | Stateful notebook cells | Shared module, bounded batches, independent reference |
| Tail summary | “Worst case” mean minus 3σ | Empirical percentile and pointwise Wilson intervals |
| Environment | Python 3.12 badge / Python 2 metadata | Executed Python 3 notebook and recorded dependencies |

The revised 1.0 V mean is **229.145636 mV**, a change of **+0.015955 mV**, and the event count remains **8**. The numerical refinement does not materially change that headline result.

Supply results change because the model assumption changes. At 0.70 V, mean SNM changes from **155.21 mV** to **107.35 mV**; at 1.10 V it changes from **253.74 mV** to **271.79 mV**. This is not presented as evidence that either model predicts real SRAM more accurately. [Full before/after data](../data/baseline_comparison.csv) also include the revised implementation with the original normalized-gain assumption.

## Independent reference and grid study

66 cases (64 independent samples with seed 2026, the matched example, and the deliberate mismatch) were evaluated at 0.70, 1.00, and 1.10 V. Maximum absolute discrepancy from the bisection reference:

| Supply | 501 diagonal points | 1,001 points (default) | 2,001 points |
|---|---:|---:|---:|
| 0.70 V | 0.002480 mV | 0.000669 mV | 0.000206 mV |
| 1.00 V | 0.005860 mV | 0.001556 mV | 0.000417 mV |
| 1.10 V | 0.007307 mV | 0.001902 mV | 0.000570 mV |

All default-grid comparisons meet the predeclared **0.01 mV** absolute tolerance. The checked discrepancy is below the 0.01 mV display precision of the main results. See [machine-readable validation](../data/numerical_validation.json).

## Automated checks

The 11 tests cover preserved sample order, random-state isolation, VTC midpoint/bounds, reference agreement, batch-size consistency, grid refinement, inverter-exchange symmetry, zero variation, monostability/extreme mismatch, Wilson boundary cases, and invalid inputs.

```bash
python -m unittest discover -s tests -v
python validate.py
python run_analysis.py
```

The reference-agreement and grid-refinement tests use a 0.01 mV tolerance; batch-size consistency uses 0.001 mV. The separate study above uses a different seed from the main Monte Carlo population. Tests do not cover arbitrary models or every possible threshold offset.

The narrative notebook is also executed from a clean kernel using `python scripts/execute_notebook.py`. Source hashes and exact core dependency versions are recorded in `data/summary.json`; `environment-lock.txt` records the full environment used for this review.

All four code cells completed with no notebook error outputs. The sandboxed review host emitted a process-enumeration permission warning during kernel shutdown; the runner exited successfully and saved the executed notebook. This host-specific cleanup warning is separate from numerical execution.

A separate command-line rerun produced byte-identical figures and generated data to the notebook run. The ten raw-sample tables contain exactly 10,000 unique, ordered sample IDs; the manifest records their partitioning. Splitting this dataset into complete 1,000-row tables keeps the source and review interfaces manageable without dropping samples.

## Regenerating the historical comparison

Run the original notebook from the linked commit in a separate directory, creating `figures/` first. Compare its printed output and supply arrays with the revised CSV. To reproduce its gain assumption using the revised model, call `snm_batch(samples, vdd=v, gain_per_v=14/v)`. Small residual differences then reflect grid/domain/lobe implementation changes. No original result is silently replaced in the revision record.
