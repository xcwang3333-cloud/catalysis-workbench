from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XANESNormalizationResult,
    XANESNormalizationSpec,
    XASError,
    XASWindow,
    normalize_xanes,
)


def test_xanes_result_rejects_digest_not_bound_to_retained_source() -> None:
    energy = np.arange(0.0, 7.0)
    delta = energy - 3.0
    source = Series(
        x=energy,
        y=np.where(energy < 3.0, 1.0 + 0.1 * delta, 3.0 + 0.2 * delta),
        key="digest-source",
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis("mu", unit="a.u."),
    )
    result = normalize_xanes(
        source,
        XANESNormalizationSpec(
            e0_ev=3.0,
            pre_edge=XASWindow(0.0, 2.0),
            post_edge=XASWindow(4.0, 6.0),
        ),
    )

    with pytest.raises(XASError, match="source_digest contradicts"):
        XANESNormalizationResult(
            source_key=result.source_key,
            source_digest="0" * 64,
            source_energy_ev=result.source_energy_ev,
            source_mu=result.source_mu,
            e0_ev=result.e0_ev,
            pre_edge=result.pre_edge,
            post_edge=result.post_edge,
            pre_edge_order=result.pre_edge_order,
            post_edge_order=result.post_edge_order,
            pre_edge_coefficients=result.pre_edge_coefficients,
            post_edge_coefficients=result.post_edge_coefficients,
            pre_edge_curve=result.pre_edge_curve,
            post_edge_curve=result.post_edge_curve,
            edge_step=result.edge_step,
            normalized=result.normalized,
        )
