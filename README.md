# MoB_KML - Cell KML Generator (Web Edition)

Web tool for RF engineers that converts cellular inventory data (LTE/5G)
into interactive map visualization and KML export, without needing Google Earth.

**Stack**: FastAPI + Leaflet.js + Pandas
**Status**: Production - Compiled as standalone .exe
**Last updated**: 02/10/2026

---

## Features

- **Modern web interface** with interactive map (Leaflet.js) - replaces Google Earth
- **Data import**: CSV, TXT (automatic delimiter detection) and Excel (.xlsx)
- **Automatic column mapping** with fuzzy matching (rapidfuzz)
- **Real-time visualization** (Live Mode) - map updates on every config change
- **Directional petals** per sector with configurable beamwidth and radius per band
- **Colors by frequency band** (700MHz to 3700MHz, LTE and 5G NR)
- **Resizable panels** - drag the bar between config and map
- **Measurement tool** - click two points to measure distance
- **Site/city search** in the map search bar
- **Regional filters** - filter by State, Area Code, Regional, City
- **Configuration profiles** - save and load configs as JSON
- **KML export** (optional) and TXT report
- **Two base maps**: OpenStreetMap and Esri Satellite

## Supported Bands

| Band | Frequency | EARFCN Range | Default Radius | Beamwidth |
|------|-----------|--------------|----------------|-----------|
| 28 | 700 MHz | 9210-9659 | 500m | 90 |
| 5 | 850 MHz | 2410-2649 | 700m | 85 |
| 8 | 900 MHz | 3450-3799 | 650m | 80 |
| 3 | 1800 MHz | 1200-1949 | 400m | 65 |
| 1 | 2100 MHz | 0-599 | 350m | 65 |
| 7 | 2600 MHz FDD | 2750-3449 | 300m | 55 |
| 38 | 2600 MHz TDD | 37750-38249 | 300m | 55 |
| 40 | 2300 MHz TDD | 38650-39649 | 320m | 60 |
| 41 | 2500 MHz TDD | 39650-41589 | 310m | 60 |
| 42 | 3500 MHz | 41590-43589 | 220m | 50 |
| 43 | 3700 MHz | 43590-45589 | 200m | 45 |
| 78 | 3500 MHz 5G NR | 620000-680000 | 220m | 50 |

---

## Run (Development)

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Access: http://127.0.0.1:8000

## Run (Compiled Executable)

```
.\dist\MoB_KML.exe
```

The exe starts the FastAPI server and opens the browser automatically.
No Python installation required. Works on any Windows 10/11 64-bit.

---

## Build the Executable (.exe)

### Prerequisites
- Python 3.9+
- Visual Studio Build Tools (C++ compiler)
- 8GB RAM (16GB recommended)
- 10GB free disk space

### Build
```powershell
# Open PowerShell and navigate to the project
cd C:\MoB_KML_bkp\MoB_KML_Ingles

# Run the build script
.\build_nuitka.ps1
```

The script automatically:
1. Activates the venv and installs dependencies
2. Creates `launcher.py` (exe entry point)
3. Compiles with Nuitka (~10-20 min)
4. Generates `.\dist\MoB_KML.exe` (~36MB)
5. Creates a desktop shortcut

### Important build notes
- `launcher.py` imports `app.main` **directly** (not as a string) so that Nuitka detects the dependency
- The `app/` package must have `__init__.py`
- Use `python -m pip` (not `pip` alone) to ensure installation in the correct venv
- Console is visible (`--windows-console-mode=force`) for debugging. After confirming everything works, change to `--windows-console-mode=disable` in `build_nuitka.ps1`
- If the exe errors, it writes to `mob_kml_error.log` next to the executable

---

## Usage Flow

1. **Import Data** - Load CSV/TXT/XLSX
2. **Column Mapping** - Click "Auto Map" (map appears automatically with Live Mode)
3. **Petal Config** - Adjust global scale and radius/beamwidth per band
4. **Labels & View** - Configure site labels
5. **Filters** - Filter by State, Area Code, Regional, City (if available in the data)
6. **Generate Output** - Download KML (optional) or Export Report

---

## Project Structure

```
MoB_KML_Ingles/
|-- app/                           # Web interface (FastAPI)
|   |-- __init__.py
|   |-- main.py                    # FastAPI server, REST endpoints
|
|-- cell_kml_generator/            # Core processing module
|   |-- __init__.py
|   |-- config.py                  # Constants: colors, radii, beamwidths, EARFCN ranges
|   |-- file_handler.py            # CSV/TXT/XLSX reader with auto delimiter detection
|   |-- column_mapper.py           # Automatic column mapping (fuzzy matching)
|   |-- validators.py              # Data validation (coords, azimuth, EARFCN)
|   |-- earfcn_utils.py            # EARFCN -> Band conversion, radius/beamwidth calculation
|   |-- geometry.py                # Geodesic calculations (haversine, petals, bearing)
|   |-- kml_generator.py           # KML file generation
|   |-- label_configurator.py      # Label configuration (LabelConfig dataclass)
|   |-- main.py                    # Legacy Tkinter GUI (not used in web edition)
|
|-- templates/
|   |-- index.html                 # Main UI (Jinja2 template)
|
|-- static/
|   |-- css/style.css              # Styles (dark theme, flexbox layout)
|   |-- js/app.js                  # Frontend logic (Leaflet, resize, search, measure)
|
|-- profiles/                      # Saved configuration profiles (.json)
|-- venv/                          # Python virtual environment
|-- dist/                          # Compiled executable
|   |-- MoB_KML.exe
|
|-- run.py                         # Legacy entry point (Tkinter GUI)
|-- launcher.py                    # Exe entry point (FastAPI + browser)
|-- build_nuitka.ps1               # Nuitka build script
|-- requirements.txt               # Python dependencies
|-- mob.ico                        # Application icon
|-- example_test.csv               # Test file (13 sectors, 6 sites)
|-- PROJECT_INFO.txt               # Detailed technical documentation
```

## Dependencies (requirements.txt)

| Package | Usage |
|---------|-------|
| pandas | Tabular data manipulation |
| openpyxl | Excel file reading (.xlsx) |
| rapidfuzz | Fuzzy matching for column mapping |
| fastapi | Web framework (REST API) |
| uvicorn | ASGI server |
| jinja2 | HTML templates |
| python-multipart | File upload support |

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Main page (index.html) |
| GET | `/api/bands` | List bands with colors, radii and beamwidths |
| POST | `/api/upload` | Upload CSV/TXT/XLSX file |
| POST | `/api/auto-map` | Automatic column mapping |
| POST | `/api/validate-mapping` | Mapping validation |
| POST | `/api/set-config` | Apply configuration (mapping, labels, scale) |
| GET | `/api/map-data` | Map data (cells, sites, labels) |
| POST | `/api/generate-kml` | Generate and download KML file |
| POST | `/api/export-report` | Generate and download TXT report |
| POST | `/api/calculate-distance` | Calculate distance between two points |
| GET | `/api/search?q=&mode=` | Search sites or cities |
| POST | `/api/filter-values` | Unique column values for filters |
| POST | `/api/apply-filters` | Apply regional filters |
| GET | `/api/profiles` | List saved profiles |
| POST | `/api/save-profile` | Save configuration profile |
| POST | `/api/load-profile` | Load configuration profile |

---

## License

MIT License

## Author

Developed to assist RF engineers in visualizing cellular network data.
