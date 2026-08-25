# CatalysisWorkbench

**CatalysisWorkbench** is a Python workbench for quantitative post-processing, comparative analysis, and publication-quality visualization of catalysis experimental, characterization, and computational data.

The reviewed v0.1 scientific foundation covers common one-dimensional XY workflows: tabular import, reusable processing, LSV/polarization curves, XRD, Raman, and exact-size PNG/SVG/PDF export. The v0.2 quantitative-electrochemistry release is complete: shared electrochemistry quantity/provenance conventions, scatter/bar rendering, Tafel analysis, Faradaic efficiency, product partial-current density, activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability analysis, and RRDE/Koutecky-Levich basics are released as `v0.2.0`. The v0.3 extended-characterization release is also complete: reviewed FTIR / ATR-FTIR, TGA / DTG / TPR / TPD thermal analysis, basic gas-sorption isotherm processing/publication plotting, and ICP/elemental-composition integration are released as `v0.3.0`.

v0.4 is released as Git tag `v0.4.0` on reviewed release commit `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`, and its GitHub Release has been published from that existing immutable tag. The shared constrained peak-fitting foundation was reviewed and merged through Issue #75 / PR #76 at `b6f428d96df9950373c17e5de487ac4113a2aacc`. The XPS preparation layer was reviewed and merged through Issue #79 / PR #80 at `a13dbd541b299f79d83e47f079c4638b082a8061`, followed by constrained XPS fitting through Issue #83 / PR #84 at `7897393e1e1e9e4d23fad774b4eeecdd70e2a90b` and XPS publication plotting/diagnostics through Issue #87 / PR #88 at `3eab8c8e936cf1897081b7a396306288e517a3bb`. The initial EIS layer completed Issue #91 / PR #92 at `cd8dd171a16576067934a13ad3ac41d0fb18d55a`. Quantitative BET completed Issue #95 / PR #96 at `c76a49d64e096d6db001c27c598356baa797f3a9`. Product calibration and inverse sample quantification completed the planned scientific scope through Issue #99 / PR #100 at `adc0f50178d899b4f257842da6e7bac553a25254`. Gate A / Issue #103 / PR #104 completed the unified fresh-wheel/public-API audit at merge commit `ce06abc11559fa7679869fc83a59356735ce6824`; Gate B / Issue #105 / PR #106 finalized and exact-wheel validated version `0.4.0`; Gate C / Issue #107 created and reverse-verified tag `v0.4.0`.

v0.5 is released as `v0.5.0`. The reviewed scientific scope includes explicit XAS/XANES preparation and normalization; FT-EXAFS and WT-EXAFS transforms/visualization; neutral EXAFS fitting-result summaries; immutable atomic structures with optional POSCAR/CONTCAR/CIF/XYZ adapters; explicit periodic-image geometry, coordination and caller-mapped structure comparison; renderer-neutral static structure visualization; and explicit total/relative/reaction/adsorption-energy post-processing. Gate A release hardening completed through #136/#137 at `0ffcd7e4a89340d993468039ba83b44bc7638050`; Gate B finalized and exact-wheel validated distribution/runtime version `0.5.0` through #138/#139 at release commit `9400ac0044ac333d2cae228554c08d955a816a4c`; Gate C / #142 reverse-verified tag `v0.5.0` exactly on that commit. The public GitHub Release `CatalysisWorkbench v0.5.0` is published from the existing tag with reviewed release notes. PyPI/package-registry publication remains deferred.

## Install from a source checkout

CatalysisWorkbench currently targets Python 3.11+.

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The tagged v0.1.0 release used a separate release-hardening gate followed by a final-version gate; see [`docs/RELEASING.md`](docs/RELEASING.md). v0.2 followed the dedicated Gate A/B/C procedure in [`docs/V0_2_RELEASING.md`](docs/V0_2_RELEASING.md), v0.3 followed the same separation in [`docs/V0_3_RELEASING.md`](docs/V0_3_RELEASING.md), v0.4 uses [`docs/V0_4_RELEASING.md`](docs/V0_4_RELEASING.md), and v0.5 uses [`docs/V0_5_RELEASING.md`](docs/V0_5_RELEASING.md). The reviewed `v0.3.0` tag remains fixed on release commit `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; `v0.4.0` remains fixed on `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`; and `v0.5.0` remains fixed on `9400ac0044ac333d2cae228554c08d955a816a4c`. The v0.5 GitHub Release is published from that existing tag. A Git tag or GitHub Release does not itself publish a package-registry artifact, and PyPI publication is currently deferred.

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

## Quantitative BET fitting

The reviewed quantitative BET API is exported from `catalysis_workbench.experimental.characterization` and consumes the existing prepared gas-sorption `Series` / `SorptionCondition` / `SorptionWindow` state. `evaluate_bet_region()` retains exact measured candidate points, the BET and Rouquerol transforms, OLS diagnostics, and independent physical-consistency state. `fit_bet()` fails closed unless the required positive-parameter, increasing `n(1-p)`, and monolayer-loading-inside-region checks all pass.

Surface area calculation requires caller-visible loading conversion inputs and a positive molecular cross-sectional area; the library does not infer gas properties from an adsorbate label. BET preprocessing provenance is also fail-closed: reviewed sorption preparation, measured-point crop, and explicit relative-pressure conversion are accepted, while unknown or y/grid-altering transformations are rejected. `plot_bet_fit()` is a lazy passive adapter over retained BET points and retained OLS fit arrays and performs no fitting, region search, conversion, sorting, smoothing, or resampling. Full equations, result semantics, validation evidence, and deferred automatic-region workflows are documented in [`docs/BET.md`](docs/BET.md).

## Product calibration and sample quantification

The reviewed product-analysis API is exported from `catalysis_workbench.experimental.product`. It consumes already integrated analytical responses and keeps calibration upstream of the existing Faradaic-efficiency/product-rate layer. `fit_calibration()` supports an explicit linear calibration with either a free intercept or an exactly fixed zero intercept, optional measured-point-only `CalibrationRange`, retained regression/residual state, and fail-closed immutable reconstruction.

`quantify_response()` separately inverts a reviewed calibration, requires an exact response-unit match, rejects extrapolation by default, rejects negative inferred quantities instead of clipping them, and applies only explicit ordered positive dimensionless `QuantificationFactor` values. Replicate summaries report arithmetic mean, sample SD and RSD when defined. `plot_calibration()` is a lazy passive `FigureSpec` adapter over retained calibration points and fit-line arrays. Raw GC/HPLC/NMR parsing, peak detection/integration/assignment, hidden response-factor libraries, automatic model/range selection, and FE/electron-stoichiometry calculation remain outside this layer. Full semantics and prior-art/license boundaries are documented in [`docs/PRODUCT_CALIBRATION.md`](docs/PRODUCT_CALIBRATION.md).

## v0.5 XAS, structure, and DFT post-processing

The reviewed v0.5 characterization stack adds explicit XAS/XANES preparation and normalization, FT-EXAFS, WT-EXAFS, and neutral EXAFS fitting-result summaries. Numerical transform state is retained and plotting remains passive; the library does not become a full FEFF/Artemis fitting environment.

The computation stack adds immutable atomic structures, optional POSCAR/CONTCAR/CIF/XYZ adapters through the reviewed `structure` extra, explicit periodic-image geometry/coordination/comparison, renderer-neutral static structure scenes, and basic DFT energy ledgers/relative/reaction/adsorption-energy post-processing. Structure visual radii/colors never feed back into scientific bond/coordination analysis, and DFT helpers do not apply CHE, ZPE, entropy, chemical-potential, or stoichiometric inference.

See [`docs/V0_5_PLAN.md`](docs/V0_5_PLAN.md), [`docs/XAS.md`](docs/XAS.md), [`docs/EXAFS.md`](docs/EXAFS.md), [`docs/WT_EXAFS.md`](docs/WT_EXAFS.md), [`docs/EXAFS_FIT_SUMMARIES.md`](docs/EXAFS_FIT_SUMMARIES.md), [`docs/STRUCTURES.md`](docs/STRUCTURES.md), [`docs/STRUCTURE_GEOMETRY.md`](docs/STRUCTURE_GEOMETRY.md), [`docs/STRUCTURE_VISUALIZATION.md`](docs/STRUCTURE_VISUALIZATION.md), and [`docs/DFT_ENERGETICS.md`](docs/DFT_ENERGETICS.md) for the reviewed contracts.

## Public API map

The supported import surfaces are intentionally organized by responsibility rather than re-exporting every object from the package root.

- `catalysis_workbench.core`: `Axis`, `Series`, `Dataset`.
- `catalysis_workbench.io`: `read_csv`, `read_txt`, `read_excel`, `read_tabular`, `TabularReadError`.
- `catalysis_workbench.processing`: crop, normalization, offset, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, Dataset mapping, processing errors/results, plus the reviewed shared constrained peak-fitting contracts and `fit_peaks`.
- `catalysis_workbench.experimental.echem`: reviewed LSV processing/configuration; explicit electrochemistry quantity/reference/provenance helpers; Tafel fitting; Faradaic-efficiency analysis and closure QA; product partial-current density and closure QA; catalyst-/metal-mass and ECSA activity normalization; TOF/TOFapp; CV/Cdl/ECSA; stability analysis; RRDE metrics; Koutecky-Levich fitting/apparent electron-number helpers; explicit EIS validation, R/C/CPE circuit evaluation/fitting, EIS diagnostics, and lazy Nyquist/Bode publication adapters.
- `catalysis_workbench.experimental.characterization`: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas-sorption, ICP/elemental-composition, quantitative BET, XPS preparation/constrained fitting/plotting/diagnostics, explicit XAS/XANES preparation/normalization/comparison, FT-EXAFS, WT-EXAFS, EXAFS fitting-result summaries, and their passive publication adapters.
- `catalysis_workbench.experimental.product`: `CalibrationRange`, `CalibrationFitResult`, `QuantificationFactor`, `QuantificationResult`, `QuantificationSummary`, `fit_calibration`, `quantify_response`, `summarize_quantification_replicates`, and lazy `plot_calibration`.
- `catalysis_workbench.computation`: immutable atomic-structure contracts and file adapters, explicit periodic-image geometry/coordination/comparison, renderer-neutral structure scenes, and explicit DFT energy ledger/relative/linear-combination/adsorption-energy post-processing.
- `catalysis_workbench.visualization`: `FigureSpec`, `LayoutSpec`, `PlotStyle`, `SeriesStyle`, annotations/export settings, presets, shared curve/scatter/bar renderers, `plot_structure`, `plot_relative_energies`, and `export_figure`.

Objects or functions in implementation modules that are not exported by these package-level `__all__` surfaces should be treated as internal and may change during development.

## Scope

CatalysisWorkbench focuses on data that require secondary processing before they can be interpreted or used in an SCI figure.

### Experimental data

- Electrochemistry: the v0.2 core is released — LSV/polarization processing, shared quantity/provenance conventions, Tafel, Faradaic efficiency, partial current density, mass/ECSA activity normalization, TOF/TOFapp, CV/Cdl/ECSA, stability, and RRDE/K-L basics. The v0.4 EIS semantics, basic equivalent-circuit fitting, Nyquist/Bode plotting, and diagnostics are released in `v0.4.0`.
- Characterization: XRD, Raman, FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas-sorption, and ICP/composition are implemented and released in v0.3. The shared constrained peak-fitting foundation, XPS preparation/constrained fitting/publication plotting/diagnostics, and quantitative BET are released in `v0.4.0`. v0.5 adds reviewed XAS/XANES, FT-EXAFS, WT-EXAFS and EXAFS fitting-summary post-processing.
- Product analysis: explicit linear calibration, inverse quantification, extrapolation state, named dimensionless factors, replicate summaries and passive calibration plotting are released in `v0.4.0`. Raw vendor-file parsing, chromatographic/NMR peak integration and product assignment remain later/out-of-scope work.

### Computational data

v0.5 implements immutable atomic structures, POSCAR/CONTCAR/CIF/XYZ adapters, explicit periodic-image geometry/coordination/comparison, static renderer-neutral structure visualization, and explicit total/relative/reaction/adsorption-energy post-processing. CHE/free-energy thermodynamics, DOS/PDOS, Bader charge, COHP/ICOHP, charge-density difference, and related electronic-structure post-processing remain planned for v0.6+.

### Visualization

The shared visualization layer provides publication-ready curve, scatter, categorical bar, XAS/EXAFS map, static structure, and relative-energy rendering with adjustable figure/axes geometry, typography, lines/markers, ticks, legends, annotations, limits, presets, explicit errors where supplied, stable-key styling, and exact-size PNG/SVG/PDF export. Scientific renderers remain passive consumers of reviewed retained state. Later releases will build advanced volumetric visualizations and interactive editing on the same explicit figure-state/scene-state model.

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
│   ├── characterization/
│   └── product/
├── computation/       # DFT and atomistic post-processing
└── visualization/     # Publication-quality rendering
```

Scientific calculation and visualization are deliberately separated:

```text
Raw data -> I/O -> standardized data -> scientific analysis -> result -> visualization/export
```

A catalyst or sample name remains lightweight metadata on a data series; CatalysisWorkbench does not introduce a laboratory sample-management system.

## Release and development status

The v0.1 common-XY foundation, v0.2 quantitative electrochemistry, v0.3 extended characterization, v0.4 advanced experimental analysis, and v0.5 XAS/structure/basic-DFT release are published on GitHub. The reviewed `v0.3.0` tag remains fixed on `845ac4c15d399a8816c7ba66d61ea6ec4cc11293`; `v0.4.0` remains fixed on `bb4cb26a500eb1a1a1ce98fdf42760d33e7d7cd6`; and `v0.5.0` remains fixed on `9400ac0044ac333d2cae228554c08d955a816a4c`. The v0.4 and v0.5 GitHub Releases are published from their existing tags. PyPI/package-registry publication is deferred.

v0.5 scientific implementation and all release gates are complete. The architecture checkpoint is #115/#116; XAS/XANES #117/#118; FT-EXAFS #119/#120; WT-EXAFS #121/#122; EXAFS fitting summaries #123/#124; atomic structures/adapters #125/#126; geometry/coordination/comparison #127/#129; static structure visualization #130/#131; and basic DFT energetics #132/#133. The scientific-completion commit is `a7ebd009ec83b0aeb068ad2d2f6712c17a783f1f`. Gate A completed at `0ffcd7e4a89340d993468039ba83b44bc7638050`; Gate B release commit is `9400ac0044ac333d2cae228554c08d955a816a4c`; Gate C #142 verified `v0.5.0` on that exact commit; GitHub Release #144 is complete. Issue #143 is the final docs-only synchronization checkpoint.

New functionality follows a strict feature loop: prior-art scan with license recording, implementation/regression tests, Draft PR, exact-head CI, scientific/API/compatibility review, direct fixes, fresh CI after every head change, second review on the final exact head, Ready/merge gate, expected-head squash merge, `main` verification, then Issue closure.

See [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) for the project-wide execution model and current checkpoint, [`docs/V0_5_PLAN.md`](docs/V0_5_PLAN.md) for the v0.5 architecture/completion state, [`docs/V0_5_RELEASING.md`](docs/V0_5_RELEASING.md) for v0.5 Gate A/B/C and release evidence, [`docs/V0_4_RELEASING.md`](docs/V0_4_RELEASING.md) for the v0.4 release-gate record, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the long-range release scope. Technique-specific reviewed contracts are linked from the capability sections above.

## Roadmap

- **v0.2:** released as `v0.2.0` after reviewed scientific implementation and Gate A/B/C release validation.
- **v0.3:** released as `v0.3.0` with FTIR/ATR-FTIR, TGA/DTG/TPR/TPD, basic gas sorption, and ICP/composition after Gate A/B/C validation.
- **v0.4:** released as `v0.4.0` with shared fitting, XPS, EIS, quantitative BET, and product calibration after Gate A/B/C validation; GitHub Release published, PyPI deferred.
- **v0.5:** released as `v0.5.0` with XAS/EXAFS, structures/geometry/static structure visualization, and basic DFT energetics after Gate A/B/C validation; GitHub Release published, PyPI deferred.
- **v0.6:** electronic-structure and catalysis-thermodynamics post-processing including CHE/free-energy, DOS/PDOS, Bader, COHP/ICOHP and charge-density-difference analysis.
- **v0.7-v1.0:** advanced volumetric visualization, operando/time-resolved analysis, reproducible batch workflows, and a local GUI.

The `main` branch is kept stable. New work should be developed through feature/release branches and pull requests, and live GitHub repository state remains authoritative if descriptive documentation becomes stale.
