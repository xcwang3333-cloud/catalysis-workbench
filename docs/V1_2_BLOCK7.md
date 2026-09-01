# v1.2 Block 7 — Theme / Responsive / Accessibility / Dogfooding

## Scope

Block 7 hardens the completed v1.2 presentation architecture without adding scientific capability, a second state model, or a release/publication path.

The retained product journey remains:

```text
Home
  -> Data Intake & Mapping
  -> Data & Analysis
  -> Figure
  -> Export
```

The scientific/session/export contracts established through Stable v1.1 and v1.2 Blocks 1–6 remain authoritative.

## Theme hardening

The desktop product exposes a user-visible `View > Theme` choice for:

- System;
- Light;
- Dark.

The preference remains desktop-only QSettings state. Theme changes must not dirty an analysis, alter `AnalysisDocument`, `FigureDraft`, `FigureSpec`, scientific arrays, workflow/provenance identities, Figure Package content, or package SHA semantics.

Block 7 also closes a dark-theme contrast defect in the presentation layer. The existing dark accent `#7aa2ff` with white foreground is approximately 2.49:1. The hardened dark primary control uses the existing dark window token as foreground, producing approximately 7.01:1 while retaining the existing accent background. Light primary controls retain the existing white foreground.

System-theme changes are re-resolved at runtime when Qt reports an operating-system color-scheme change.

## Responsive decision

Block 7 does **not** lower the inherited Stable v1.1 `>=1200x760` main-window minimum.

The responsive target is instead hardened inside that compatibility envelope:

- 1920x1080: wide reference layout;
- 1440x900: normal expanded navigation;
- 1366x768: normal expanded navigation;
- 1280x760: automatic compact navigation;
- 1200x760: automatic compact navigation at the inherited minimum.

The v1.2 product path therefore uses a 1320 logical-pixel automatic sidebar breakpoint while preserving the existing user collapse preference. This is presentation-only and remains outside project/scientific identity.

## Accessibility and keyboard review

Block 7 adds product-shell accessibility metadata and visible focus treatment without changing scientific behavior:

- accessible names/descriptions for the application shell, primary navigation, command bar, state/status surface, and core shell buttons;
- explicit strong keyboard focus for shell navigation/command controls;
- visible semantic focus rings for navigation, command buttons, primary/secondary/tertiary actions, key editors, lists, and tables;
- `Ctrl+1` Home;
- `Ctrl+2` Data & Analysis;
- `Ctrl+3` Figure;
- `Ctrl+4` Export;
- `Ctrl+Shift+B` collapse/expand primary navigation;
- normal menu keyboard access for System / Light / Dark theme selection.

Disabled Figure/Export prerequisites remain authoritative; keyboard routing cannot bypass scientific or export gates.

## High-DPI boundary

Qt 6 remains responsible for per-screen high-DPI scaling. Block 7 does not introduce fixed physical-pixel transforms, rasterized application fonts, or a separate DPI preference. Validation checks positive logical DPI/device-pixel-ratio information and ensures the v1.2 shell remains operable across the reviewed logical window sizes.

Publication rendering remains controlled only by FigureSpec/renderer semantics; application theme and high-DPI presentation must not alter publication output.

## Dogfooding

The fresh-wheel Block-7 desktop smoke exercises the completed v1.2 product path for:

1. Generic XY;
2. LSV / Polarization;
3. FE & Partial Current.

The journeys validate Data & Analysis -> Figure -> Export gates while theme changes and responsive shell states remain presentation-only. Existing cumulative Stable v1.0/v1.1 and v1.2 Block 1–6 smokes remain active before the Block-7 smoke.

## Architecture boundary

Block 7 does not change:

- `AnalysisSession`, evaluator behavior, task IDs, processing formulas, scientific arrays, or analysis identities;
- `SourceSpec`, `TabularMappingSpec`, `DataSeriesSpec`, parser/materialization semantics, or source ownership;
- `FigureDraft`, `FigureSpec`, renderer behavior, stale/refresh semantics, or display-range/scientific-data separation;
- Figure Package writer behavior, manifest/source-data rules, deterministic package identity, or export prerequisites;
- workspace/project persistence, concurrency/rollback behavior, recent-project scientific identity, or schema version;
- legacy v1.0 `create_desktop()` behavior;
- runtime/distribution version `1.1.0` during v1.2 development;
- the Stable v1.1 `>=1200x760` minimum-window contract.

Signing-provider enrollment, certificates/private keys, Authenticode/SmartScreen work, signed candidates, installer publication, Release assets, tag mutation, and PyPI/package-registry publication remain outside Block 7.

## Open-source architecture references

- napari's theme model/theme sample is used as a reference for semantic theme roles and reviewing common widget states rather than applying ad-hoc page colors.
- napari's figure-export examples reinforce keeping application theme separate from exported scientific/publication content.
- Spyder's desktop history is used as a QA reference for high-DPI scaling and explicit focus/shortcut review.

No external plugin framework, dock architecture, custom theme ecosystem, or persistent shortcut editor is introduced.

## Validation

The exact-head Block-7 gates must verify:

1. System / Light / Dark are user-selectable and persisted only through QSettings;
2. dark primary-action foreground contrast is hardened without changing FigureSpec or project identity;
3. 1920 / 1440 / 1366 / 1280 / 1200 logical-width behavior is deterministic, with compact navigation at 1280 and 1200;
4. the inherited `>=1200x760` minimum remains unchanged;
5. accessible names, strong focus policies, visible focus QSS, and route shortcuts are installed on the v1.2 product path;
6. high-DPI runtime metadata is valid under the installed PySide6 wheel;
7. Generic XY, LSV, and FE & Partial Current complete through the v1.2 scientific/figure/export gates;
8. schema version 4 and runtime version 1.1.0 remain unchanged;
9. all earlier Stable v1.0/v1.1 and v1.2 Block 1–6 installed-wheel smokes remain green.
