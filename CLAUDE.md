# MoB_KML - Cell KML Generator (Web Edition)

Ferramenta web para engenheiros de RF. Converte dados de inventario celular (LTE/5G)
em visualizacao interativa no mapa (Leaflet.js) e exportacao KML.

## Stack

- **Backend**: FastAPI (app/main.py) com endpoints REST
- **Frontend**: HTML (Jinja2) + Leaflet.js + Bootstrap 5 + vanilla JS
- **Core**: cell_kml_generator/ (pandas, rapidfuzz, openpyxl)
- **Build**: Nuitka -> exe standalone Windows (~36MB)
- **Python**: 3.9 (venv em ./venv)

## Estrutura principal

```
app/
  __init__.py          # OBRIGATORIO - sem ele o Nuitka nao detecta o pacote
  main.py              # FastAPI server, todos os endpoints REST

cell_kml_generator/    # Modulo core de processamento
  config.py            # BAND_COLORS, BAND_RADIUS_M, BAND_BEAMWIDTH, BAND_RANGES
  file_handler.py      # load_file() - CSV/TXT/XLSX com auto-deteccao delimitador
  column_mapper.py     # auto_map_columns() - fuzzy matching com rapidfuzz
  validators.py        # Validacao de coords, azimute, EARFCN
  earfcn_utils.py      # EARFCN -> Banda, calculo de raio/beamwidth
  geometry.py          # Haversine, generate_petal(), destination_point()
  kml_generator.py     # generate_kml() -> bytes KML
  label_configurator.py # LabelConfig dataclass
  main.py              # GUI Tkinter LEGADO (nao usado na web edition)

templates/index.html   # UI principal
static/css/style.css   # Tema escuro, layout flexbox
static/js/app.js       # Frontend: mapa, resize, search, measure, live mode
profiles/              # Perfis de config (.json), criado em runtime
```

## Como executar

```bash
# Desenvolvimento
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Executavel compilado
.\dist\MoB_KML.exe
```

## Como compilar (.exe)

```powershell
.\build_nuitka.ps1
```

### Gotchas criticos do build Nuitka

1. **app/__init__.py DEVE existir** - sem ele: "No module named 'app'"
2. **launcher.py deve importar app.main DIRETAMENTE** (`from app.main import app as fastapi_app`), NAO como string (`"app.main:app"`) - Nuitka nao resolve strings de importacao dinamica
3. **Usar `python -m pip`** (nao `pip` sozinho) - o pip avulso pode instalar no venv errado
4. **Modulos dinamicos do uvicorn** precisam de --include-package explicito: uvicorn.protocols, uvicorn.lifespan, uvicorn.loops, anyio, starlette, multipart
5. **PowerShell Out-File adiciona BOM** - usar [System.IO.File]::WriteAllText com UTF8Encoding($false)
6. **--windows-console-mode=force** esta ativo para debug. Trocar para `disable` e recompilar para producao

## Caminhos no exe

app/main.py calcula `APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (dois niveis acima). Funciona tanto em dev quanto no exe porque Nuitka mantem estrutura relativa dos --include-data-dir.

## API Endpoints principais

- POST `/api/upload` - upload arquivo CSV/TXT/XLSX
- POST `/api/auto-map` - mapeamento automatico de colunas
- POST `/api/set-config` - aplica config (mapping, labels, escala)
- GET `/api/map-data` - dados do mapa (celulas, sites, labels)
- POST `/api/generate-kml` - gera KML
- GET `/api/search?q=&mode=` - busca sites/cidades
- POST `/api/filter-values` / `/api/apply-filters` - filtros regionais
- GET/POST `/api/profiles`, `/api/save-profile`, `/api/load-profile`

## Documentacao detalhada

Ver `PROJETO_INFO.txt` para: pipeline de processamento completo, problemas de build resolvidos, funcoes do frontend, bandas suportadas com EARFCN ranges.
