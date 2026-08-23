# v0.2 scatter and bar visualization contract

Issue #20 extends the reviewed v0.1 visualization layer with generic scatter and categorical bar rendering needed by later quantitative electrochemistry modules. The implementation stays visualization-only: no electrochemical equations, fitting, uncertainty estimation, or scientific normalization live here.

## Prior-art review

The implementation was designed after inspecting mature open-source plotting APIs and their licenses:

- `matplotlib/matplotlib` is the rendering backend already used by CatalysisWorkbench. Its `Axes.scatter`, `Axes.bar`, and `Axes.errorbar` APIs provide the primitive artist model we need. The Matplotlib license permits reuse under its stated attribution/change conditions; CatalysisWorkbench calls the public API and does not copy Matplotlib implementation code.
- `garrettj403/SciencePlots` (MIT) demonstrates small, composable publication presets and temporary style contexts. CatalysisWorkbench keeps the useful idea that presets are starting points, but uses explicit immutable `FigureSpec`/`PlotStyle` state rather than depending on a global stylesheet package.
- `nschloe/matplotx` (MIT) demonstrates narrow Matplotlib extensions, including clean bar plots and value annotations, without replacing Matplotlib. CatalysisWorkbench follows the same narrow-extension principle but keeps its own exact-size/layout and stable-key contracts and does not add matplotx as a dependency.

No implementation code is copied from these projects and no new plotting dependency is added.

## Scatter API

`render_scatter(...)` accepts the existing core `Series` or `Dataset` objects. It uses the same axis-compatibility rules as `render_curves`: matching axis names/units plus compatibility-critical `reference` and `normalization` metadata.

Scatter points reuse `FigureSpec`, `PlotStyle`, `SeriesStyle`, annotations, physical layout, legend behavior, rc isolation, and exact export semantics. `PlotStyle.marker_size` is interpreted as a marker diameter in points and converted to Matplotlib scatter area internally so the existing marker-size control has a consistent user-facing meaning.

Uncertainty is never inferred. Optional `ScatterError` records hold explicit x/y uncertainty arrays. A single `ScatterError` may accompany a single `Series`; a `Dataset` uses a mapping addressed only by non-empty stable `Series.key` values. Error arrays must match the point count, be real, non-negative where finite, and may use NaN to represent an explicitly missing error value.

## Bar API

Categorical summaries do not fit the numerical-x `Series` core model, so Issue #20 deliberately avoids changing `core`. Instead visualization owns three small immutable input records:

- `BarCategory(key, label)` for deterministic category order and stable category addressing;
- `BarSeries(key, values, label, errors=None)` for one ordered scalar summary series;
- `BarData(categories, series, x_axis, y_axis)` for one single-series or grouped bar figure.

`BarData` requires non-empty unique category keys and series keys. Display labels may be duplicated or explicitly blank. Values are real float64 arrays; NaN is preserved as explicit missing data while +/-inf and complex values fail. Explicit error arrays must match category count and contain only non-negative finite values or NaN.

`SeriesStyle` remains the per-series style contract. A new small `CategoryStyle` provides stable-key category overrides for color, alpha, tick-label text, and visibility. Series color is the grouped-bar default; an explicitly configured category color/alpha takes precedence for that category. This makes single-series catalyst-comparison bars easy to style by catalyst key without forcing grouped bars to abandon per-series colors.

`PlotStyle.bar_group_width` controls the total fractional width occupied by one category group. Bars are centered deterministically within each group in `BarData.series` order. Error bars are drawn only from explicit `BarSeries.errors` using `PlotStyle.errorbar_capsize`; no standard deviation/standard error is computed by visualization.

Because the x axis is categorical, `render_bars(...)` requires a linear x scale. Y scaling/limits remain controlled by the normal `FigureSpec` contract.

## Shared rendering invariants

All three generic renderers (`render_curves`, `render_scatter`, `render_bars`) must preserve these rules:

- return `(fig, ax)` and never call `show()`;
- create a headless `Figure`/Agg canvas without `pyplot`;
- start from Matplotlib defaults inside a local `rc_context`, then apply explicit `FigureSpec` state, restoring ambient rcParams afterwards;
- use `LayoutSpec.axes_bounds_fraction()` so figure size and physical axes drawing-region size remain exact and identical across renderer types;
- treat `None` axis labels as automatic and explicit `""` as intentional blank labels;
- address overrides by stable keys, never by duplicate display labels;
- preserve deterministic input order;
- draw only explicitly supplied uncertainty;
- keep vector text editable under the existing SVG/PDF export settings and preserve exact PNG/SVG/PDF canvas size.

## Scope boundary

Issue #20 does not implement FE, Tafel, activity, TOF, ECSA, RRDE, or any other electrochemical analysis. It also does not add automatic significance markers, statistical aggregation, automatic uncertainty, broken axes, multi-panel layout, or interactive editing. Those belong to later domain or GUI work.