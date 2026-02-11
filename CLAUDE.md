# MoB_KML - Cell KML Generator (Web Edition)

Web tool for RF engineers. Converts cellular inventory data (LTE/5G)
into interactive map visualization (Leaflet.js) and KML export.

## Stack

- **Backend**: FastAPI (app/main.py) with REST endpoints
- **Frontend**: HTML (Jinja2) + Leaflet.js + Bootstrap 5 + vanilla JS
- **Core**: cell_kml_generator/ (pandas, rapidfuzz, openpyxl)
- **Build**: Nuitka -> standalone Windows exe (~36MB)
- **Python**: 3.9 (venv in ./venv)

## Main Structure

```
app/
  __init__.py          # REQUIRED - without it Nuitka won't detect the package
  main.py              # FastAPI server, all REST endpoints

cell_kml_generator/    # Core processing module
  config.py            # BAND_COLORS, BAND_RADIUS_M, BAND_BEAMWIDTH, BAND_RANGES
  file_handler.py      # load_file() - CSV/TXT/XLSX with auto delimiter detection
  column_mapper.py     # auto_map_columns() - fuzzy matching with rapidfuzz
  validators.py        # Validation of coords, azimuth, EARFCN
  earfcn_utils.py      # EARFCN -> Band, radius/beamwidth calculation
  geometry.py          # Haversine, generate_petal(), destination_point()
  kml_generator.py     # generate_kml() -> KML bytes
  label_configurator.py # LabelConfig dataclass
  main.py              # Legacy Tkinter GUI (not used in web edition)

templates/index.html   # Main UI
static/css/style.css   # Dark theme, flexbox layout
static/js/app.js       # Frontend: map, resize, search, measure, live mode
profiles/              # Config profiles (.json), created at runtime
```

## How to Run

```bash
# Development
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Compiled executable
.\dist\MoB_KML.exe
```

## How to Build (.exe)

```powershell
.\build_nuitka.ps1
```

### Critical Nuitka Build Gotchas

1. **app/__init__.py MUST exist** - without it: "No module named 'app'"
2. **launcher.py must import app.main DIRECTLY** (`from app.main import app as fastapi_app`), NOT as a string (`"app.main:app"`) - Nuitka doesn't resolve dynamic import strings
3. **Use `python -m pip`** (not `pip` alone) - standalone pip may install in the wrong venv
4. **Dynamic uvicorn modules** need explicit --include-package: uvicorn.protocols, uvicorn.lifespan, uvicorn.loops, anyio, starlette, multipart
5. **PowerShell Out-File adds BOM** - use [System.IO.File]::WriteAllText with UTF8Encoding($false)
6. **--windows-console-mode=force** is active for debug. Switch to `disable` and recompile for production

## Paths in the exe

app/main.py computes `APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (two levels up). Works both in dev and in the exe because Nuitka maintains relative structure from --include-data-dir.

## Main API Endpoints

- POST `/api/upload` - upload CSV/TXT/XLSX file
- POST `/api/auto-map` - automatic column mapping
- POST `/api/set-config` - apply config (mapping, labels, scale)
- GET `/api/map-data` - map data (cells, sites, labels)
- POST `/api/generate-kml` - generate KML
- GET `/api/search?q=&mode=` - search sites/cities
- POST `/api/filter-values` / `/api/apply-filters` - regional filters
- GET/POST `/api/profiles`, `/api/save-profile`, `/api/load-profile`

## Detailed Documentation

See `PROJECT_INFO.txt` for: full processing pipeline, resolved build issues, frontend functions, supported bands with EARFCN ranges.
