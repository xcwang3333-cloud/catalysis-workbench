# Bader result parsing and explicit charge accounting

CatalysisWorkbench v0.6 block 4 reads already-generated standard Henkelman-style `ACF.dat` results. It does not perform Bader partitioning and does not launch, install, bundle, or discover an external Bader executable.

## Scope and producer boundary

The canonical Henkelman Bader program partitions a supplied electron-density grid and writes atom-resolved results such as `ACF.dat`. CatalysisWorkbench starts **after** that external calculation has finished.

The initial reader targets the standard ACF atom table:

```text
# X Y Z CHARGE MIN DIST ATOMIC VOL
1 ...
2 ...
...
VACUUM CHARGE: ...
VACUUM VOLUME: ...
NUMBER OF ELECTRONS: ...
```

For this standard electron-density result, CatalysisWorkbench interprets the producer `CHARGE` column as a raw integrated **electron population** and exposes it as `bader_electrons`. The public API deliberately avoids an ambiguous raw or derived field named only `charge`.

Standard result-level footer diagnostics are retained when present:

- `vacuum_charge_electrons`;
- `vacuum_volume_angstrom3`;
- `number_of_electrons`.

Historical ACF outputs that omit one or more footer diagnostics can still be represented; missing values remain `None` and are never inferred.

## Source atom indices and site mapping

`ACF.dat` atom indices are retained as `source_atom_index` and are **1-based**, matching the external file. The minimum supported parser requires the standard ordered sequence `1..N`; duplicate, skipped, zero, negative, or reordered source indices fail rather than being repaired.

An ACF result can remain completely unmapped to an `AtomicStructure`. In that state, source index and Cartesian position are still authoritative raw result fields.

Optional structure mapping is intentionally strict. When an `AtomicStructure` is supplied:

1. the caller must also supply a positive finite `position_tolerance_angstrom`;
2. ACF atom count must equal structure site count;
3. row `i` is compared directly with structure site `i` in Cartesian angstrom coordinates;
4. every coordinate difference must lie within the caller-supplied tolerance;
5. the mapped row retains the 0-based CatalysisWorkbench `site_index`, deterministic `site_key`, structure digest, and tolerance.

The reader does **not** sort atoms, perform nearest-neighbor assignment, apply periodic-image corrections, wrap coordinates, translate/align structures, or infer elements. If the ACF row order/positions do not directly match the supplied structure, mapping fails closed.

The original 1-based `source_atom_index` is retained even after mapping, so source-file identity and CatalysisWorkbench site identity cannot be confused.

## Raw result contract

`BaderSiteResult` retains:

- `source_atom_index`;
- immutable Cartesian position in angstrom;
- `bader_electrons`;
- `min_distance_angstrom`;
- `atomic_volume_angstrom3`;
- optional mapped `site_index` and `site_key`;
- deterministic site digest.

`BaderResult` retains the ordered immutable site tuple, optional footer diagnostics, mapping provenance when present, source format/path/ID, and deterministic scientific digest.

Scientific/result digests include the parsed numerical state and mapping state. Descriptive `source_path` and caller `source_id` remain provenance but are excluded from the scientific digest, so byte-identical ACF scientific content at two file paths does not become a different scientific result merely because it was renamed.

For the standard electron-density scope, raw electron populations and minimum distances must be non-negative and atomic volumes must be positive. Non-finite values fail explicitly.

## Explicit charge accounting

Raw Bader electron population is **not** itself a partial atomic charge. Charge accounting is a separate operation and requires caller-supplied reference electron counts.

For each site:

```text
electron_transfer = N_Bader - N_reference
partial_charge    = N_reference - N_Bader
```

Therefore:

- positive `electron_transfer` means electron gain / anionic direction;
- negative `electron_transfer` means electron loss / cationic direction;
- positive `partial_charge` means electron deficiency / cationic direction;
- negative `partial_charge` means electron excess / anionic direction;
- `partial_charge = -electron_transfer` by construction.

`account_bader_charges()` requires exactly one finite non-negative `reference_electrons` value per ACF row and a nonblank `reference_id`. The reference ID records caller-visible provenance such as a manually supplied pseudopotential-valence convention.

CatalysisWorkbench does not infer reference electrons from:

- element or atomic number;
- oxidation state;
- POTCAR/POTCAR-like files;
- pseudopotential family;
- display labels;
- Bader output itself.

`BaderChargeSiteResult` retains the raw Bader population, caller reference, both explicitly signed derived quantities, source-site digest, Cartesian/source identity and any mapped site identity. `BaderChargeResult` retains the source raw-result digest and the caller's `reference_id`.

## Reporting

`bader_result_frame()` returns a detached one-row-per-site table of raw ACF state and mapping/source provenance.

`bader_charge_frame()` returns a detached one-row-per-site table containing the unambiguous fields:

- `bader_electrons`;
- `reference_electrons`;
- `electron_transfer`;
- `partial_charge`.

Neither reporting table contains a derived column named simply `charge`. Editing a returned DataFrame cannot mutate retained result objects.

## Prior art and licensing

Implementation-time review in Issue #162 considered:

- the Henkelman-group Bader v1.05 producer and ACF format. Its current source is GPLv3-or-later. It remains external producer/reference only; no source is copied and no executable is bundled or launched;
- current pymatgen `pymatgen.command_line.bader_caller.BaderAnalysis`. It wraps a compiled Bader executable and distinguishes raw Bader population from charge transfer and partial charge. Its sign conventions are useful prior art, but the wrapper is not a dependency because CatalysisWorkbench only parses existing results and must not launch the external program or automatically obtain POTCAR ZVAL;
- pyBader, an MIT-licensed Python implementation of the full grid partitioning algorithm. It is reference-only because adding a partitioner is outside this block and would add unnecessary runtime scope/dependencies.

No new dependency is required for `ACF.dat` parsing or explicit arithmetic.

## Explicit exclusions

Block 4 does not provide:

- zero-flux partition calculation;
- Henkelman Bader or pyBader execution;
- executable discovery or installation;
- CHGCAR/AECCAR summation or reference-density construction;
- POTCAR parsing or automatic valence/reference lookup;
- oxidation-state assignment;
- automatic chemistry interpretation;
- nearest-neighbor or periodic-image site remapping;
- `BCF.dat` / `AtomVolumes.dat` basin processing;
- plotting;
- COHP/ICOHP analysis, CHE/free energy, or charge-density-difference processing.

Those responsibilities either remain external or belong to later frozen v0.6/v0.7 blocks.
