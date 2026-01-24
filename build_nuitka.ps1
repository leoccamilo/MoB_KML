$ErrorActionPreference = "Stop"

python -m nuitka `
  --standalone `
  --onefile `
  --disable-ccache `
  --enable-plugin=tk-inter `
  --enable-plugin=anti-bloat `
  --windows-console-mode=disable `
  --assume-yes-for-downloads `
  --follow-imports `
  --remove-output `
  --lto=yes `
  --experimental=use_pefile_fullrecursion `
  --output-dir=dist_nuitka_protegido `
  --output-filename=CellKML.exe `
  --include-package=cell_kml_generator `
  cell_kml_generator/main.py
