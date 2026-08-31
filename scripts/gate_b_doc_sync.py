from __future__ import annotations

from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def sub(path: str, pattern: str, replacement: str, *, flags: int = 0) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"expected exactly one match in {path}: {pattern!r}; got {count}")
    write(path, updated)


sub(
    "README.md",
    r"The active v1\.1 release-candidate development identity is:\n\n```text\n1\.1\.0\.dev0\n```\n\nv1\.1 Blocks 1–6 are complete and merged on `main`\..*?upload to a package registry\.",
    "The active v1.1 final-version candidate identity is:\n\n```text\n1.1.0\n```\n\nv1.1 Blocks 1–6 and Stable 1.1 Gate A are complete and merged on `main`. Gate A was squash-merged as `843df51828d740405aa5365142541ed361e069cc`; post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 all succeeded on that exact commit.\n\nStable 1.1 Gate B now performs mechanical final-version synchronization only: distribution/runtime identity, version-sensitive smoke evidence, and exact artifact expectations are `1.1.0`. Gate B does **not** create `v1.1.0`, publish a GitHub Release, create installers, or upload to a package registry.",
    flags=re.S,
)

sub(
    "CHANGELOG.md",
    r"- v1\.1 Block 6 hardens the ordinary desktop workflow without changing the reviewed scientific semantics or the frozen v1\.0 compatibility surface; the development version remains `1\.1\.0\.dev0`\.\n- Block 6 is merged and post-merge verified\..*?Gate A does not create a v1\.1 tag, GitHub Release, installer, or PyPI/package-registry publication\.",
    "- v1.1 Block 6 hardens the ordinary desktop workflow without changing the reviewed scientific semantics or the frozen v1.0 compatibility surface.\n- Stable 1.1 Gate A is merged and post-merge verified at `843df51828d740405aa5365142541ed361e069cc`; CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 are green on that exact main commit.\n- Gate B synchronizes the release candidate mechanically to `1.1.0`, including distribution/runtime identity, version-sensitive installed-smoke evidence, and exact wheel/sdist expectations. No feature, scientific, dependency, schema, public-API, or runtime-semantic change is introduced.\n- Stable 1.0 Readiness remains an active compatibility gate. Gate B does not create `v1.1.0`, publish a GitHub Release, create installers, or publish to PyPI/package registries.",
    flags=re.S,
)

sub(
    "docs/MASTER_PLAN.md",
    r"## Current checkpoint — v1\.1 release hardening",
    "## Current checkpoint — v1.1 Gate B final-version candidate",
)
sub(
    "docs/MASTER_PLAN.md",
    r"- candidate development version: `1\.1\.0\.dev0`;\n- v1\.1 Blocks 1–6: complete and merged;\n- exact Block-6 squash merge / Gate-A baseline: `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`;\n- Block-6 post-merge CI #851: success;\n- Block-6 post-merge Stable 1\.0 Readiness #113: success;\n- current phase: Stable 1\.1 Gate A — release hardening at unchanged development version\.\n\nGate A adds v1\.1-specific release audit, platform-install, and artifact validation only\. Final `1\.1\.0`, the `v1\.1\.0` tag, GitHub Release publication, installers, and package-registry publication remain later gates\.",
    "- final-version candidate: `1.1.0`;\n- v1.1 Blocks 1–6: complete and merged;\n- Stable 1.1 Gate A squash merge / Gate-B baseline: `843df51828d740405aa5365142541ed361e069cc`;\n- Gate-A post-merge CI #854: success;\n- Gate-A post-merge Stable 1.0 Readiness #116: success;\n- Gate-A post-merge Stable 1.1 Readiness #3: success;\n- current phase: Stable 1.1 Gate B — mechanical final-version candidate synchronization.\n\nGate A release hardening is complete. Gate B changes only release identity/evidence to exact `1.1.0`. The `v1.1.0` tag, GitHub Release publication, installers, and package-registry publication remain later separately authorized gates.",
)
sub(
    "docs/MASTER_PLAN.md",
    r"It was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`; post-merge CI #851 and Stable 1\.0 Readiness #113 succeeded\. Stable 1\.1 Gate A is now the active release-hardening phase\.",
    "It was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`; post-merge CI #851 and Stable 1.0 Readiness #113 succeeded. Stable 1.1 Gate A later squash-merged as `843df51828d740405aa5365142541ed361e069cc` and passed post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3. Gate B is now the active final-version candidate phase.",
)
sub(
    "docs/MASTER_PLAN.md",
    r"- finalize `1\.1\.0`;",
    "- change the final-version identity outside an explicitly authorized release gate;",
)

sub(
    "docs/ROADMAP.md",
    r"- the active v1\.1 release-candidate development identity is `1\.1\.0\.dev0`\.\n- PyPI/package-registry publication has not been performed\.\n- Stable 1\.1 Gate A is in progress; final `1\.1\.0`, the v1\.1 tag, GitHub Release, installers, and any registry publication remain later verified gates\.",
    "- the active v1.1 final-version candidate identity is `1.1.0`.\n- PyPI/package-registry publication has not been performed.\n- Stable 1.1 Gate A is complete and merged; Gate B final-version validation is active. The v1.1 tag, GitHub Release, installers, and any registry publication remain later separately verified gates.",
)
sub(
    "docs/ROADMAP.md",
    r"Block 6 completed the real installed-wheel dogfooding review and was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`\. Post-merge CI #851 and Stable 1\.0 Readiness #113 both succeeded on that exact commit\.\n\nThe active release path is now staged:\n\n1\. \*\*Gate A — release hardening:\*\* retain `1\.1\.0\.dev0`, add Stable 1\.1 exact-wheel audit, Linux/Windows/macOS base \+ desktop install checks, wheel/sdist validation, and release documentation;\n2\. \*\*Gate B — final-version candidate:\*\* synchronize distribution/runtime/gate expectations to exact `1\.1\.0` without feature changes;",
    "Block 6 completed the real installed-wheel dogfooding review and was squash-merged as `c81ee2e1aa8767e1560a14c5f7f4c1209fc4b6f9`. Stable 1.1 Gate A then added the exact-wheel/cross-platform/artifact release evidence and was squash-merged as `843df51828d740405aa5365142541ed361e069cc`; post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 all succeeded on that exact commit.\n\nThe active release path is now staged:\n\n1. **Gate A — release hardening: complete.** `1.1.0.dev0` was retained while Stable 1.1 exact-wheel, Linux/Windows/macOS base + desktop, wheel/sdist, and release-documentation evidence was established;\n2. **Gate B — final-version candidate: active.** Distribution/runtime/gate expectations are synchronized to exact `1.1.0` without feature changes;",
)

sub(
    "docs/DESKTOP.md",
    r"- current development identity: `1\.1\.0\.dev0`;\n- current desktop phase: v1\.1 Block 6 — Dogfooding Hardening & Desktop Cleanup;",
    "- current final-version candidate identity: `1.1.0`;\n- current desktop phase: v1.1 Gate B — final-version candidate;",
)
sub(
    "docs/DESKTOP.md",
    r"The stable v1\.0 compatibility shell remains available while v1\.1 develops a task-first ordinary-user workbench\.",
    "The stable v1.0 compatibility shell remains available while the completed v1.1 task-first workbench proceeds through final release validation.",
)

plan_path = "docs/V1_1_PLAN.md"
plan = read(plan_path)
marker = "## Release maturity — Gate B final-version candidate"
if marker not in plan:
    plan += """

## Release maturity — Gate B final-version candidate

Blocks 1–6 are complete. Stable 1.1 Gate A was squash-merged as `843df51828d740405aa5365142541ed361e069cc` after exact-head CI #853, Stable 1.0 Readiness #115, and Stable 1.1 Readiness #2 succeeded. Post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 then succeeded on that exact main commit.

Gate B starts from `843df51828d740405aa5365142541ed361e069cc` and owns mechanical final-version synchronization only:

- distribution and runtime identity become `1.1.0`;
- ordinary CI and both release-readiness workflows expect exact `1.1.0`;
- version-sensitive installed-smoke/workflow evidence expects `1.1.0`;
- wheel/sdist artifact names use final `1.1.0` naming; and
- release-status documentation identifies `1.1.0` as a final candidate, not an already published release.

Gate B does not change scientific algorithms, task behavior, dependencies, schema, public API, runtime semantics, or desktop compatibility contracts. It does not create `v1.1.0`, publish a GitHub Release, create installers, or publish to PyPI/package registries. Gate B merge remains separately authorized after exact-head CI and formal review.
"""
write(plan_path, plan)

sub(
    "docs/V1_1_RELEASING.md",
    r"- current candidate development version: `1\.1\.0\.dev0`;",
    "- current Gate-B final-version candidate: `1.1.0`;",
)
sub(
    "docs/V1_1_RELEASING.md",
    r"## Gate A — Stable 1\.1 release hardening — in progress",
    "## Gate A — Stable 1.1 release hardening — complete",
)
sub(
    "docs/V1_1_RELEASING.md",
    r"\| final Gate-A head \| pending \|\n\| exact-head ordinary CI \| pending \|\n\| exact-head Stable 1\.0 Readiness \| pending \|\n\| exact-head Stable 1\.1 Readiness \| pending \|\n\| formal release/API/packaging review \| pending \|\n\| unresolved review threads \| pending \|\n\| merge gate \| pending \|\n\| squash merge / Gate-B baseline \| pending \|",
    "| final Gate-A head | `edf7c8554177e6bf25a146085633a047f0744e7a` |\n| exact-head ordinary CI | #853 — success |\n| exact-head Stable 1.0 Readiness | #115 — success |\n| exact-head Stable 1.1 Readiness | #2 — success |\n| formal release/API/packaging review | `5062533798` — clean |\n| unresolved review threads | 0 |\n| merge gate | separately authorized expected-head squash merge |\n| squash merge / Gate-B baseline | `843df51828d740405aa5365142541ed361e069cc` |",
)
sub(
    "docs/V1_1_RELEASING.md",
    r"## Gate B — final-version candidate\n\nGate B may start only from the exact post-merge Gate-A main after all Gate-A push workflows are green\.",
    "## Gate B — final-version candidate — in progress\n\nGate B starts from exact post-merge Gate-A main `843df51828d740405aa5365142541ed361e069cc`. Gate-A post-merge CI #854, Stable 1.0 Readiness #116, and Stable 1.1 Readiness #3 are all green on that exact commit.",
)
releasing_path = "docs/V1_1_RELEASING.md"
releasing = read(releasing_path)
if "### Gate B evidence" not in releasing:
    marker_c = "\n## Gate C — immutable tag\n"
    if marker_c not in releasing:
        raise SystemExit("Gate C marker missing")
    gate_b = """

### Gate B evidence

| Evidence | State |
| --- | --- |
| exact base | `843df51828d740405aa5365142541ed361e069cc` |
| candidate version | `1.1.0` |
| Gate-B branch | `release/v1.1.0-gate-b` |
| final Gate-B head | pending final documentation sync |
| exact-head ordinary CI | pending |
| exact-head Stable 1.0 Readiness | pending |
| exact-head Stable 1.1 Readiness | pending |
| formal release/API/packaging review | pending |
| unresolved review threads | pending |
| merge gate | pending separate authorization |

Ready status never authorizes Gate B merge. Tagging remains Gate C and is not implied by a successful Gate B candidate.
"""
    releasing = releasing.replace(marker_c, gate_b + marker_c, 1)
write(releasing_path, releasing)

sub(
    "docs/V1_1_RELEASE_NOTES_DRAFT.md",
    r"These notes describe the reviewed v1\.1 release-candidate scope\. During Gate A the distribution/runtime identity remains `1\.1\.0\.dev0`; final `1\.1\.0`, the `v1\.1\.0` tag, GitHub Release, installers, and registry publication remain later gates\.",
    "These notes describe the reviewed v1.1 release-candidate scope. Gate A release hardening is complete and Gate B now uses exact distribution/runtime identity `1.1.0`. This is still a final-version candidate: the `v1.1.0` tag, GitHub Release, installers, and registry publication remain later separately verified gates.",
)
sub(
    "docs/V1_1_RELEASE_NOTES_DRAFT.md",
    r"Gate A retains `1\.1\.0\.dev0` while proving release readiness\. Gate B will separately synchronize the exact reviewed candidate to `1\.1\.0`\. Tagging, GitHub Release publication, installers, and package-registry publication occur only after their own verification gates\.",
    "Gate A proved release readiness at `1.1.0.dev0` and was merged as `843df51828d740405aa5365142541ed361e069cc`. Gate B synchronizes the exact candidate to `1.1.0` and must pass ordinary CI plus Stable 1.0 and Stable 1.1 readiness before review/merge. Tagging, GitHub Release publication, installers, and package-registry publication occur only after their own verification gates.",
)

print("Gate B release-status documentation synchronized")