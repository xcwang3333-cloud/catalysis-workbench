# Explicit zero-centered color limits

`symmetric_color_limits(values, *, zero_half_range=1.0)` derives a
renderer-independent display interval centered exactly at zero.

For any nonzero real input, the helper performs only:

```text
half_range = max(abs(values))
limits = (-half_range, +half_range)
```

For all-zero input, the interval would otherwise be degenerate. The helper therefore
uses the explicit positive `zero_half_range` only in that case.

```python
import numpy as np

from catalysis_workbench.visualization import symmetric_color_limits

limits = symmetric_color_limits(np.array([[-2.0, 0.0], [4.0, 1.0]]))
assert limits == (-4.0, 4.0)

zero_limits = symmetric_color_limits(
    np.zeros((3, 3)),
    zero_half_range=0.5,
)
assert zero_limits == (-0.5, 0.5)
```

The input may have any shape, including a scalar, but must be non-empty, real and
finite. Complex values, NaN and infinity fail explicitly. Caller-owned arrays are not
mutated.

This helper selects limits only. It does not construct a Matplotlib normalization or
colormap, clip values, estimate percentiles, smooth data, normalize scientific values,
infer signs or units, or render a heatmap. Renderers remain responsible for applying
the returned explicit limits.

## Prior-art and license boundary

Matplotlib
[`CenteredNorm`](https://matplotlib.org/stable/api/_as_gen/matplotlib.colors.CenteredNorm.html)
and
[`TwoSlopeNorm`](https://matplotlib.org/stable/api/_as_gen/matplotlib.colors.TwoSlopeNorm.html)
are semantics/API references for mapping around a conceptual center. Matplotlib is an
existing project dependency under its own Matplotlib license. No upstream
implementation is copied or adapted, and Issue #245 adds no dependency.
