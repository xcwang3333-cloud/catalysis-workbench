# Turnover frequency (TOF) and apparent TOF (TOFapp)

Issue #25 adds turnover-frequency analysis only after fixing the denominator semantics. The implementation deliberately distinguishes a true active-site-normalized TOF from inventory-normalized apparent values.

## Scientific prior art

The design follows the reporting cautions in the electrocatalysis literature rather than treating every metal-normalized current as an intrinsic turnover frequency.

- Anantharaj et al., *Angewandte Chemie International Edition* (2021), "The Significance of Properly Reporting Turnover Frequency in Electrocatalysis Research", emphasizes that TOF is meaningful only when the active-site count and Faradaic efficiency are handled explicitly.
- Bae et al., *JACS Au* (2021), "Quantification of Active Site Density and Turnover Frequency: From Single-Atom Metal to Nanoparticle Electrocatalysts", defines intrinsic TOF as reaction rate divided by experimentally quantified active-site density/inventory and stresses that apparent activity is the product of site density and per-site TOF.
- The 2022 *Materials Advances* water-electrolysis review notes that using all relevant/total metal atoms as if they were active produces only a lower-limit estimate when true active sites are unknown.

Open-source architecture was also surveyed before coding:

- `samueldy/mkmcxx-tof-demo` is MIT licensed. It is a compact microkinetic TOF plotting example and is useful only as a terminology/visualization reference; it does not supply the experimental electrochemical current-to-rate contract required here.
- `SUNCAT-Center/catmap` is GPLv3. CatMAP is mature microkinetic-modeling prior art for site-based catalytic rates, but its copyleft license and modeling scope make it reference-only for this issue. No code is copied or adapted.
- `mosp-catalysis/MOSP` was inspected as kinetic Monte Carlo / site-specific TOF prior art. It is not used as a dependency and no code is copied.

The scientific equations are standard and implemented independently around CatalysisWorkbench's existing quantity/provenance layer.

## Terminology contract

Three inventory bases are built in:

- `active_sites`: an explicitly supplied inventory that the caller can justify as catalytically active under the reported conditions. Output is `TOF` / `turnover_frequency`.
- `total_metal`: total metal inventory/loading converted to an amount of metal. It is **not** assumed to equal active sites. Output is `TOFapp` / `apparent_turnover_frequency`.
- `bulk_inventory`: another explicit bulk inventory not proven to equal active sites. Output is also `TOFapp`.

The library never upgrades `total_metal` or `bulk_inventory` to intrinsic TOF, even when a paper or catalyst label informally calls the result TOF.

## Inventory units

Inventory is canonicalized to moles of inventory entities.

Amount-of-substance units reuse the shared Issue #19 converter:

- `mol`
- `mmol`
- `umol`
- `nmol`

Discrete inventory counts are also supported explicitly:

- `count`
- `site` / `sites`
- `atom` / `atoms`

Counts are converted to moles using the exact SI Avogadro constant, `6.02214076e23 mol^-1`. The semantic meaning of the entities comes from `inventory_basis`; the count-unit spelling is descriptive and must not be used to infer active-site status.

Every inventory must be finite and strictly positive. No active-site fraction is inferred from ICP loading, catalyst composition, catalyst name, coordination model, ECSA, or microscopy.

## Rate-based equation

For an explicitly quantified product formation rate:

```text
TOF_or_TOFapp = r_product / n_inventory
```

where `r_product` is converted to `mol/s` and `n_inventory` to `mol`.

A product formation rate is required to be finite and non-negative. Negative values are rejected rather than silently taking an absolute value.

## Current-based equation

For product partial current:

```text
r_product = I_product / (n_e * F)
TOF_or_TOFapp = r_product / n_inventory
```

where:

- `I_product` is the **total product partial-current magnitude** in amperes;
- `n_e` is the explicit positive integer electron stoichiometry for one product molecule;
- `F = 96485.33212 C mol^-1` is the shared Faraday constant.

Issue #23 produces product partial **current density**, so a Series/Dataset adapter must reconstruct total partial current with an explicit compatible geometric area before Faraday's law is applied:

```text
I_product = j_product,geo * A_geo
```

No FE is recalculated in Issue #25. Compatible Issue #23 provenance (`analysis=partial_current_density`, `current_source`, and `fe_source`) is mandatory for the partial-current Series path.

## Sign handling

TOF is a non-negative event frequency, but converting a signed electrochemical partial current to a rate must never be hidden.

Current-based APIs therefore require an explicit `current_mode`:

- `nonnegative`: source current values must already be non-negative; no sign transformation is performed.
- `magnitude`: the caller explicitly requests `abs(I_product)` before Faraday conversion.

The selected mode is retained in provenance. The upstream Issue #23 sign mode is also retained when present.

## Output units

The canonical frequency is `s^-1`. Publication-facing conversion is restricted to:

- `s^-1`
- `min^-1`
- `h^-1`

The numerical value is converted only after the canonical calculation.

## Result and provenance contract

An immutable result records enough information to reconstruct the calculation:

- source kind (`molar_rate` or `partial_current`);
- canonical product rate in `mol/s`;
- explicit electron number for current-derived results;
- explicit current mode for current-derived results;
- inventory basis;
- original inventory value/unit;
- canonical inventory amount in mol;
- output unit;
- source key/label/digest for Series-derived results;
- geometric reconstruction area when Issue #23 partial-current density is consumed;
- upstream partial-current provenance and sign mode when available.

## Series and Dataset compatibility

Output y semantics are intentionally different:

- `active_sites` -> `y_axis.name="turnover_frequency"`, label `TOF`;
- `total_metal` / `bulk_inventory` -> `y_axis.name="apparent_turnover_frequency"`, label `TOFapp`.

The y-axis `normalization` metadata is the exact inventory basis. This makes intrinsic TOF and TOFapp impossible to silently overlay through the shared renderer. `total_metal` and `bulk_inventory` are also kept distinct because their denominators are scientifically different.

Per-Series inventory/area mappings in Dataset helpers use exact non-empty `Series.key` values. Display labels are never identifiers.

## Plotting boundary

Plot adapters receive already calculated TOF/TOFapp Series/Datasets. They do not:

- count sites;
- infer metal loading;
- calculate FE;
- choose a potential/current point;
- aggregate replicates;
- interpolate or align grids;
- change current sign;
- renormalize values.

Condition-resolved Series use the shared curve/scatter renderers. Bar summaries remain caller-constructed unless a later explicit condition-selection API is designed.

## Explicit non-goals

Issue #25 does not derive active-site density, ECSA, metal loading, ICP composition, active-site fraction, or reaction mechanism. It does not infer electron stoichiometry from a product name. It does not relabel total-metal-normalized estimates as intrinsic TOF.
