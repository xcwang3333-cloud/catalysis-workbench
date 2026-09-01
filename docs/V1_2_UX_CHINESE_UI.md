# v1.2 Chinese-first UI UX pass

This UX pass makes the visible v1.2 product desktop Chinese-first while preserving scientific notation and all persisted semantics.

## Presentation rule

Translate ordinary interface language into Simplified Chinese:

- menus, navigation, buttons, section headings, empty states, help text, status text, and modal decisions;
- data-import and mapping labels;
- Analysis Workspace and Processing Inspector labels;
- Figure Workbench and Figure Package Export presentation text.

Keep scientific abbreviations, physical-variable notation, and unit symbols unchanged where they are the conventional scientific representation, including examples such as:

- `LSV`, `FE`, `RHE`, `SHE`, `iR`, `X`, `Y`, `pH`;
- `V`, `K`, `Ω`, `cm²`, `mA/cm^2`, `A/cm^2`, `%`;
- `SVG`, `PDF`, `PNG`, `XLSX`, `TXT`.

## Frozen semantic boundary

This is a presentation-only change.

The following remain unchanged:

- `AnalysisSession`, evaluators, scientific arrays, and transformation behavior;
- task IDs such as `lsv`, `fe_partial_current`, and `generic_xy`;
- view/preset/scale IDs such as `raw`, `processed`, `publication`, and `linear`;
- user-entered project titles, series names, paths, and scientific labels;
- FigureDraft/FigureSpec semantics and renderer output;
- Figure Package contents, manifest identity, and export determinism;
- AnalysisDocument schema version 4;
- runtime/distribution version `1.1.0`;
- legacy v1.0/v1.1 desktop constructors.

Technical exception details may remain English so diagnostic information is not rewritten or obscured.

## Architecture

`ChineseUiLocalizer` is installed only by the v1.2 `create_workbench_desktop()` path. It activates when the product window is actually shown and translates app-owned Qt presentation strings. This preserves retained pre-show compatibility tests and avoids replacing internal enum/text values that participate in scientific behavior.

Combo-box display strings are localized only when they are backed by stable `itemData`; combos whose `currentText()` is itself a scientific or serialized value remain untouched.

The implementation does not introduce a full Qt `.ts/.qm` language framework or a language selector in this pass.

## Validation

Fresh-wheel validation must confirm:

- Home/navigation/New Analysis display Chinese after the window is shown;
- `FE & Partial Current` no longer loses its ampersand to Qt mnemonic parsing because its visible label becomes `FE 与分电流`;
- Analysis/Processing/Figure/Export presentation labels are Chinese;
- `RHE`, `SHE`, `iR`, `pH`, `X/Y`, file formats, and unit symbols remain unchanged;
- internal combo values and task IDs remain unchanged;
- user-owned project titles are not translated;
- legacy accessibility metadata and stable compatibility behavior remain intact.

Dark-theme visual completeness is tracked separately and is intentionally outside this localization pass.
