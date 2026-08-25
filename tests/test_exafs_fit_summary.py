from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.experimental.characterization.exafs_fit_summary import (
    EXAFSFitDiagnostic,
    EXAFSFitSummary,
    EXAFSFitSummaryError,
    EXAFSFitValue,
    EXAFSPathSummary,
    exafs_fit_diagnostics_frame,
    exafs_fit_summary_frame,
)


def _summary() -> EXAFSFitSummary:
    path = EXAFSPathSummary(
        key="fe-o-1",
        label="Fe-O first shell",
        coordination_number=EXAFSFitValue(5.8, 0.4, status="fitted"),
        r_angstrom=EXAFSFitValue(1.98, 0.02, status="fitted"),
        sigma2_angstrom2=EXAFSFitValue(0.006, 0.001, status="fitted"),
        delta_e0_ev=EXAFSFitValue(2.3, 0.5, status="fitted"),
        amplitude=EXAFSFitValue(0.85, status="fixed"),
        metadata={"path_file": "fe-o.dat", "tags": ["first", "shell"]},
    )
    return EXAFSFitSummary(
        producer="Larch",
        source_id="fit-001",
        paths=(path,),
        diagnostics=(
            EXAFSFitDiagnostic("R-factor", 0.0123),
            EXAFSFitDiagnostic("chi-square", 123.4),
        ),
        metadata={"project": {"name": "synthetic"}},
    )


def test_complete_summary_preserves_reported_state() -> None:
    summary = _summary()
    path = summary.paths[0]
    assert path.coordination_number.value == pytest.approx(5.8)
    assert path.r_angstrom.value == pytest.approx(1.98)
    assert path.sigma2_angstrom2.uncertainty == pytest.approx(0.001)
    assert path.delta_e0_ev.status == "fitted"
    assert path.amplitude.status == "fixed"
    assert [item.label for item in summary.diagnostics] == [
        "R-factor",
        "chi-square",
    ]


def test_missing_is_explicit_and_distinct_from_zero() -> None:
    path = EXAFSPathSummary(
        key="path",
        coordination_number=EXAFSFitValue(0.0, status="reported"),
    )
    assert path.coordination_number.value == pytest.approx(0.0)
    assert path.coordination_number.status == "reported"
    assert path.r_angstrom.value is None
    assert path.r_angstrom.status == "unavailable"


def test_negative_external_fit_values_are_retained_not_repaired() -> None:
    path = EXAFSPathSummary(
        key="suspicious-fit",
        sigma2_angstrom2=EXAFSFitValue(-0.001, 0.0002, status="fitted"),
        delta_e0_ev=EXAFSFitValue(-3.2, status="fitted"),
    )
    assert path.sigma2_angstrom2.value == pytest.approx(-0.001)
    assert path.delta_e0_ev.value == pytest.approx(-3.2)


def test_fit_value_validation_fails_closed() -> None:
    with pytest.raises(EXAFSFitSummaryError, match="finite"):
        EXAFSFitValue(np.inf)
    with pytest.raises(EXAFSFitSummaryError, match="non-negative"):
        EXAFSFitValue(1.0, uncertainty=-0.1)
    with pytest.raises(EXAFSFitSummaryError, match="must not carry"):
        EXAFSFitValue(0.0, status="unavailable")
    with pytest.raises(EXAFSFitSummaryError, match="require"):
        EXAFSFitValue(None, status="reported")


def test_duplicate_keys_and_diagnostic_labels_fail() -> None:
    path = EXAFSPathSummary(key="same")
    with pytest.raises(EXAFSFitSummaryError, match="path keys"):
        EXAFSFitSummary(
            producer="Artemis",
            source_id="fit",
            paths=(path, EXAFSPathSummary(key="same")),
        )
    with pytest.raises(EXAFSFitSummaryError, match="diagnostic labels"):
        EXAFSFitSummary(
            producer="Artemis",
            source_id="fit",
            paths=(path,),
            diagnostics=(
                EXAFSFitDiagnostic("R-factor", 0.01),
                EXAFSFitDiagnostic("R-factor", 0.02),
            ),
        )


def test_metadata_is_deeply_immutable_and_detached() -> None:
    metadata = {"nested": {"values": [1, 2]}}
    path = EXAFSPathSummary(key="path", metadata=metadata)
    metadata["nested"]["values"].append(3)
    assert path.metadata["nested"]["values"] == (1, 2)
    with pytest.raises(TypeError):
        path.metadata["new"] = "x"
    thawed = path.metadata_dict()
    thawed["nested"]["values"].append(9)
    assert path.metadata["nested"]["values"] == (1, 2)


def test_path_dataframe_has_explicit_columns_and_is_detached() -> None:
    summary = _summary()
    frame = exafs_fit_summary_frame(summary)
    assert list(frame["path_key"]) == ["fe-o-1"]
    assert frame.loc[0, "r_angstrom"] == pytest.approx(1.98)
    assert frame.loc[0, "r_angstrom_uncertainty"] == pytest.approx(0.02)
    assert frame.loc[0, "sigma2_angstrom2"] == pytest.approx(0.006)
    assert frame.loc[0, "delta_e0_ev"] == pytest.approx(2.3)
    frame.loc[0, "r_angstrom"] = 9.9
    assert summary.paths[0].r_angstrom.value == pytest.approx(1.98)


def test_diagnostics_dataframe_preserves_producer_labels_and_units() -> None:
    summary = EXAFSFitSummary(
        producer="Producer-X",
        source_id="fit-x",
        paths=(EXAFSPathSummary(key="path"),),
        diagnostics=(
            EXAFSFitDiagnostic("reduced chi-square", 4.2, unit=None),
            EXAFSFitDiagnostic("N independent", 12.5, unit="count"),
        ),
    )
    frame = exafs_fit_diagnostics_frame(summary)
    assert list(frame["diagnostic_label"]) == [
        "reduced chi-square",
        "N independent",
    ]
    assert list(frame["unit"]) == [None, "count"]
