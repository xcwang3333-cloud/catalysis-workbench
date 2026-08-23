from __future__ import annotations

import pytest

from catalysis_workbench.experimental.echem import EchemQuantityError, SourceDataRef


def test_source_data_ref_rejects_signed_and_nonhex_sha256_values():
    for invalid_digest in ("-" + "a" * 63, "g" * 64):
        with pytest.raises(EchemQuantityError, match="sha256"):
            SourceDataRef(
                key="cat-a",
                label="Cat A",
                sha256=invalid_digest,
                x_name="potential",
                x_unit="V",
                y_name="current_density",
                y_unit="mA/cm^2",
            )
