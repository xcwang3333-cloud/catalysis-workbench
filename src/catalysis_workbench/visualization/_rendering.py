"""Internal rendering helpers shared by generic visualization primitives."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .specs import FigureSpec


@contextmanager
def figure_axes_context(spec: FigureSpec) -> Iterator[tuple[Figure, Axes]]:
    """Create a headless figure/axes pair inside an isolated Matplotlib rc context."""
    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    layout = spec.layout
    style = spec.style
    rc = {
        "font.family": style.font_family,
        "font.size": style.font_size,
        "axes.unicode_minus": True,
    }
    with mpl.rc_context():
        mpl.rcdefaults()
        mpl.rcParams.update(rc)
        figure = Figure(
            figsize=(layout.figure_width_in, layout.figure_height_in),
            dpi=100,
        )
        FigureCanvasAgg(figure)
        ax = figure.add_axes(layout.axes_bounds_fraction())
        yield figure, ax


def finalize_axes(
    ax: Axes,
    spec: FigureSpec,
    *,
    xlabel: str,
    ylabel: str,
    labeled_count: int,
    apply_xscale: bool = True,
) -> None:
    """Apply scales, physical-independent styling, legend, and annotations.

    ``apply_xscale=False`` is reserved for renderers that install a categorical
    ``FixedLocator``/``FixedFormatter`` before finalization. Reapplying Matplotlib's
    linear scale after those categorical ticks would replace them with numeric locators.
    """
    style = spec.style
    if apply_xscale:
        ax.set_xscale(spec.xscale)
    ax.set_yscale(spec.yscale)
    if spec.xlim is not None:
        ax.set_xlim(*spec.xlim)
    if spec.ylim is not None:
        ax.set_ylim(*spec.ylim)

    ax.set_xlabel(xlabel, fontsize=style.axis_label_size)
    ax.set_ylabel(ylabel, fontsize=style.axis_label_size)
    if spec.title:
        ax.set_title(spec.title, fontsize=style.title_size)

    for spine in ax.spines.values():
        spine.set_linewidth(style.spine_width)
    ax.tick_params(
        axis="both",
        which="major",
        direction=style.tick_direction,
        length=style.tick_length,
        width=style.tick_width,
        labelsize=style.tick_label_size,
        top=style.top_ticks,
        right=style.right_ticks,
    )
    ax.tick_params(
        axis="both",
        which="minor",
        direction=style.tick_direction,
        length=style.tick_length * 0.55,
        width=style.tick_width,
        top=style.top_ticks,
        right=style.right_ticks,
    )
    if style.minor_ticks:
        ax.minorticks_on()
    else:
        ax.minorticks_off()

    show_legend = labeled_count > 1 if spec.show_legend is None else spec.show_legend
    if show_legend and labeled_count:
        ax.legend(
            loc=style.legend_location,
            fontsize=style.legend_font_size,
            frameon=style.legend_frame,
        )

    for annotation in spec.annotations:
        transform = ax.transAxes if annotation.coordinates == "axes" else ax.transData
        ax.text(
            annotation.x,
            annotation.y,
            annotation.text,
            transform=transform,
            fontsize=(style.font_size if annotation.font_size is None else annotation.font_size),
            ha=annotation.horizontal_alignment,
            va=annotation.vertical_alignment,
            rotation=annotation.rotation,
            color=annotation.color,
        )
