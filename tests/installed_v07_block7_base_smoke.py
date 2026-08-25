"""Installed base-wheel smoke for the v0.7 Block-7 lazy 3-D public surface."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.visualization import (
    Volumetric3DRenderResult,
    Volumetric3DRenderSpec,
    export_volumetric_scene_3d,
    render_volumetric_scene_3d,
)


def _heavy_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name == "pyvista"
        or name.startswith("pyvista.")
        or name == "vtk"
        or name.startswith("vtk.")
    )


def main() -> None:
    assert callable(render_volumetric_scene_3d)
    assert callable(export_volumetric_scene_3d)
    assert not _heavy_modules(), _heavy_modules()

    spec = Volumetric3DRenderSpec(window_size_px=(320, 240), anti_aliasing="none")
    assert spec.window_size_px == (320, 240)
    assert len(spec.digest) == 64
    assert not _heavy_modules(), _heavy_modules()

    pixels = np.zeros((2, 3, 3), dtype=np.uint8)
    result = Volumetric3DRenderResult(
        image=pixels,
        scene_geometry_digest="installed-scene",
        render_spec_digest=spec.digest,
        backend_name="test-backend",
        backend_version="1",
        vtk_version="none",
        visible_layer_count=1,
    )
    assert result.image.shape == (2, 3, 3)
    assert not result.image.flags.writeable
    assert not hasattr(result, "plotter")
    assert not _heavy_modules(), _heavy_modules()
    print("installed v0.7 Block-7 base lazy-backend smoke: ok")


if __name__ == "__main__":
    main()
