"""Minimal example of the v0.1 XY-processing pipeline."""

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.processing import crop, integrate, normalize, savgol

series = Series(
    x=[100, 200, 300, 400, 500, 600, 700],
    y=[2.0, 2.5, 4.0, 3.2, 5.0, 3.5, 2.8],
    label="Example spectrum",
    x_axis=Axis("shift", unit="cm^-1", label="Raman shift"),
    y_axis=Axis("intensity", unit="a.u.", label="Intensity"),
    key="example-spectrum",
)

selected = crop(series, x_min=200, x_max=600)
smoothed = savgol(selected, window_length=5, polyorder=2)
normalized = normalize(smoothed, method="max")
area = integrate(normalized, absolute=True)

print(normalized.metadata["processing_history"])
print(area.value)
