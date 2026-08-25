# EXAFS fitting-result summary integration

v0.5 integrates already-computed EXAFS fitting results without becoming an EXAFS fitting engine.

This layer is intentionally neutral: values and diagnostic names come from the producing tool/caller. CatalysisWorkbench records them, validates representation/provenance, and produces detached reporting tables. It does not generate FEFF paths, optimize model parameters, calculate uncertainties, or reinterpret statistics.

## Scientific boundary

EXAFS packages such as Larch/Artemis commonly expose path-level quantities including coordination-number-like values, path length/R, sigma-squared, delta-E0 and amplitude-related parameters, plus fit-level diagnostics such as R-factor- or chi-square-like quantities.

Those diagnostics are not assumed to have universal cross-program definitions. A producer label is retained as supplied rather than normalized into a CatalysisWorkbench statistic.

## EXAFSFitValue

`EXAFSFitValue` stores one externally reported scalar:

- `value`;
- optional `uncertainty`;
- `status`.

Allowed statuses:

- `reported`;
- `fitted`;
- `fixed`;
- `derived`;
- `unavailable`.

`unavailable` is an explicit state with no numeric value or uncertainty.

This makes the distinction between

```text
reported value = 0
```

and

```text
value unavailable
```

unambiguous.

Uncertainties must be finite and non-negative when supplied. CatalysisWorkbench does not calculate them.

## Suspicious external fit values

The summary layer is not a scientific censor. If an external fit reports a finite but suspicious value, such as a negative fitted sigma-squared, the value is retained unchanged.

This is deliberate. Clipping or silently replacing an externally reported parameter would destroy provenance and could hide a poor/unphysical fit. Scientific interpretation/quality assessment belongs in a separate reviewed analysis layer.

## EXAFSPathSummary

One path/shell has a stable `key`, optional display `label`, metadata, and explicit fields:

- `coordination_number`;
- `r_angstrom`;
- `sigma2_angstrom2`;
- `delta_e0_ev`;
- `amplitude`.

Each field is an `EXAFSFitValue`; omitted fields are normalized to explicit unavailable state.

The field names encode the standard units expected by this neutral interchange contract:

- R: angstrom;
- sigma-squared: angstrom squared;
- delta-E0: eV;
- coordination number: dimensionless count-like scalar.

`amplitude` is intentionally generic. It must not be silently identified with `S0^2` or another producer-specific parameter unless the caller records that meaning in metadata/provenance.

## EXAFSFitDiagnostic

A fit-level diagnostic stores:

- producer label;
- numeric value;
- optional producer unit;
- optional metadata.

The label is preserved exactly apart from trimming outer whitespace. For example, `R-factor`, `reduced chi-square`, and another tool's similarly named statistic remain distinct labels.

## EXAFSFitSummary

A fit summary retains:

- `producer`;
- `source_id`;
- ordered path summaries;
- ordered producer diagnostics;
- deeply immutable metadata.

Stable path keys must be unique. Diagnostic labels must also be unique within one summary so downstream addressing is deterministic.

## Reporting tables

`exafs_fit_summary_frame(summary)` returns a detached pandas DataFrame with one row per path and explicit columns for each value, uncertainty and status.

Representative columns include:

```text
producer
source_id
path_key
path_label
coordination_number
coordination_number_uncertainty
coordination_number_status
r_angstrom
r_angstrom_uncertainty
r_angstrom_status
sigma2_angstrom2
sigma2_angstrom2_uncertainty
sigma2_angstrom2_status
delta_e0_ev
delta_e0_ev_uncertainty
delta_e0_ev_status
amplitude
amplitude_uncertainty
amplitude_status
```

`exafs_fit_diagnostics_frame(summary)` returns a separate detached diagnostic table with the producer's exact diagnostic labels/units. This separation prevents fit-level statistics from being repeated or accidentally interpreted as path parameters.

Returned DataFrames are copies for reporting/export; changing them does not mutate the immutable scientific summary.

## Metadata and provenance

Path, diagnostic and summary metadata are deeply frozen. Nested mappings, sequences, sets and NumPy arrays cannot be mutated through the retained result. `metadata_dict()` returns an independent mutable copy when serialization or editing is needed.

## Example

```python
from catalysis_workbench.experimental.characterization import (
    EXAFSFitDiagnostic,
    EXAFSFitSummary,
    EXAFSFitValue,
    EXAFSPathSummary,
    exafs_fit_summary_frame,
)

summary = EXAFSFitSummary(
    producer="Larch",
    source_id="fit-001",
    paths=(
        EXAFSPathSummary(
            key="fe-o-1",
            label="Fe-O first shell",
            coordination_number=EXAFSFitValue(5.8, 0.4, status="fitted"),
            r_angstrom=EXAFSFitValue(1.98, 0.02, status="fitted"),
            sigma2_angstrom2=EXAFSFitValue(0.006, 0.001, status="fitted"),
            delta_e0_ev=EXAFSFitValue(2.3, 0.5, status="fitted"),
        ),
    ),
    diagnostics=(EXAFSFitDiagnostic("R-factor", 0.0123),),
)
frame = exafs_fit_summary_frame(summary)
```

The example labels/values are illustrative only. CatalysisWorkbench does not infer which external field should map to these neutral fields without an explicit caller/adapter decision.

## Explicit non-actions

This block does not provide:

- FEFF path generation;
- Artemis/Larch nonlinear fitting;
- parameter constraints;
- uncertainty calculation;
- R-factor or chi-square conversion/redefinition;
- native opaque-project-file parsing;
- fit-quality acceptance/rejection criteria.

Those require separate reviewed contracts if added later.
