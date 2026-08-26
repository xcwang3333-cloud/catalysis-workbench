"""Installed-wheel smoke for explicit zero-centered color limits."""

from catalysis_workbench.visualization import symmetric_color_limits


def main() -> None:
    assert symmetric_color_limits([-2.0, 5.0]) == (-5.0, 5.0)
    assert symmetric_color_limits([0.0], zero_half_range=0.25) == (-0.25, 0.25)
    print("installed symmetric color-limit smoke: ok")


if __name__ == "__main__":
    main()
