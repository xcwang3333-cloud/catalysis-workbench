# Releasing CatalysisWorkbench v0.1

The repository remains at `0.1.0.dev0` until the v0.1 release-hardening pull request has passed review. Versioning and tagging are deliberately separate from feature implementation so a green scientific PR cannot accidentally become a release merely because it was merged.

## Pre-release gate

Before changing the version to `0.1.0`, all of the following must be true on the reviewed release-hardening branch or merged `main`:

1. Ruff passes across the repository.
2. The complete pytest suite passes.
3. The package builds as a wheel from `pyproject.toml`.
4. A fresh virtual environment installs that wheel and `python -m pip check` reports no dependency conflicts.
5. `tests/installed_api_smoke.py` runs successfully from the installed wheel, proves imports do not resolve from the repository `src/` tree, verifies distribution metadata matches `catalysis_workbench.__version__`, and resolves every name in the six documented package-level `__all__` public surfaces.
6. README quickstart code and the three compact examples remain executable against documented public imports.
7. Running the examples does not dirty the source checkout with generated figures.
8. `CHANGELOG.md` reflects the final v0.1 feature set and known scope boundaries.
9. The release-hardening PR has no unresolved scientific/API/packaging blockers.

## Final version step

Only after the gate is approved:

1. Change `[project].version` in `pyproject.toml` from `0.1.0.dev0` to `0.1.0`.
2. Change `catalysis_workbench.__version__` to `0.1.0` in the same release commit/PR.
3. Re-run the full CI and installed-wheel smoke job.
4. Confirm the built wheel reports `0.1.0` both through distribution metadata and `catalysis_workbench.__version__`; the installed smoke program enforces their equality.
5. Create an annotated or GitHub release tag `v0.1.0` from the reviewed `main` commit.
6. Attach/publish release artifacts only if a package registry/release-distribution workflow has been explicitly configured and reviewed.

## What not to do

- Do not tag a commit that still reports `0.1.0.dev0` as the final release.
- Do not make a version bump in the same round as unresolved scientific or packaging changes.
- Do not infer that a successful editable install proves the wheel is installable; the installed-wheel smoke gate exists specifically to catch packaging/public-import problems.
- Do not accept a version check that only matches a prefix; distribution metadata and runtime `__version__` must agree exactly.
- Do not publish to a package registry until credentials, artifact signing/provenance, licensing, and the intended distribution policy have been explicitly configured.
