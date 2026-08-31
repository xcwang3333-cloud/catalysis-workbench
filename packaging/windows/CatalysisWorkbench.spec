# PyInstaller specification for the Windows x64 CatalysisWorkbench v1.1 desktop.
#
# The application package itself is installed from the immutable v1.1.0 tag in
# an isolated build environment. This spec belongs to post-release packaging
# infrastructure and must not be used to freeze product code from the branch.

from pathlib import Path

spec_dir = Path(SPECPATH)
launcher = spec_dir / "launcher.py"

a = Analysis(
    [str(launcher)],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "openpyxl",
        "matplotlib.backends.backend_qtagg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pymatgen",
        "pyvista",
        "vtk",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CatalysisWorkbench",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CatalysisWorkbench",
)
