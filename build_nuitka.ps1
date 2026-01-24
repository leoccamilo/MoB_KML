$ErrorActionPreference = "Stop"

python -m nuitka `
  --standalone `
  --onefile `
  --disable-ccache `
  --enable-plugin=tk-inter `
  --enable-plugin=anti-bloat `
  --windows-console-mode=disable `
  --windows-icon-from-ico=mob.ico `
  --assume-yes-for-downloads `
  --follow-imports `
  --remove-output `
  --lto=yes `
  --include-data-files=mob.ico=mob.ico `
  --output-dir=dist `
  --output-filename=CellKML.exe `
  --include-package=cell_kml_generator `
  run.py
