# Activity normalization

Issue #24 adds explicit activity normalization to the reviewed v0.2 electrochemistry foundation. The goal is not to create a generic unit-algebra engine or to attach the ambiguous label "specific activity" to any normalized current. The goal is to make the numerator reconstruction, denominator basis, units, sign convention, provenance, and compatibility semantics explicit.

## Prior-art review

The design was informed by comparable open-source electrochemistry projects and scientific terminology resources before implementation.

### `ixdat/ixdat` — MIT

`ixdat` is the main architecture reference for explicit electrochemical calibration state. Its electrochemistry model keeps current/potential values attached to units and calibration context, and electrode-area normalization is represented as explicit calibration state rather than inferred from a sample name.

CatalysisWorkbench adopts that explicit-state principle. It does not adopt ixdat's persistence/database model and does not add ixdat as a dependency for Issue #24.

### `MyPyDavid/elchempy` — MIT

`elchempy` is a Python framework for several electrochemical experiments and separates ORR analysis, plotting, RDE/RRDE/Koutecky-Levich submodules, and test modules. That separation is useful architectural prior art for keeping numerical analysis and publication rendering distinct.

Some workflow helpers also illustrate why CatalysisWorkbench should be stricter: experiment conditions can be recovered or guessed from workflow-specific conventions. Issue #24 will not guess a denominator, catalyst loading, ECSA, or geometric area from filenames, labels, segment counts, or hidden conventions.

No implementation is copied and no dependency is added.

### `gcarrascohuertas/electrochemical_ORR_procesing_autolab` — GPL-3.0

This practical ORR script is useful reference-only prior art for real laboratory post-processing. It stores geometric electrode area as a script-level constant and combines experiment-specific constants, calculations, and plotting in one workflow.

For CatalysisWorkbench this is primarily an anti-pattern reference: normalization quantities must be caller-visible scientific inputs, not hard-coded globals, and calculation must remain separate from plotting. GPL-3.0 code is not copied or adapted.

### `gcarrascohuertas/electrochemical_ECSA_processing_autolab` — GPL-3.0

This project treats ECSA determination as a dedicated electrochemical analysis workflow and reports electrochemical area. That supports the boundary between Issue #24 and Issue #26: Issue #24 consumes an explicitly supplied ECSA denominator; it does not silently derive ECSA from CV data. CV/Cdl/ECSA derivation remains Issue #26.

The repository is GPL-3.0 and beta/script-oriented, so it is reference-only. No implementation is copied or added as a dependency.

### `emmo-repo/domain-sofc` — CC-BY-4.0

The SOFC domain ontology is useful terminology prior art because "specific activity" can be expressed against different bases such as catalyst mass, electrochemically active area, or volume. That confirms that the bare phrase "specific activity" is not a sufficient machine-readable scientific basis.

CatalysisWorkbench therefore records the denominator basis explicitly and does not treat different denominator bases as compatible merely because both are described informally as specific activity.

## Scope for v0.2

Built-in denominator bases are deliberately limited to:

- `catalyst_mass`: total catalyst mass;
- `metal_mass`: active-metal/target-metal mass supplied by the caller;
- `ecsa`: electrochemically active surface area supplied by the caller.

BET-specific surface area and arbitrary composite denominator units are not built into Issue #24. A common BET value such as `m^2 g^-1` is a different composite physical basis from an area or mass denominator and should not be shoehorned into the conservative v0.2 unit layer. A later extension can add additional denominator dimensions after defining their conversion and compatibility contracts explicitly.

## Numerical model

Activity normalization is defined as a two-stage operation:

1. establish an explicit total-current numerator in amperes;
2. divide that numerator by an explicit denominator converted to its canonical basis.

For total-current input:

```text
I = I_source
```

For geometric current-density input:

```text
I = j_geo * A_geo
```

where `A_geo` is an explicit geometric electrode area. A current-density Series cannot be converted to a mass- or ECSA-normalized activity unless the geometric area needed to reconstruct total current is explicit and scientifically compatible with the source normalization state.

The normalized quantities are then:

```text
activity_catalyst_mass = I / m_catalyst
activity_metal_mass    = I / m_metal
activity_ECSA          = I / A_ECSA
```

No reaction-specific stoichiometry is involved in Issue #24. Product partial current can be normalized if it already has explicit partial-current provenance from Issue #23; the normalization step does not recalculate FE.

## Canonical calculation bases

Issue #24 reuses the shared Issue #19 quantity layer rather than introducing a second unit parser.

- total current is converted to `A`;
- mass denominator is converted to `g`;
- ECSA denominator is converted to `cm^2`;
- geometric reconstruction area is converted to `cm^2`.

The implementation may expose publication output units such as:

- `A/g`;
- `mA/mg`;
- `A/mg`;
- `mA/g`;
- `A/cm^2` or `mA/cm^2` for ECSA-normalized activity.

Conversion is dimensional and deterministic. In particular, `1 A/g == 1 mA/mg`; regression tests should make this equivalence explicit rather than rely on intuition about prefixes.

## Sign convention

Normalization must not redefine electrochemical direction.

- `sign_mode="signed"` preserves the sign of the source current.
- `sign_mode="magnitude"` returns the absolute normalized magnitude.

No function automatically changes cathodic negative current to positive current. The selected sign mode is recorded in the result and Series provenance.

## Source-current contract

Accepted source y semantics are limited to explicit current-like data that can be reduced to total current without guessing:

- `current`: direct total-current numerator;
- `current_density`: accepted only when its normalization basis is explicitly geometric and a compatible geometric electrode area is supplied or explicitly selected from trusted source provenance;
- `partial_current_density`: accepted under the same geometric reconstruction rule when it carries compatible Issue #23 source semantics.

An already mass-normalized, metal-mass-normalized, ECSA-normalized, or otherwise non-geometric activity/current-density source must not be normalized again through Issue #24.

## Double-normalization guard

The implementation must reject double normalization before numerical division.

Examples that must fail:

- ECSA-normalized current divided by ECSA again;
- catalyst-mass activity divided by catalyst mass again;
- metal-mass activity passed as if it were geometric current density;
- a current-density source whose axis metadata declares a non-geometric normalization basis;
- a geometric current-density source reconstructed with a conflicting electrode area relative to trusted provenance when that provenance is present.

The error should identify the source normalization state and requested target basis rather than silently attempt to reinterpret it.

## Denominator contract

Every denominator must have:

- explicit basis;
- explicit finite positive value;
- explicit supported unit;
- optional caller-facing source description/provenance when available.

Mass basis is semantic as well as dimensional. `catalyst_mass` and `metal_mass` both have mass units but are scientifically incompatible normalization bases.

No denominator is inferred from `Series.label`, `Series.key`, catalyst name, file name, or an arbitrary metadata field without an explicit API selection.

For Dataset workflows, per-catalyst denominators are mapped by stable non-empty `Series.key`. Display labels are never mapping keys. Missing keys, extra keys, or Dataset series without stable keys fail explicitly.

## Result and provenance contract

The numerical result should be immutable and preserve enough state to reconstruct the reported activity:

- source current/current-density values in their canonical calculation basis;
- source current semantic and original unit;
- any geometric area used to reconstruct total current;
- canonical total-current numerator;
- denominator basis;
- denominator value and original/canonical unit;
- output unit;
- sign mode;
- deterministic source `SourceDataRef` / SHA-256 when operating on a Series;
- stable source key and label where applicable.

The result axis must identify activity semantics and carry compatibility-critical normalization metadata.

Compatibility should distinguish denominator **basis**, not require equal denominator numerical values. Two catalysts normalized by different catalyst masses are scientifically comparable as catalyst-mass activities; catalyst-mass activity and metal-mass activity are not compatible even if both happen to use `A/g`.

Denominator value/unit remain traceable provenance but should not make otherwise equivalent same-basis activities impossible to overlay.

## API direction

The intended public surface is deliberately small:

- `ActivityNormalizationError`;
- immutable `ActivityNormalizationResult`;
- constrained `ActivityBasis` with built-ins `catalyst_mass`, `metal_mass`, and `ecsa`;
- explicit low-level `normalize_activity(...)`;
- `normalize_activity_series(...)`;
- `normalize_activity_dataset(...)` with exact stable-key denominator mapping;
- lazy `plot_activity(...)` adapter using shared curve/scatter rendering;
- an explicit summary/bar adapter only if it can reuse `BarData` without hiding condition selection or statistical aggregation.

Convenience wrappers such as catalyst-mass or ECSA helpers should be added only if they improve semantic clarity without creating parallel calculation paths.

## Publication plotting

Plotting performs no normalization, denominator lookup, interpolation, condition selection, or statistical aggregation.

Already normalized Series/Dataset data can be rendered through shared `render_curves` or `render_scatter`. Bar summaries must reuse the Issue #20 categorical renderer and must receive already explicit summary values or an explicitly selected condition; a plotting function must not silently choose a potential/current point.

Different normalization bases must be rejected by the shared compatibility guard before overlay even when their displayed units are dimensionally identical.

## Regression-test plan

At minimum, implementation tests should cover:

- hand calculation from total current and catalyst mass;
- hand calculation from geometric current density plus explicit geometric area;
- catalyst-mass versus metal-mass semantics with identical physical units;
- ECSA-specific activity from total current and from reconstructable geometric current density;
- `A/g`, `mA/mg`, `A/mg`, `mA/g`, and current/ECSA unit conversions;
- explicit `1 A/g == 1 mA/mg` equivalence;
- signed cathodic and anodic inputs plus magnitude mode;
- non-positive and non-finite denominator rejection;
- unsupported/missing denominator unit rejection;
- current-density input without required geometric area rejection;
- source geometric-area conflict rejection when trusted source provenance is available;
- double-normalization rejection for mass/ECSA/non-geometric sources;
- stable-key Dataset denominator mapping, including missing and unknown keys;
- deterministic source provenance and immutable result arrays;
- shared renderer incompatibility for catalyst-mass versus metal-mass versus ECSA bases;
- lazy Matplotlib import for numerical electrochemistry.

## Explicit non-goals

Issue #24 does not:

- derive ECSA from CV/Cdl data;
- derive metal loading from ICP, catalyst names, or composition metadata;
- infer active-site fraction;
- calculate TOF/TOFapp;
- implement BET-specific-surface-area normalization;
- add a general dimensional-analysis/unit package;
- automatically choose a potential/current condition for bar summaries;
- smooth, interpolate, clip, renormalize, or sign-flip source data.

These boundaries keep activity normalization a traceable scientific transformation rather than a collection of hidden benchmarking assumptions.
