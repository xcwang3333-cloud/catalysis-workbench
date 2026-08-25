from __future__ import annotations

import pathlib
import tempfile

import catalysis_workbench.computation as computation
import catalysis_workbench.io as cw_io

Path = pathlib.Path
TemporaryDirectory = tempfile.TemporaryDirectory

ACF = """# X Y Z CHARGE MIN DIST ATOMIC VOL
------------------------------------------------------------
1 0.0 0.0 0.0 5.5 0.7 12.0
2 1.0 2.0 3.0 7.2 0.8 14.0
------------------------------------------------------------
VACUUM CHARGE: 0.1
VACUUM VOLUME: 1.0
NUMBER OF ELECTRONS: 12.8
"""


def main() -> None:
    assert issubclass(computation.BaderError, ValueError)
    assert issubclass(cw_io.BaderIOError, ValueError)
    assert computation.BaderSiteResult.__name__ == "BaderSiteResult"
    assert computation.BaderResult.__name__ == "BaderResult"
    assert computation.BaderChargeSiteResult.__name__ == "BaderChargeSiteResult"
    assert computation.BaderChargeResult.__name__ == "BaderChargeResult"

    structure = computation.AtomicStructure(
        species=("C", "O"),
        elements=("C", "O"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 2.0, 3.0)),
        site_keys=("c-site", "o-site"),
    )
    with TemporaryDirectory() as directory:
        path = Path(directory) / "ACF.dat"
        path.write_text(ACF, encoding="utf-8")
        raw = cw_io.read_bader_acf(
            path,
            structure=structure,
            position_tolerance_angstrom=1e-8,
            source_id="installed-smoke",
        )

    assert raw.mapped
    assert raw.sites[0].source_atom_index == 1
    assert raw.sites[0].site_index == 0
    assert raw.sites[0].site_key == "c-site"
    assert raw.sites[0].bader_electrons == 5.5
    charge = computation.account_bader_charges(
        raw,
        (6.0, 7.0),
        reference_id="manual-reference",
    )
    assert charge.sites[0].electron_transfer == -0.5
    assert charge.sites[0].partial_charge == 0.5
    assert round(charge.sites[1].electron_transfer, 12) == 0.2
    assert round(charge.sites[1].partial_charge, 12) == -0.2
    assert list(computation.bader_result_frame(raw)["bader_electrons"]) == [5.5, 7.2]
    assert list(computation.bader_charge_frame(charge)["reference_electrons"]) == [6.0, 7.0]
    print("installed v0.6 Bader parser/charge-accounting smoke: ok")


if __name__ == "__main__":
    main()
