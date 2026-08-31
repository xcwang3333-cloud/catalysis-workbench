# CatalysisWorkbench v1.1 Windows installer — Gates D/E

## Current status

`v1.1.0` is already an immutable tagged and published GitHub release:

`v1.1.0 -> 80da57c65bb70f599c1e068f6fe71a1551eaa856`

Gate D installer-readiness infrastructure is merged on `main`. It proved the
exact-tag Windows x64 frozen build, notices/provenance generation, Inno Setup
packaging, silent install, installed desktop smoke, silent uninstall, and
artifact hashing. Gate D intentionally produced an **unsigned readiness build**
and did not attach it to the GitHub Release.

Gate E is the later **installer publication gate**. Gate E must not change the
v1.1.0 product source or move/recreate the tag. It adds publication-time
signature/compliance verification around the already frozen product source.

## Frozen product scope

The first native installer target remains Windows x64 only.

- Product source: exact immutable `v1.1.0` tag.
- Product release commit: `80da57c65bb70f599c1e068f6fe71a1551eaa856`.
- Python build interpreter: CPython 3.11 x64.
- Freezer: PyInstaller 6.22.2.
- Freeze mode: `onedir`; `onefile` is intentionally not used.
- Installer compiler: Inno Setup 6.7.3 for the reviewed v1.1.0 build recipe.
- Installed location: per-user under local application data.
- Python extras: base + `[desktop]`.
- Excluded extras: `[structure]`, `[volumetric3d]`.

PyInstaller and Inno Setup remain build/distribution tooling and are not package
runtime dependencies.

## Exact-source and exact-infrastructure contract

Installer workflows must treat product source and packaging infrastructure as two
separate provenance identities:

1. product source is always immutable `v1.1.0` at
   `80da57c65bb70f599c1e068f6fe71a1551eaa856`;
2. packaging/signing infrastructure is the exact reviewed branch or `main`
   commit used for the build/signing operation.

No Gate-D or Gate-E infrastructure commit may become v1.1.0 product input.
Workflows fail closed if either identity drifts.

## Reproducible dependency resolution

The reviewed Windows x64 v1.1.0 dependency resolution is committed as:

`packaging/windows/constraints-v1.1.0-windows-x64.txt`

Installer builds install immutable `v1.1.0[desktop]` and PyInstaller through that
constraints file and require `pip check` before freezing. Build provenance
records the constraints SHA-256 and the actual sorted resolved-requirements
SHA-256 separately.

This lock is specific to the standalone Windows x64 v1.1.0 build. It does not
change public wheel/sdist dependency declarations.

## Gate D readiness evidence

A passing Windows Installer Readiness run proves:

1. exact infrastructure-head and release-tag/SHA/version verification;
2. constrained dependency installation and `pip check`;
3. clean PyInstaller `onedir` build;
4. frozen offscreen task-first desktop construction;
5. third-party license/notice inventory generation;
6. per-user Inno Setup installer build;
7. silent install into an isolated test directory;
8. installed executable offscreen smoke;
9. silent uninstall;
10. provenance and SHA-256 generation; and
11. upload to GitHub Actions artifacts only.

The expected installer filename is:

`CatalysisWorkbench-1.1.0-windows-x64-setup.exe`

Gate D evidence is necessary but is not public-distribution authorization.

## Gate E code-signing contract

The repository-level policy is defined in
[`CODE_SIGNING_POLICY.md`](CODE_SIGNING_POLICY.md).

The publication gate is provider-neutral. External enrollment may use an approved
open-source signing service, a managed public-trust signing service, or another
reviewed CA/HSM-backed workflow. Signing credentials and private keys must never
be committed to this repository.

At minimum, publication requires trusted Authenticode signatures on:

- the final Setup EXE;
- installed `CatalysisWorkbench.exe`; and
- the generated Inno Setup uninstaller (`unins*.exe`).

Signing only the outer Setup executable is not sufficient.

SHA-256 or stronger is required for code signing, and a trusted RFC3161 timestamp
using SHA-256 or stronger is required. The fail-closed verifier lives at:

`packaging/windows/verify_signed_artifact.ps1`

The `Windows Installer Publication Readiness` workflow exercises that verifier on
a trusted Windows binary and proves that unsigned and wrong-publisher inputs are
rejected. It deliberately has `contents: read` only and cannot publish a Release
asset.

## Final signed-candidate verification

After a signing provider is configured, the signed publication candidate must be
verified again from bytes that will actually be released:

1. exact filename and exact immutable release-source identity;
2. trusted Authenticode signer identity;
3. RFC3161 timestamp presence;
4. final signed-installer SHA-256;
5. isolated silent install;
6. installed application signature verification;
7. installed uninstaller signature verification;
8. installed offscreen desktop smoke;
9. silent uninstall;
10. final signing/provider/certificate provenance; and
11. final third-party notice/compliance review.

Any byte-level change after signing invalidates the evidence and requires a fresh
verification cycle.

## Licensing and redistribution review

Bundling is materially different from the wheel + optional-extra model. The
artifact must retain the project BSD-3-Clause license, third-party notice
inventory, dependency evidence, and build/signing provenance.

PySide6/Qt and all other bundled dependencies remain subject to their applicable
publication-time license obligations. The notice inventory is evidence, not legal
advice. Where the build is used commercially, current Inno Setup commercial
license expectations must also be checked before production publication.

## SmartScreen expectation

A valid public-trust signature establishes publisher identity but does not promise
that a newly released file has already accumulated Microsoft Defender SmartScreen
reputation. Release documentation must not claim that first-download warnings are
guaranteed to be absent.

## Final publication authorization boundary

Successful signing and verification still do **not** authorize GitHub Release
mutation.

Before a signed installer is attached to the existing `v1.1.0` Release, a final
review must identify the exact signed file hash, signer/timestamp evidence,
provenance, notices, and install/uninstall results. Asset attachment then requires
a separate explicit authorization.

Gate E must never:

- move, replace, or recreate `v1.1.0`;
- silently overwrite an existing Release asset;
- publish an unsigned or self-signed installer; or
- publish to PyPI/package registries as a side effect.
