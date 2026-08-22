# Examples

The v0.1 examples are intentionally compact and non-sensitive. Each script uses only documented public package exports and follows the same workflow used in research projects:

```text
file -> Dataset/Series -> scientific processing -> FigureSpec -> plot -> PNG/SVG/PDF
```

Run them from the repository root after installing the package:

```bash
python examples/lsv_quickstart.py
python examples/xrd_quickstart.py
python examples/raman_quickstart.py
```

By default the scripts write figures to `examples/output/`. Generated files in that directory are ignored by Git, so running the documented examples does not dirty the source checkout.

## LSV

`lsv_quickstart.py` reads `data/lsv_example.csv`, derives an RHE conversion offset from an explicit illustrative Ag/AgCl reference potential versus SHE, pH, and temperature, then applies iR correction, geometric current-density normalization, publication plotting, and PNG/SVG/PDF export.

The example uses `0.210 V vs SHE`, pH 13.0, and 298.15 K only to demonstrate the API. In real work, the reference-potential term must match the actual reference electrode/filling solution and the pH/temperature must match the experiment. The synthetic current/potential values are not benchmark electrochemical data.

## XRD

`xrd_quickstart.py` reads `data/xrd_example.csv`, validates 2θ/intensity semantics, crops and max-normalizes the pattern, adds one explicit peak annotation, and exports the resulting publication figure.

## Raman

`raman_quickstart.py` reads `data/raman_example.csv`, crops and max-normalizes the spectrum, calculates an explicit-window `I_D/I_G` height ratio, adds D/G annotations, and exports the figure.

`RamanBand` windows are supplied by the caller; CatalysisWorkbench does not silently assume universal D/G windows.

## Example-data policy

Keep examples small enough to review in Git. Large raw experimental or computational datasets should not be committed solely as demonstrations. Prefer compact fixtures that reproduce the scientific/API behavior being documented or tested.
