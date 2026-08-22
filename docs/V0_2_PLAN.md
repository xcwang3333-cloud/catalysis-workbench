# v0.2 electrochemistry plan

v0.2 extends the reviewed v0.1 XY foundation into quantitative electrochemical analysis. New scientific modules must continue to follow the project rule: survey comparable open-source projects before implementation, record useful algorithms/architecture/tests/licenses, reuse mature dependencies where appropriate, and keep scientific calculations separate from visualization.

## Shared contracts first

Before domain modules proliferate, v0.2 should centralize conservative electrochemistry quantity validation and traceable fit-result conventions. The existing LSV public API must remain compatible. Units remain explicit strings in v0.2; Pint is still deferred.

The visualization layer should also gain generic scatter and bar rendering once, using the existing `FigureSpec` layout/typography/export state. Domain modules should not create separate Matplotlib style systems.

## Domain scope

- Tafel: explicit fit windows/branches, log-current handling, slope/intercept/fit-quality provenance.
- Faradaic efficiency: explicit charge/electron stoichiometry and product amount/rate inputs; no raw chromatogram calibration yet.
- Partial current density: explicit FE fraction and signed/magnitude convention.
- Mass/specific activity: explicit denominator basis (catalyst mass, metal mass, ECSA, or another caller-declared basis).
- TOF/TOFapp: explicit electron number and site/metal inventory; total-metal normalization is `TOFapp` unless an active-site inventory is genuinely supplied.
- CV/Cdl/ECSA: explicit scan rates/non-Faradaic window, Cdl fitting, and caller-supplied specific capacitance for ECSA conversion.
- Stability: chronoamperometry/chronopotentiometry retention, drift, and interval summaries without hiding sign or reference semantics.
- RRDE/K-L: explicit collection efficiency, rotation units, electron-number/peroxide equations, and Koutecky-Levich fitting inputs/constants.

## Dependencies between modules

Faradaic efficiency precedes product partial-current helpers. Activity and TOF should reuse the same current/product and denominator-provenance conventions rather than each inventing unit parsing. CV/Cdl/ECSA and RRDE/K-L can proceed after the shared electrochemistry foundation because they have fewer dependencies on FE/product metrics.
