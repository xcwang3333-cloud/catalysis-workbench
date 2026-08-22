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

By default the scripts write figures to `examples/output/`.

## LSV

`lsv_quickstart.py` reads `data/lsv_example.csv`, performs an explicit reference-potential shift, iR correction, geometric current-density normalization, publication plotting, and PNG/SVG/PDF export.

The example values are synthetic and exist only to exercise the workflow; they are not benchmark electrochemical data.

## XRD

`xrd_quickstart.py` reads `data/xrd_example.csv`, validates 2θ/intensity semantics, crops and max-normalizes the pattern, adds one explicit peak annotation, and exports the resulting publication figure.

## Raman

`raman_quickstart.py` reads `data/raman_example.csv`, crops and max-normalizes the spectrum, calculates an explicit-window `I_D/I_G` height ratio, adds D/G annotations, and exports the figure.

`RamanBand` windows are supplied by the caller; CatalysisWorkbench does not silently assume universal D/G windows.

## Example-data policy

Keep examples small enough to review in Git. Large raw experimental or computational datasets should not be committed solely as demonstrations. Prefer compact fixtures that reproduce the scientific/API behavior being documented or tested.
