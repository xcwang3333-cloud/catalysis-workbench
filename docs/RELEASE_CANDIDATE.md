# v0.1.0 release candidate

Date: 2026-08-23

This branch is the final version gate for CatalysisWorkbench v0.1.0. It contains no new scientific algorithms.

## Candidate version

- Distribution metadata: `0.1.0`
- Runtime `catalysis_workbench.__version__`: `0.1.0`
- Intended tag after final authorization: `v0.1.0`

## Required validation before tag

- Ruff passes.
- Full pytest suite passes.
- The wheel builds with filename/version `0.1.0`.
- Fresh-wheel installation passes `pip check`.
- Installed distribution metadata equals runtime `__version__` exactly.
- All six documented package-level `__all__` surfaces resolve from the installed wheel.
- Installed LSV/XRD/Raman smoke workflows pass.
- All three documented examples execute against the installed wheel.
- Formal release/API/packaging review reports no blocker.

The tag is deliberately not created on this branch. The reviewed candidate must first be merged to `main`, rechecked there, and then receive explicit final tag authorization.
