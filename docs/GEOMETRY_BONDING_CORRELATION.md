# Geometry–bonding correlation

CatalysisWorkbench v0.6 block 6 represents explicitly paired geometry and descriptor values. The layer is descriptive: it records which reviewed scientific values were paired and why. It does not infer atom/bond correspondence, fit structures, rank bonds, or claim causation.

## Explicit pairing boundary

A `CorrelationPoint` contains one finite x/y pair together with:

- a stable point key;
- exact x source key and source digest;
- exact y source key and source digest;
- a stable mapping key;
- caller-visible mapping provenance explaining why the two values correspond;
- optional immutable scientific metadata;
- an optional display/source label.

There is no API that accepts two unlabeled arrays and silently zips them by position. Row order, label similarity, nearest-neighbor distance, species identity, or automatic structure fitting is never treated as proof that two values correspond.

For cross-structure workflows, callers must use already-reviewed stable identities such as explicit `SiteMapping` state or another separately reviewed mapping procedure and record that provenance in the correlation point.

## Dataset semantics

`CorrelationDataset` retains:

- an explicit x definition and unit;
- an explicit y definition and unit;
- dataset-level provenance ID;
- ordered retained `CorrelationPoint` records;
- separately retained caller-declared `CorrelationExclusion` records;
- a deterministic scientific digest.

Definitions and units are scientific state. A plot label is not allowed to redefine them downstream.

Display-only `source_label` fields are excluded from the scientific digest. Changing a reporting label therefore does not change numerical/scientific identity, while changing values, source digests, mapping provenance, metadata, definitions, units, or retained/excluded records does.

## Missing and excluded candidates

Required retained points fail closed when x or y is missing, non-finite, or lacks source/mapping identity. CatalysisWorkbench does not silently drop such points.

If a caller intentionally excludes a candidate, `CorrelationExclusion` keeps it outside the numeric point collection and requires:

- a stable exclusion key;
- mapping key;
- caller-supplied reason;
- at least one x or y source key;
- optional immutable metadata.

`correlation_points_frame()` and `correlation_exclusions_frame()` are separate detached tables, so excluded candidates cannot silently enter statistical or plotting arrays.

## ICOHP bond length versus ICOHP(E_F)

`icohp_length_correlation()` is the narrow convenience path for the canonical block-6 example.

It consumes reviewed block-5 `ICOHPResult` / `ICOHPBondSummary` state and pairs, for each exact selected bond:

- x: retained LOBSTER bond length, unit `angstrom`;
- y: source-sign ICOHP(E_F), unit `eV`;
- mapping identity: the same reviewed `ICOHPBondSummary` bond key.

The caller must explicitly provide the physical spin contribution(s). For spin-polarized summaries, `("up", "down")` invokes the already-reviewed explicit block-5 spin sum; a single requested spin retains only that physical channel. There is no implicit spin sum.

The sign is never inverted. A conventional publication axis labelled `-ICOHP` would be a separately explicit display transform and does not overwrite this source-sign dataset.

The source `number_of_bonds` value is retained in point metadata as multiplicity provenance. It is not used to multiply or divide the ICOHP value automatically.

## Generic geometry and charge use cases

Other frozen block-6 use cases are represented through caller-created `CorrelationPoint` state rather than specialized hidden joins. Examples include:

- reviewed `SiteAngleResult.angle_degrees` versus a caller-selected bonding descriptor;
- `CoordinationResult.coordination_number` versus an explicitly mapped Bader `partial_charge` or `electron_transfer`;
- another explicit local-geometry metric versus a reviewed bonding descriptor.

The caller records the exact source keys/digests and the mapping provenance. CatalysisWorkbench does not invent a universal mapping between VASP geometry sites, Bader rows, and LOBSTER bond labels because these may come from different structures/calculations or periodic images.

## Statistics and interpretation

The minimum block-6 implementation performs no automatic Pearson/Spearman correlation, regression, trend line, p-value, threshold, ranking, or significance test.

SciPy is already available if a later reviewed extension adds explicit statistics, but any such result must retain method, sample count, undefined/constant-input state, and must not be described as causal evidence.

A visually strong or numerically large correlation does not by itself establish a physical mechanism.

## Prior-art boundary

Current pymatgen `StructureMatcher` can reduce cells, scale structures, search lattice/site tolerances, and perform other nontrivial matching operations. That behavior is intentionally not used here because block 6 requires caller-visible mappings rather than hidden atom correspondence.

Matminer provides broad materials featurization/data-mining workflows and DataFrame-oriented analysis, but adding that dependency would exceed this narrow explicit-pairing layer. No new runtime dependency is introduced.

## Explicit exclusions

Block 6 does not perform:

- automatic structure/site/bond matching;
- `StructureMatcher`-based fitting;
- nearest-neighbor or label-based pairing;
- hidden minimum-image replacement or geometry recomputation;
- automatic bond ranking or strongest-bond filtering;
- cation/anion or chemistry inference;
- automatic statistics, regression, or significance testing;
- causal interpretation;
- CHE/free-energy thermodynamics;
- free-energy-diagram construction;
- charge-density-difference analysis.

The next scientific block is CHE/free-energy thermodynamics after block-6 completion state is merged and reverified.
