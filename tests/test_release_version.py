from __future__ import annotations

import catalysis_workbench


def test_release_candidate_runtime_version_is_final_v0_1_0():
    assert catalysis_workbench.__version__ == "0.1.0"
