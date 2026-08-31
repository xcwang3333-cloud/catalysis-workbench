# Code signing policy

## Purpose

This policy defines the minimum code-signing and publication controls for native
Windows installer artifacts published by CatalysisWorkbench.

The stable product source for the v1.1.0 Windows installer is immutable:

`v1.1.0 -> 80da57c65bb70f599c1e068f6fe71a1551eaa856`

Packaging infrastructure may evolve on `main`, but it must never silently replace
or reinterpret that product source.

## Trust model

Release signing must use a publicly trusted Authenticode code-signing identity or
an equivalent managed signing service whose certificate chain is trusted by
supported Windows systems. Self-signed certificates are test-only and are never
acceptable for public release artifacts.

Private signing keys must not be committed to this repository, embedded in build
artifacts, printed to Actions logs, or stored as an exportable plaintext secret.
Prefer HSM-backed or managed remote signing. Where a CI integration is used, its
permissions must be limited to the minimum signing identity and release policy.

Provider choice is deliberately separated from this repository-level safety
contract. Candidate integrations include open-source signing services with
trusted-build/origin verification and managed public-trust signing services.
Provider enrollment and credentials are external prerequisites, not implicit
repository state.

## Cryptographic requirements

Public release artifacts must use Authenticode with SHA-256 or stronger. A
trusted RFC3161 timestamp using SHA-256 or stronger is required so the signature
can remain verifiable after certificate expiry.

A publication verifier must fail closed unless all required signatures report
`Valid` under Windows Authenticode verification.

## Required signed surfaces

For the first Windows x64 installer, at minimum these first-party executable
surfaces must be signed by the approved publisher identity before publication:

1. `CatalysisWorkbench-1.1.0-windows-x64-setup.exe`;
2. installed `CatalysisWorkbench.exe`; and
3. the Inno Setup-generated uninstaller (`unins*.exe`).

Signing only the outer Setup executable is insufficient. A publication workflow
must install the final signed installer into an isolated directory and verify the
installed application and uninstaller signatures before running the installed
smoke and uninstall checks.

Third-party binaries keep their upstream licensing and signature identities; they
must not be re-signed as if they were first-party code unless the upstream license
and publication policy explicitly permit it.

## Provenance and hashing

The final signed artifact set must record, separately:

- product version `1.1.0`;
- immutable product source commit
  `80da57c65bb70f599c1e068f6fe71a1551eaa856`;
- exact packaging-infrastructure commit used to build the candidate;
- signing provider/profile identifier without exposing credentials;
- signer certificate subject and thumbprint;
- timestamp certificate subject and thumbprint when exposed by the platform;
- SHA-256 of the final signed installer; and
- SHA-256 of the dependency constraints and resolved-requirements evidence.

Hashes from an unsigned readiness artifact are not final publication hashes.
Any byte-level change after signing invalidates the publication evidence and
requires a fresh verification cycle.

## Release mutation boundary

Code signing and GitHub Release mutation are separate gates.

A successful signing/verification run may produce a signed publication candidate,
but it does not authorize attachment to the existing `v1.1.0` GitHub Release.
Release asset upload requires a separate explicit authorization after exact
artifact identity, signatures, timestamp, hashes, provenance, licensing notices,
and install/uninstall evidence have been reviewed.

The `v1.1.0` tag must never be moved, replaced, or recreated as part of installer
publication. PyPI/package-registry publication is a different release operation
and remains independently gated.

## SmartScreen expectations

A valid signature establishes publisher identity but does not guarantee that a
new binary has already accumulated Microsoft Defender SmartScreen reputation.
Release notes and support guidance must not promise that first-download warnings
will be absent. Consistent signing identity should be retained across future
installer releases whenever practical.

## Compliance boundary

The installer bundles the project under BSD-3-Clause together with third-party
runtime components. Publication requires a reviewed `THIRD_PARTY_NOTICES.txt` and
resolved dependency evidence. In particular, PySide6/Qt redistribution remains
subject to its applicable LGPLv3/GPLv3 or commercial terms.

If the build is performed in a commercial context, current Inno Setup commercial
license expectations must also be checked before production publication.
