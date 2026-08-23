# Releasing CatalysisWorkbench v0.1

Versioning and tagging are deliberately separated from feature implementation so a green scientific PR cannot accidentally become a release merely because it was merged.

## Release-hardening gate

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

This gate was completed by Issue #18 / PR #29 before the final version candidate was created.

## Final version gate

The release candidate changes `[project].version` and `catalysis_workbench.__version__` together from `0.1.0.dev0` to `0.1.0`. Before tagging, it must then pass the same release checks again with the final version embedded in the built wheel:

1. Ruff and the complete pytest suite pass.
2. The package builds a `catalysis_workbench-0.1.0-*.whl` artifact.
3. A fresh virtual environment installs that wheel and `python -m pip check` succeeds.
4. Installed distribution metadata and runtime `catalysis_workbench.__version__` both report exactly `0.1.0`.
5. All documented public `__all__` surfaces and the representative LSV/XRD/Raman installed workflows pass.
6. The three documented examples execute against the installed final-version wheel.
7. The version-gate PR receives formal review with no unresolved release/API/packaging blockers.
8. The reviewed version-gate PR is merged to `main`.
9. The `main` commit intended for release is rechecked to report `0.1.0` before a tag is created.
10. Create `v0.1.0` only after explicit final release authorization.

## Tag and distribution boundary

The `v0.1.0` tag must point to the reviewed `main` commit that already reports version `0.1.0`. Tag creation is intentionally a separate operation from the version bump/merge so the reviewed commit can be verified first.

Package-registry publication is not implied by creating the Git tag. Attach or publish artifacts only if a package-registry/release-distribution workflow, licensing, credentials, artifact provenance/signing, and intended distribution policy have been explicitly configured and reviewed.

## What not to do

- Do not tag a commit that reports `0.1.0.dev0` as the final release.
- Do not create `v0.1.0` before the final-version wheel has passed the installed smoke gate.
- Do not make a version bump in the same round as unresolved scientific or packaging changes.
- Do not infer that a successful editable install proves the wheel is installable; the installed-wheel smoke gate exists specifically to catch packaging/public-import problems.
- Do not accept a version check that only matches a prefix; distribution metadata and runtime `__version__` must agree exactly.
- Do not publish to a package registry until credentials, artifact signing/provenance, licensing, and the intended distribution policy have been explicitly configured.
