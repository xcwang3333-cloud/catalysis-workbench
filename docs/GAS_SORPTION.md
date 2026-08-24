# Basic gas-sorption isotherm contract

Issue #58 adds a conservative gas-sorption isotherm layer for explicit measured `P/P0` versus adsorbed quantity data and publication plotting. It deliberately stops before BET surface-area fitting, Rouquerol region selection, pore-volume or pore-size-distribution calculations.

Quantitative BET fitting is added later by v0.4 Issue #95 as a separate consumer of this measured-isotherm contract. Its equations, consistency checks, unit conversion and explicit caller-region policy are documented in [`BET.md`](BET.md). The v0.3 behavior described below remains unchanged.

## Design boundary

Gas-sorption data continue to use the shared immutable `Series` / `Dataset` model. CatalysisWorkbench does not introduce a second isotherm object hierarchy. Numerical handling, experimental-condition metadata, and publication rendering remain separate.

The initial contract requires:

- explicit relative-pressure semantics and fraction/percent units;
- explicit adsorbed-quantity unit/basis;
- explicit adsorbate and measurement temperature;
- explicit adsorption or desorption branch state;
- explicit standard-gas temperature and pressure for `cm^3(STP)/g` data;
- stable `Series.key` addressing for Dataset mappings and visual overrides;
- deterministic source-data digests and processing history;
- no hidden branch inference, sorting, interpolation, smoothing, normalization, unit conversion, fitting, or clipping.

## Relative pressure

The x axis represents relative pressure `P/P0`. Canonical name is `relative_pressure`; unambiguous `p/p0` and `p_p0` aliases are accepted. The inverse quantity `P0/P` is not an alias and must fail validation.

Supported representations are explicit dimensionless fraction (`1`) and percent (`%`). Conversion is always caller-requested:

```python
percent = convert_relative_pressure(isotherm, target_unit="percent")
```

Fraction-to-percent conversion is

\[
(P/P_0)_{\%} = 100(P/P_0)_{\mathrm{fraction}}.
\]

Relative-pressure values must be finite and non-negative. A branch requires at least two measured points and must be strictly monotonic in stored order, ascending or descending, with no duplicates. Source order is preserved. Values above `P/P0 = 1` are not silently clipped; the library preserves the measured input and leaves scientific interpretation to the caller.

## Adsorbed quantity

The y semantic is `adsorbed_quantity` (with documented `loading` / `uptake` aliases). The v0.3 layer accepts explicit per-mass units:

- `mmol/g`;
- `mol/kg`;
- `mg/g`;
- `cm^3(STP)/g`.

`mmol/g` and `mol/kg` are numerically equivalent, but CatalysisWorkbench does not silently convert one into the other. Their unit strings remain compatibility-critical so a plotted overlay cannot disguise different declared representations.

Gas volume at standard conditions is especially ambiguous across instruments and conventions. Therefore `cm^3(STP)/g` requires caller-visible `standard_temperature_k` and `standard_pressure_kpa`. The string `STP` alone is not treated as a sufficient scientific definition.

## Experimental conditions and branch state

A raw measured branch is prepared with an explicit condition:

```python
prepared = prepare_sorption_series(
    raw,
    SorptionCondition(
        adsorbate="N2",
        measurement_temperature_k=77.0,
        branch="adsorption",
    ),
)
```

The condition stores:

- adsorbate identity;
- measurement temperature in kelvin;
- branch (`adsorption` or `desorption`);
- standard-gas condition where required.

Branch identity is never inferred from whether `P/P0` rises or falls. An ascending desorption branch and a descending adsorption branch are both valid when explicitly declared. The stored pressure direction is provenance, not classification.

Adsorption and desorption branches remain separate `Series` objects. This avoids fabricating a joined path, resampling one branch onto the other, or creating implied correspondence between nonmatching pressure points.

## Processing

`SorptionProcessingConfig` initially supports only explicit relative-pressure crop and vertical offset. Defaults perform no scientific transformation beyond preparation/validation.

```python
processed = process_sorption(
    raw,
    condition=SorptionCondition("N2", 77.0, "adsorption"),
    config=SorptionProcessingConfig(
        relative_pressure_min=0.05,
        relative_pressure_max=0.95,
    ),
)
```

Dataset condition/config overrides use stable `Series.key` values. Unknown keys fail. No operation silently drops missing values, sorts points, aligns branches, or interpolates across samples.

## Measured-point window summary

`SorptionWindow` and `summarize_sorption_window()` provide a deliberately model-free direct summary. Inside a caller-supplied relative-pressure interval they report only measured-point count plus measured minimum/maximum loading and their measured pressures.

The helper performs no boundary interpolation. A requested interval containing no actual measured point fails rather than inventing values.

This v0.3 helper itself is not a BET-region selector and does not report monolayer capacity, BET constant, surface area, pore volume, hysteresis area, or pore-size information. v0.4 quantitative BET deliberately reuses `SorptionWindow` as an explicit caller-selected measured region rather than changing this summary behavior.

## Overlay compatibility

Before publication overlay, all selected branches must share:

- adsorbate identity;
- measurement temperature;
- relative-pressure representation/unit;
- loading semantic/family/unit;
- standard-gas condition where relevant.

Sample/material names and branch identity may differ. This allows an adsorption/desorption pair for the same physical experiment while preventing silent comparison of incompatible gas, temperature, pressure representation, or uptake basis.

No unit conversion is performed merely to make an overlay pass. Convert explicitly first when scientifically justified.

## Publication plotting

`plot_sorption()` is a lazy adapter over the shared `FigureSpec`/curve renderer:

```python
fig, ax = plot_sorption(dataset, spec, branch="all")
```

It performs no fitting, interpolation, branch reconstruction, normalization, or unit conversion. Branch selection filters only already-declared metadata.

For immediate readability, adsorption defaults to a solid line and desorption to a dashed line when no stable-key-specific line style has been supplied. Explicit `FigureSpec.series_styles` overrides are authoritative. All typography, figure/axes dimensions, line/marker settings, limits/scales, legends, annotations, and PNG/SVG/PDF export continue to use the shared visualization layer.

Importing `catalysis_workbench.experimental.characterization` does not import Matplotlib. Matplotlib is loaded only when the lazy `plot_sorption()` wrapper is called.

## Prior art and license decisions

The module was scoped after reviewing:

- `pauliacomi/pyGAPS` — MIT. Primary architecture/scientific reference for explicit pressure mode/unit, loading basis/unit, material basis/unit, adsorbate/temperature metadata, branch-aware plotting, and extensive adsorption analysis. CatalysisWorkbench does not copy its implementation and deliberately does not adopt automatic branch inference from pressure direction.
- `hjkgrp/SESAMI_web` — MIT. Workflow/scope reference demonstrating that BET region selection, Rouquerol consistency criteria, and surface-area calculation are substantial quantitative algorithms distinct from raw isotherm plotting.
- `AIF-development-team/adsorptioninformationformat` — MIT. Metadata/interoperability reference reinforcing explicit experimental conditions and units. Issue #58 does not add an AIF or vendor-specific parser.
- `nakulrampal/betsi-gui` — current upstream `LICENSE.txt` directly verifies MIT. The older Issue #58-era `NOASSERTION` repository-metadata note is superseded by this direct license verification. Its dedicated BET/Rouquerol workflow remains reference-only; no implementation is copied or adapted.
- Existing CatalysisWorkbench `FigureSpec` and shared renderer remain the publication backend.

No upstream implementation code is copied.

## Explicitly deferred from the v0.3 foundation

Issue #58 itself does not implement:

- BET surface-area calculation or automatic linear-region selection;
- Rouquerol criteria;
- monolayer capacity or BET C-constant inference;
- total/micropore/mesopore volume calculations;
- BJH, Dollimore-Heal, DFT/QSDFT/NLDFT, Horvath-Kawazoe or related pore-size distributions;
- t-plot, alpha-s, Dubinin or generic adsorption-model fitting;
- automatic hysteresis classification, knee detection, closure detection or hysteresis-area integration;
- automatic adsorption/desorption branch inference;
- AIF or manufacturer-specific parser expansion;
- GUI behavior;
- a `0.3.0` version bump, tag, release, or package-registry publication.

The later quantitative BET implementation is separately contracted by Issue #95 and does not retroactively change the reviewed v0.3 measured-isotherm behavior.
