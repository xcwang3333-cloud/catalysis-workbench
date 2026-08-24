# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

The reviewed v0.1 scientific foundation covers common one-dimensional XY workflows: tabular import, reusable processing, LSV/polarization curves, XRD, Raman, and exact-size PNG/SVG/PDF export. The v0.2 quantitative-electrochemistry release is complete: shared electrochemistry quantity/provenance conventions, scatter/bar rendering, Tafel analysis, Faradaic efficiency, product partial-current density, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability analysis, and RRDE/Koutecky-Levich basics are released as `v0.2.0`. The v0.3 extended-characterization release is also complete: reviewed FTIR / ATR-FTIR, TGA / DTG / TPR / TPD thermal analysis, basic gas-sorption isotherm processing/publication plotting, and ICP/elemental-composition integration are released as `v0.3.0`. Package-registry publication remains separate and has not been performed.

v0.4 implementation is active. The shared constrained peak-fitting foundation was reviewed and merged through Issue #75 / PR #76 at `b6f428d96df9950373c17e5de487ac4113a2aacc`. The XPS preparation layer was reviewed and merged through Issue #79 / PR #80 at `a13dbd541b299f79d83e47f079c4638b082a8061`, adding explicit binding-energy/eV semantics, caller-supplied additive energy correction, measured-point region preparation, direction-safe linear background, and an independently implemented Shirley fixed-point background with explicit convergence/failure state. Constrained XPS components/doublets and shared-fit integration were then reviewed and merged through Issue #83 / PR #84 at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`, adding explicit signed doublet separation, caller-supplied amplitude/shape relations, exact prepared-background alignment, and auditable XPS fit provenance. XPS publication plotting and fit diagnostics were reviewed and merged through Issue #87 / PR #88 at `3eab8c8e936cf1897081b7a396306288e517a3bb`, adding passive retained-array rendering, an optional physical-residual panel, display-only binding-energy direction control, stable `FigureSpec` visual keys, and value-oriented diagnostics. The initial EIS layer was reviewed and merged through Issue #91 / PR #92 at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`, adding explicit complex-impedance semantics, R/C/CPE series/parallel circuits, constrained real+imag fitting, fail-closed fit-result state, passive Nyquist/Bode plotting, and diagnostics. The next v0.4 scientific stage is quantitative BET fitting.

## Install from a source checkout

CatalysisWorkbench currently targets Python 3.11+.

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The tagged v0.1.0 release used a separate release-hardening gate followed by a final-version gate; see [`docs/RELEASING.md`](docs/RELEASING.md). v0.2 followed the dedicated Gate A/B/C procedure in [`docs/V0_2_RELEASING.md`](docs/V0_2_RELEASING.md), and v0.3 followed the same separation in [`docs/V0_3_RELEASING.md`](docs/V0_3_RELEASING.md). The reviewed `v0.3.0` tag resolves to release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`. Ordinary v0.4 feature work does not move that tag or authorize a new release/version/package publication.

## Quickstart: CSV -> LSV processing -> publication export

```python
from catalysis_workbench.experimental.echem import (
    LSVProcessingConfig,
    plot_lsv,
    process_lsv,
    rhe_offset_from_she,
)
from catalysis_workbench.io import read_csv
from catalysis_workbench.visualization import FigureSpec, export_figure, get_preset

raw = read_csv(
    "examples/data/lsv_example.csv",
    x="Potential [V]",
    y="Current [mA]",
    source_id="quickstart-lsv",
)

rhe_offset_v = rhe_offset_from_she(
    reference_potential_vs_she_v=0.210,
    ph=13.0,
    temperature_k=298.15,
)

processed = process_lsv(
    raw[0],
    LSVProcessingConfig(
        rhe_offset_v=rhe_offset_v,
        source_reference="Ag/AgCl",
        resistance_ohm=5.0,
        electrode_area_cm2=0.196,
        normalize_to_current_density=True,
    ),
)

spec: FigureSpec = (
    get_preset("publication")
    .with_layout(figure_width_in=3.5, figure_height_in=2.625)
    .with_style(axis_label_size=8, tick_label_size=7, line_width=1.2)
    .with_export(dpi=300)
)

fig, _ = plot_lsv(processed, spec)
export_figure(fig, "lsv.svg", spec=spec)
export_figure(fig, "lsv.pdf", spec=spec)
export_figure(fig, "lsv.png", spec=spec)
```

The processing API does not silently guess a reference electrode, pH, reference potential, current sign, or electrode area. Those choices remain explicit and are stored in provenance.

Seven complete compact examples are available in [`examples/`](examples/):

```bash
python examples/lsv_quickstart.py
python examples/xrd_quickstart.py
python examples/raman_quickstart.py
python examples/ftir_quickstart.py
python examples/thermal_quickstart.py
python examples/sorption_quickstart.py
python examples/composition_quickstart.py
```

## Shared constrained peak fitting

The v0.4 shared fitting API is exported from `catalysis_workbench.processing`.

```python
import numpy as np

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import (
    FitParameterSpec,
    PeakComponentSpec,
    PeakFitSpec,
    fit_peaks,
)

x = np.linspace(-5.0, 5.0, 401)
y = 12.0 / (0.8 * np.sqrt(2.0 * np.pi)) * np.exp(
    -((x - 0.75) ** 2) / (2.0 * 0.8**2)
)
source = Series(
    x=x,
    y=y,
    key="synthetic",
    x_axis=Axis("energy", unit="eV"),
    y_axis=Axis("intensity", unit="counts"),
)
peak = PeakComponentSpec(
    key="peak_a",
    model="gaussian",
    parameters={
        "amplitude": FitParameterSpec(10.0, lower=0.0),
        "center": FitParameterSpec(0.5, lower=-2.0, upper=2.0),
        "sigma": FitParameterSpec(1.0, lower=0.1, upper=2.0),
    },
)
result = fit_peaks(source, PeakFitSpec(-4.0, 4.0, (peak,)))
print(result.parameters["peak_a.center"].value)
```

The initial reviewed line-shape set is Gaussian, Lorentzian, Voigt, pseudo-Voigt, and Doniach. Fit regions, component count, initial parameters, bounds/ties, background, and optional weights are caller-visible. The library does not automatically detect peaks, assign chemistry, smooth/normalize spectra, select a baseline/background, or infer XPS constraints. Full semantics are documented in [`docs/PEAK_FITTING.md`](docs/PEAK_FITTING.md).

## XPS preparation, constrained fitting, plotting, and diagnostics

The reviewed XPS numerical API is exported from `catalysis_workbench.experimental.characterization`.

```python
from catalysis_workbench.experimental.characterization import (
    linear_xps_background,
    prepare_xps_region,
    shift_xps_binding_energy,
    shirley_xps_background,
    validate_xps_series,
)

validate_xps_series(source)
corrected = shift_xps_binding_energy(
    source,
    0.25,
    reference="caller-supplied reference",
)
region = prepare_xps_region(corrected, 282.0, 292.0)
background = shirley_xps_background(region)
```

XPS x data must explicitly identify binding energy in eV. Energy correction is exactly `E_corrected = E_source + shift_ev`; no chemical label triggers automatic charge correction or literature lookup. Region selection uses measured points only and preserves source storage direction. Linear and Shirley backgrounds use the exact prepared grid; the Shirley calculation exposes convergence settings and fails explicitly if its integral is invalid or does not converge.

Constrained XPS fitting is a thin consumer of the shared fitting API. `XPSDoubletSpec` requires a caller-supplied signed separation, amplitude ratio, and explicit ratios for all remaining model shape/width parameters; no p/d/f textbook ratios are embedded. `fit_xps_peaks()` accepts explicit single components and/or doublets and rejects prepared backgrounds unless their source key/digest, eV and intensity units, source direction, x grid/order, observed intensities, and fit-region coverage match exactly. `XPSPeakFitResult` composes XPS preparation/background/doublet provenance with the immutable shared fit result.

`plot_xps_fit()` is a passive lazy plotting adapter over `XPSPeakFitResult`: it renders the exact retained observed/background/component/best-fit arrays and, when requested, the reviewed physical residual without fitting or model reevaluation. Binding-energy reversal is display-only. `FigureSpec.series_styles` addresses deterministic XPS layer keys plus the actual component keys. `summarize_xps_fit()` returns immutable `XPSFitDiagnostics` copied from already-computed fit/statistical/uncertainty state. Full semantics and license boundaries are documented in [`docs/XPS.md`](docs/XPS.md).

## EIS analysis and publication plotting

The reviewed initial EIS API is exported from `catalysis_workbench.experimental.echem`. EIS data use the existing immutable core `Series`: frequency is explicit in Hz and impedance is stored literally as complex `Z = Z' + jZ''` in ohm. The first circuit vocabulary contains ideal R, C, and CPE elements with explicit series/parallel composition; topology, initial values, fixed/vary state, bounds, and optional residual weights remain caller-visible.

`fit_eis()` uses SciPy trust-region least squares over deterministic real+imag residual channels while retaining the physical complex residual as exactly `Z_observed - Z_best_fit`. `EISFitResult` fail-closes reconstructed state against its circuit, fitted parameters, frequency direction, units, retained arrays, weights, and objective metadata rather than trusting contradictory provenance. `plot_eis_nyquist()` and `plot_eis_bode()` are lazy passive renderers over exact retained complex data; the common `-Im(Z)` Nyquist convention is display-only and Bode phase uses the principal complex angle without hidden phase unwrapping or reordering. Full equations, domains, fitting semantics, plotting conventions, diagnostics, and license boundaries are documented in [`docs/EIS.md`](docs/EIS.md).

## Public API map

The supported import surfaces are intentionally organized by responsibility rather than re-exporting every object from the package root.

- `catalysis_workbench.core`: `Axis`, `Series`, `Dataset`.
- `catalysis_workbench.io`: `read_csv`, `read_txt`, `read_excel`, `read_tabular`, `TabularReadError`.
- `catalysis_workbench.processing`: crop, normalization, offset, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, Dataset mapping, processing errors/results, plus the reviewed shared constrained peak-fitting contracts and `fit_peaks`.
- `catalysis_workbench.experimental.echem`: reviewed LSV processing/configuration; explicit electrochemistry quantity/reference/provenance helpers; Tafel fitting; Faradaic-efficiency analysis and closure QA; product partial-current density and closure QA; catalyst-/metal-mass and ECSA activity normalization; TOF/TOFapp; CV/Cdl/ECSA; stability analysis; RRDE metrics; Koutecky-Levich fitting/apparent electron-number helpers; explicit EIS validation, R/C/CPE circuit evaluation/fitting, EIS diagnostics, and lazy Nyquist/Bode publication adapters.
- `catalysis_workbench.experimental.characterization`: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas-sorption, ICP/elemental-composition, XPS preparation, constrained XPS fitting, passive XPS publication plotting, and fit diagnostics; XPS public state includes validation, explicit additive binding-energy correction, measured-point region preparation, immutable linear/Shirley background results, `XPSDoubletSpec`, `XPSPeakFitResult`, `fit_xps_peaks`, `plot_xps_fit`, `XPSFitDiagnostics`, and `summarize_xps_fit`.
- `catalysis_workbench.visualization`: `FigureSpec`, `LayoutSpec`, `PlotStyle`, `SeriesStyle`, annotations/export settings, presets, shared curve/scatter/bar renderers, and `export_figure`.

Objects or functions in implementation modules that are not exported by these package-level `__all__` surfaces should be treated as internal and may change during development.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data

- Electrochemistry: the v0.2 core is released — LSV/polarization processing, shared quantity/provenance conventions, Tafel, Faradaic efficiency, partial current density, mass/ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, and RRDE/K-L basics. The initial v0.4 EIS semantics, basic equivalent-circuit fitting, Nyquist/Bode plotting, and diagnostics are now implemented on `main`; product calibration remains later roadmap work.
- Characterization: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas-sorption, and ICP/composition are implemented and released in v0.3. The shared constrained peak-fitting foundation plus XPS preparation, constrained fitting, publication plotting, and diagnostics are implemented on `main`. Quantitative BET is the active next v0.4 scientific stage; product calibration follows. XAS remains staged later.
- Product analysis: v0.2 Faradaic efficiency starts from already quantified product amounts or rates. Raw calibration and GC/HPLC/NMR-derived quantification workflows remain staged after the core electrochemistry foundation.

### Computational data

Planned modules cover atomic structures, geometry, adsorption/free energies, CHE, DOS/PDOS, Bader charge, COHP/ICOHP, charge-density difference, and related post-processing. These are not part of the current implemented core.

### Visualization

The shared visualization layer provides publication-ready curve, scatter, and categorical bar rendering with adjustable figure/axes geometry, typography, lines/markers, ticks, legends, annotations, limits, presets, explicit errors where supplied, stable-key styling, and exact-size PNG/SVG/PDF export. XPS fit rendering and EIS Bode rendering now demonstrate the same figure-state model for multi-axes scientific diagnostics. Later releases will build advanced scientific visualizations and interactive editing on the same explicit figure-state model.

## Out of scope

CatalysisWorkbench is not intended to manage synthesis records, laboratory notebooks, inventory, TEM/SEM image processing, instrument control, HPC job submission, or complete VASP workflow management.

## Architecture

```text
src/catalysis_workbench/
├── core/              # Shared scientific data models
├── io/                # Excel/CSV/TXT and scientific file readers
├── processing/        # Reusable mathematical processing + shared fitting
├── experimental/      # Experimental analysis
│   ├── echem/
│   └── characterization/
├── computation/       # DFT and atomistic post-processing
└── visualization/     # Publication-quality rendering
```

Scientific calculation and visualization are deliberately separated:

```text
Raw data -> I/O -> standardized data -> scientific analysis -> result -> visualization/export
```

A catalyst or sample name remains lightweight metadata on a data series; CatalysisWorkbench does not introduce a laboratory sample-management system.

## Release and development status

The v0.1 common-XY foundation, v0.2 quantitative electrochemistry, and v0.3 extended characterization are released. The reviewed `v0.3.0` tag remains fixed on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`.

v0.4 architecture was defined through Issue #73 / PR #74. Shared constrained peak fitting completed Issue #75 / PR #76 with exact-head CI #255, two formal reviews, and squash merge commit `b6f428d96df9950373c17e5de487ac4113a2aacc`. XPS preparation completed Issue #79 / PR #80 with exact-head CI #261, formal reviews `5008700786` and `5008706395`, and squash merge commit `a13dbd541b299f79d83e47f079c4638b082a8061`. Constrained XPS fitting completed Issue #83 / PR #84 with final exact-head CI #267 / run `32739584536`, formal reviews `5009021201` and `5009026855`, and squash merge commit `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b`. XPS publication plotting and diagnostics completed Issue #87 / PR #88 with final exact-head CI #274 / run `32741710370`, final-head review records `5009266827` and `5009270492`, and squash merge commit `3eab8c8e936cf1897081b7a396306288e517a3bb`. EIS completed Issue #91 / PR #92 with final exact-head CI #285 / run `32746265252` on `18d81a0029cc851c136420fc550ec3e823094862`, formal reviews `5009748594` and `5009757335`, and squash merge commit `cd8dd171a16576067934a13ad3ac41d0fb18d55a`. Runtime/distribution version remains `0.3.0`; these development checkpoints do not authorize a v0.4 release/tag/package publication.

New functionality follows a strict feature loop: prior-art scan with license recording, implementation/regression tests, Draft PR, exact-head CI, scientific/API/compatibility review, direct fixes, fresh CI after every head change, second review on the final exact head, Ready/merge gate, expected-head squash merge, `main` verification, then Issue closure.

See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the project-wide execution model and current checkpoint, [`docs/V0_4_PLAN.md`](docs/V0_4_PLAN.md) for the active v0.4 dependency order, [`docs/PEAK_FITTING.md`](docs/PEAK_FITTING.md) for the shared fitting contract, [`docs/XPS.md`](docs/XPS.md) for the XPS preparation/fitting/plotting/diagnostics contract, [`docs/EIS.md`](docs/EIS.md) for the reviewed EIS contract, [`docs/V0_3_RELEASING.md`](docs/V0_3_RELEASING.md) for the completed v0.3 release record, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the long-range release scope.

## Roadmap

- **v0.2:** released as `v0.2.0` after reviewed scientific implementation and Gate A/B/C release validation.
- **v0.3:** released as `v0.3.0` with FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas sorption, and ICP/composition after Gate A/B/C validation.
- **v0.4:** implementation active — shared constrained fitting, the reviewed XPS stack, and the initial EIS analysis/plotting stack are complete; quantitative BET is next, followed by product calibration.
- **v0.5-v0.6:** XAS, structures, and major DFT/electronic-structure post-processing.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved analysis, reproducible batch workflows, and a local GUI.

The `main` branch is kept stable. New work should be developed through feature/release branches and pull requests, and live GitHub repository state remains authoritative if descriptive documentation becomes stale.
