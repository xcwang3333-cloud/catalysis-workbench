"""Exact-size export helpers for publication figures."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

import matplotlib as mpl
from matplotlib.figure import Figure

from .specs import ExportSpec, FigureSpec, VisualizationError

_SUPPORTED_FORMATS = {"png", "svg", "pdf"}


def _resolve_format(path: Path, requested: str | None) -> str:
    if requested is not None:
        output_format = str(requested).strip().lower().lstrip(".")
    else:
        output_format = path.suffix.lower().lstrip(".")
    if output_format not in _SUPPORTED_FORMATS:
        raise VisualizationError(
            f"export format must be one of {sorted(_SUPPORTED_FORMATS)!r}; "
            f"got {output_format!r}"
        )
    return output_format


def export_figure(
    figure: Figure,
    path: str | PathLike[str],
    *,
    spec: FigureSpec | None = None,
    format: str | None = None,
    dpi: int | None = None,
    transparent: bool | None = None,
) -> Path:
    """Export one figure as PNG, SVG, or PDF without changing live figure state.

    ``bbox_inches='tight'`` is deliberately not used: trimming would change the
    publication figure's requested physical width/height.  When ``spec`` is supplied,
    its physical size is applied only for the save operation and the figure's original
    size is restored afterwards so preview and export dimensions remain independent.
    """
    if not isinstance(figure, Figure):
        raise TypeError("figure must be a matplotlib.figure.Figure")
    if spec is not None and not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    output_path = Path(path)
    output_format = _resolve_format(output_path, format)
    export = ExportSpec() if spec is None else spec.export
    output_dpi = export.dpi if dpi is None else int(dpi)
    if output_dpi <= 0:
        raise VisualizationError("export dpi must be greater than zero")
    output_transparent = export.transparent if transparent is None else bool(transparent)

    original_size = tuple(float(value) for value in figure.get_size_inches())
    if spec is not None:
        figure.set_size_inches(
            spec.layout.figure_width_in,
            spec.layout.figure_height_in,
            forward=True,
        )

    rc = {
        "svg.fonttype": export.svg_fonttype,
        "pdf.fonttype": export.pdf_fonttype,
    }
    try:
        with mpl.rc_context(rc):
            figure.savefig(
                output_path,
                format=output_format,
                dpi=output_dpi,
                transparent=output_transparent,
                bbox_inches=None,
            )
    finally:
        if spec is not None:
            figure.set_size_inches(*original_size, forward=True)
    return output_path
