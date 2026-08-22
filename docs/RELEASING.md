# Releasing CatalysisWorkbench v0.1

The repository remains at `0.1.0.dev0` until the v0.1 release-hardening pull request has passed review. Versioning and tagging are deliberately separate from feature implementation so a green scientific PR cannot accidentally become a release merely because it was merged.

## Pre-release gate

Before changing the version to `0.1.0`, all of the following must be true on the reviewed release-hardening branch or merged `main`:

1. Ruff passes across the repository.
2. The complete pytest suite passes.
3. The package builds as a wheel from `pyproject.toml`.
4. A fresh virtual environment installs that wheel and runs `tests/installed_api_smoke.py` successfully.
5. README quickstart code and the three compact examples remain executable against documented public imports.
6. `CHANGELOG.md` reflects the final v0.1 feature set and known scope boundaries.
7. The release-hardening PR has no unresolved scientific/API/packaging blockers.

## Final version step

Only after the gate is approved:

1. Change `[project].version` in `pyproject.toml` from `0.1.0.dev0` to `0.1.0`.
2. Change `catalysis_workbench.__version__` to `0.1.0` in the same release commit/PR.
3. Re-run the full CI and installed-wheel smoke job.
4. Confirm `python -c "import catalysis_workbench; print(catalysis_workbench.__version__)"` reports `0.1.0` from the built wheel.
5. Create an annotated or GitHub release tag `v0.1.0` from the reviewed `main` commit.
6. Attach/publish release artifacts only if a package registry/release-distribution workflow has been explicitly configured and reviewed.

## What not to do

- Do not tag a commit that still reports `0.1.0.dev0` as the final release.
- Do not make a version bump in the same round as unresolved scientific or packaging changes.
- Do not infer that a successful editable install proves the wheel is installable; the installed-wheel smoke gate exists specifically to catch packaging/public-import problems.
- Do not publish to a package registry until credentials, artifact signing/provenance, and the intended distribution policy have been explicitly configured.
