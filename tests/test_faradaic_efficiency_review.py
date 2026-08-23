from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.echem import (
    FaradaicEfficiencyClosure,
    FaradaicEfficiencyError,
    faradaic_efficiency_closure,
    faradaic_efficiency_from_amount,
    faradaic_efficiency_from_rate,
    series_data_sha256,
    source_data_ref,
)


def _axis() -> Axis:
    return Axis("potential", unit="V", metadata={"reference": "RHE"})


def _fe_series(key: str, values: tuple[float, ...]) -> Series:
    return Series(
        x=(-0.5, -0.6, -0.7),
        y=values,
        key=key,
        label=key,
        x_axis=_axis(),
        y_axis=Axis("faradaic_efficiency", unit="%", label="Faradaic efficiency"),
    )


@pytest.mark.parametrize(
    ("factory", "args"),
    [
        (
            faradaic_efficiency_from_amount,
            ("1.0", "umol", -1.0, "C"),
        ),
        (
            faradaic_efficiency_from_amount,
            (1.0, "umol", "-1.0", "C"),
        ),
        (
            faradaic_efficiency_from_rate,
            ("1.0", "nmol/s", -1.0, "mA"),
        ),
        (
            faradaic_efficiency_from_rate,
            (1.0, "nmol/s", "-1.0", "mA"),
        ),
    ],
)
def test_low_level_fe_factories_reject_numeric_strings(factory, args):
    with pytest.raises(FaradaicEfficiencyError, match="real numeric"):
        factory(*args, electron_number=2)


def test_closure_factory_retains_ordered_source_provenance():
    co = _fe_series("CO", (40.0, 50.0, 60.0))
    h2 = _fe_series("H2", (30.0, 20.0, 10.0))

    closure = faradaic_efficiency_closure(Dataset([co, h2]))

    assert closure.product_keys == ("CO", "H2")
    assert tuple(source.key for source in closure.sources) == ("CO", "H2")
    assert closure.sources[0].sha256 == series_data_sha256(co)
    assert closure.sources[1].sha256 == series_data_sha256(h2)
    assert closure.sources[0].x_name == closure.condition_axis.name
    assert closure.sources[0].x_unit == closure.condition_axis.unit


def test_public_closure_constructor_rejects_non_boolean_mask():
    co = _fe_series("CO", (50.0, 50.0, 50.0))
    source = source_data_ref(co)

    with pytest.raises(FaradaicEfficiencyError, match="boolean"):
        FaradaicEfficiencyClosure(
            condition_values=co.x,
            condition_axis=co.x_axis,
            total_fraction=(0.5, 0.5, 0.5),
            exceeds_limit=(0, 0, 0),
            product_keys=("CO",),
            sources=(source,),
        )


def test_public_closure_constructor_validates_source_correspondence():
    co = _fe_series("CO", (50.0, 50.0, 50.0))
    h2_source = source_data_ref(_fe_series("H2", (50.0, 50.0, 50.0)))

    with pytest.raises(FaradaicEfficiencyError, match="source keys"):
        FaradaicEfficiencyClosure(
            condition_values=co.x,
            condition_axis=co.x_axis,
            total_fraction=(0.5, 0.5, 0.5),
            exceeds_limit=(False, False, False),
            product_keys=("CO",),
            sources=(h2_source,),
        )


def test_public_closure_constructor_requires_one_source_per_product():
    co = _fe_series("CO", (50.0, 50.0, 50.0))

    with pytest.raises(FaradaicEfficiencyError, match="one SourceDataRef"):
        FaradaicEfficiencyClosure(
            condition_values=co.x,
            condition_axis=co.x_axis,
            total_fraction=(0.5, 0.5, 0.5),
            exceeds_limit=(False, False, False),
            product_keys=("CO",),
            sources=(),
        )
