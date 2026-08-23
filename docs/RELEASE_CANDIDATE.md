# v0.1.0 release validation record

Date: 2026-08-23

This document records the final version gate for CatalysisWorkbench v0.1.0. It contains no new scientific algorithms and is intentionally written so the same snapshot remains accurate before and after the release tag is created.

## Final version

- Distribution metadata: `0.1.0`
- Runtime `catalysis_workbench.__version__`: `0.1.0`
- Release tag name: `v0.1.0`

## Required validation

- Ruff passes.
- Full pytest suite passes.
- The wheel builds with filename/version `0.1.0`.
- Fresh-wheel installation passes `pip check`.
- Installed distribution metadata equals runtime `__version__` exactly.
- All six documented package-level `__all__` surfaces resolve from the installed wheel.
- Installed LSV/XRD/Raman smoke workflows pass.
- All three documented examples execute against the installed wheel.
- Formal release/API/packaging review reports no blocker.

## Tag policy

A `v0.1.0` tag may point only to the reviewed `main` commit that already reports version `0.1.0`, after the final-version checks pass and explicit release authorization is given. Tag creation is a separate operation from the version-gate PR merge.
