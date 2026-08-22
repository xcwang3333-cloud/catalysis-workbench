import pytest

from catalysis_workbench.core import Series
from catalysis_workbench.processing import ProcessingError, savgol


def test_savgol_rejects_irregular_x_spacing():
    series = Series(
        x=[0.0, 1.0, 2.2, 3.0, 4.0],
        y=[0.0, 1.0, 4.0, 9.0, 16.0],
    )

    with pytest.raises(ProcessingError, match="uniform x spacing"):
        savgol(series, window_length=5, polyorder=2)
