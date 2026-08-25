# PROCAR projected bands and fat-band plotting

This document records the reviewed v0.7 Block-4 contract for VASP PROCAR projection state, explicit site/orbital aggregation, and passive fat-band plotting.

The architecture authority remains [`V0_7_PLAN.md`](V0_7_PLAN.md). Ordinary band/path/reference semantics remain governed by [`BAND_STRUCTURE.md`](BAND_STRUCTURE.md). Block 4 extends that exact band source; it does not create a second energy/path authority.

## Scientific model

`BandProjectionState` binds one immutable projection result to one exact compatible `BandStructureState`.

The associated `BandStructureState` remains authoritative for:

- ordered source k-points;
- reciprocal-lattice matrix and the retained `2*pi` convention;
- path segments and source labels;
- band order/index;
- physical spin identity;
- source Fermi level and current explicit energy reference;
- all plotted band energies.

PROCAR contributes only the retained projection-weight layer.

Each `BandProjectionChannel` stores one physical spin channel with canonical axis order

```text
(band, kpoint, site, orbital)
```

The current `pymatgen-core` scalar projection order is `(kpoint, band, ion, orbital)`. The adapter performs only the explicit axis transpose needed to align the retained projection tensor with the reviewed Block-3 band axis order. Values are not normalized, clipped, broadened, smoothed, thresholded, or rescaled.

Projection weights are retained as finite, non-negative, dimensionless `vasp-procar-projection-weight` values. CatalysisWorkbench does not reinterpret them as percentages or force their sum to one.

## Site and orbital identity

Site identity comes only from the `AtomicStructure` already attached to the associated band state:

- source site index;
- stable site key;
- element identity.

CatalysisWorkbench retains the orbital/component labels exposed by the reviewed `pymatgen-core.Procar` parser literally and in backend-retained source order. It does not rename orbital labels from chemistry conventions or infer orbital families.

Current `pymatgen-core.Procar` parses the raw PROCAR orbital header by removing the leading `ion` token and the trailing raw-file `tot` token before allocating scalar projection `data`. Therefore the current Block-4 adapter does **not** claim to retain the raw terminal `tot` column. It preserves exactly `parsed.orbitals` and the corresponding scalar component values exposed by the backend, and it does not reconstruct, synthesize, or use the omitted total as a normalization denominator.

## Explicit aggregation

`aggregate_band_projection(...)` requires all scientific selection choices explicitly:

```python
result = aggregate_band_projection(
    projection_state,
    spin="total",
    site_indices=(0, 3),
    orbitals=("s", "pz"),
)
```

The operation:

1. validates the requested physical spin against the associated band state;
2. requires a non-empty, duplicate-free site selection;
3. requires a non-empty, duplicate-free set of exact retained orbital labels;
4. canonicalizes site/orbital identity to retained source order for deterministic provenance;
5. sums only the selected retained weights over site and orbital axes;
6. returns one immutable `(n_bands, n_kpoints)` `AggregatedBandProjection` with explicit `aggregation="sum"`.

It does **not**:

- infer element groups;
- infer `s/p/d/f` families from detailed orbital labels;
- discover active atoms;
- sum spin channels;
- normalize to a maximum;
- normalize to 100%;
- normalize against an inferred or reconstructed total;
- normalize by electron count or occupation;
- apply a projection threshold.

## VASP PROCAR adapter

The public minimum adapter is:

```python
projection = read_procar_projection(
    "PROCAR",
    band_structure=band_state,
    source_id="calc-001",
    kpoint_atol=1e-5,
    energy_atol_ev=1e-4,
)
```

The adapter lazy-imports the existing optional `pymatgen-core` dependency. No new runtime dependency is introduced.

### Compatibility checks

The adapter requires one ordinary non-SOC/non-collinear PROCAR from the same calculation represented by the associated Block-3 band state.

It validates:

- one PROCAR path only; the public minimum API does not concatenate multiple files;
- scalar, non-SOC projection layout;
- exact non-empty unique backend-exposed orbital labels;
- exact k-point count and order;
- k-point coordinates under the caller-visible absolute `kpoint_atol`;
- exact band count;
- PROCAR eigenvalues against retained Block-3 band energies under caller-visible absolute `energy_atol_ev`;
- exact ion/site count;
- finite non-negative scalar projection weights;
- physical spin compatibility.

Current `pymatgen-core` rounds parsed PROCAR k-point coordinates to five decimal places internally. Therefore k-point compatibility is intentionally an explicit tolerance check rather than a false bitwise-equality claim. The tolerance is retained in projection metadata.

The adapter never reorders k-points, selects a nearest path, drops bands, pads missing bands, replaces Block-3 band energies, reconstructs a path from PROCAR, or reconstructs the backend-omitted raw terminal `tot` projection column.

### Physical spin

The physical spin contract follows the associated Block-3 band state, not a backend container key name:

- a non-spin-polarized band state contains `total`; exactly one backend PROCAR channel is mapped to physical `total`, even when the backend calls it `Spin.up`;
- a collinear spin-polarized band state requires complete `up` and `down` backend channels;
- spin summation is not performed.

## SOC and non-collinear boundary

Current `pymatgen-core` exposes `xyz_data=None` for ordinary non-SOC PROCAR state and vector `xyz_data` for SOC/non-collinear magnetization projections. The initial Block-4 contract intentionally rejects the latter state.

CatalysisWorkbench does not collapse vector/spinor projection information into misleading scalar `up/down` channels. Supporting SOC/non-collinear projected bands requires a separately reviewed future state model.

## Passive fat-band plotting

`plot_fat_band(...)` consumes one explicit `AggregatedBandProjection`.

Example:

```python
figure, ax = plot_fat_band(
    result,
    marker_area_scale=36.0,
    marker="o",
    alpha=0.55,
    show_base_bands=True,
)
```

The renderer uses:

- Block-3 `band_path_coordinates(...)` for x coordinates;
- the associated Block-3 retained band energies for y coordinates;
- the aggregated retained projection weight for marker area.

`marker_area_scale`, marker style, alpha, color, and base-line width are presentation state only. Changing them does not change projection values, scientific digests, band energies, or path state.

Zero retained projection weight produces zero marker area. No artificial visual floor is added.

Discontinuous reciprocal-space path segments remain separate. The renderer does not reconnect bands across segment boundaries, sort crossings, interpolate k-points, smooth bands, infer a gap, infer metallicity, or shift energies implicitly.

If the associated band state has already been explicitly transformed to `E - E_F`, fat-band plotting uses that retained reference exactly. If it remains source-native, the renderer leaves it source-native.

## Provenance and auditability

Projection state retains:

- associated band-state digest and source digest;
- PROCAR source digest;
- exact physical spin channels;
- exact backend-exposed orbital order;
- exact structure-coupled site identity;
- adapter k-point and energy compatibility tolerances;
- producer/backend metadata including current `pymatgen-core` version;
- source k-point weights when available as provenance only.

K-point weights and occupancies are not used to infer electronic character, band filtering, metallicity, or projection normalization.

## Prior art and license boundary

`pymatgen-core` is the existing permissive optional VASP I/O backend.

`romerogroup/pyprocar` is GPLv3. It is reference-only for projected-band/fat-band behavior and UX. CatalysisWorkbench does not copy or adapt PyProcar implementation code and does not add PyProcar as a dependency.

## Explicitly out of scope for Block 4

- SOC/non-collinear vector or spinor projection representation;
- automatic element grouping or orbital-family grouping;
- atom selection from chemistry heuristics;
- spin summation;
- max/percentage/inferred-total/electron-count normalization;
- reconstruction of the raw terminal PROCAR `tot` column omitted by current `pymatgen-core`;
- automatic projection thresholds;
- band sorting/reconnection;
- k-point interpolation or smoothing;
- scissor correction;
- band-gap/direct-gap/metallicity inference;
- symmetry-path generation;
- LOCPOT/work-function processing;
- NEB/barrier processing;
- advanced 3-D volumetric rendering;
- VASP/HPC execution or workflow management.
