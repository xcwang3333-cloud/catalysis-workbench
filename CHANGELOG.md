# Changelog

All notable changes to CatalysisWorkbench are recorded here.

## [0.1.0] - unreleased

The first usable release establishes the common one-dimensional catalysis-data workflow and publication rendering foundation.

### Added

- Immutable-style `Axis`, `Series`, and ordered `Dataset` scientific data models with stable non-display Series keys and deterministic metadata handling.
- Excel, CSV, TXT/TSV/DAT tabular readers with explicit column selection, conservative unit inference, source provenance, and multi-series handling.
- Shared XY processing primitives for crop, offset, normalization, Savitzky-Golay smoothing, interpolation, integration, explicit baseline subtraction, and Dataset mapping.
- LSV/polarization processing with explicit RHE conversion, signed iR correction, geometric current-density normalization, provenance, and publication plotting.
- XRD validation/processing, multi-pattern overlay/stacking, normalization compatibility, peak annotations, reference sticks, and publication plotting.
- Raman validation/processing, multi-spectrum overlay/stacking, direct-window band measurements, explicit ID/IG-style ratios, provenance, and publication plotting.
- Serializable `FigureSpec`, physical figure/axes geometry, editable presets, per-Series style overrides, annotations, deterministic rendering, and exact-size PNG/SVG/PDF export.
- Compact end-to-end LSV, XRD, and Raman examples plus installed-wheel public-API smoke coverage.

### Scientific/API principles

- Scientific transformations are non-mutating and preserve deterministic provenance.
- Units, electrochemical references, normalization bases, branch/sign behavior, and analysis windows are explicit rather than silently inferred when that would change scientific meaning.
- Visualization is separated from scientific processing; domain plot adapters reuse the shared renderer instead of creating independent Matplotlib stacks.
- v0.1 intentionally remains focused on one-dimensional XY workflows. CLI/GUI, N-D operando data, advanced electrochemistry, extended characterization, and DFT post-processing remain roadmap work.

### Release gate

The source tree remains versioned `0.1.0.dev0` until Issue #18 is reviewed and all release-hardening checks pass. The final version bump/tag/release is a separate explicit action documented in `docs/RELEASING.md`.
