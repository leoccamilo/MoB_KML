# MoB_KML - Cell KML Generator (Web Edition)

Ferramenta web para engenheiros de RF que converte dados de inventario celular (LTE/5G)
em visualizacao interativa no mapa e exportacao KML, sem necessidade de Google Earth.

**Stack**: FastAPI + Leaflet.js + Pandas
**Status**: Produção - Compilado como .exe standalone
**Ultima atualizacao**: 03/02/2026

---

## Funcionalidades

- **Interface web moderna** com mapa interativo (Leaflet.js) - substitui Google Earth
- **Importacao de dados**: CSV, TXT (deteccao automatica de delimitador) e Excel (.xlsx)
- **Mapeamento automatico de colunas** com fuzzy matching (rapidfuzz)
- **Visualizacao em tempo real** (Live Mode) - mapa atualiza a cada mudanca de config
- **Petalas direcionais** por setor com abertura e raio configuraveis por banda
- **Cores por banda** de frequencia (700MHz a 3700MHz, LTE e 5G NR)
- **Paineis redimensionaveis** - arraste a barra entre config e mapa
- **Ferramenta de medicao** - clique em dois pontos para medir distancia
- **Busca de sites/cidades** na barra de pesquisa do mapa
- **Filtros regionais** - filtre por UF, DDD, Regional, Municipio
- **Perfis de configuracao** - salve e carregue configs em JSON
- **Exportacao KML** (opcional) e relatorio TXT
- **Dois base maps**: OpenStreetMap e Esri Satellite

## Bandas Suportadas

| Banda | Frequencia | EARFCN Range | Raio Padrao | Beamwidth |
|-------|------------|--------------|-------------|-----------|
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

## Executar (Desenvolvimento)

```bash
# Criar e ativar ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install -r requirements.txt

# Iniciar servidor
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Acesse: http://127.0.0.1:8000

## Executar (Executavel Compilado)

```
.\dist\MoB_KML.exe
```

O exe inicia o servidor FastAPI e abre o navegador automaticamente.
Nao requer Python instalado. Funciona em qualquer Windows 10/11 64-bit.

---

## Compilar o Executavel (.exe)

### Pre-requisitos
- Python 3.9+
- Visual Studio Build Tools (compilador C++)
- 8GB RAM (16GB recomendado)
- 10GB disco livre

### Compilar
```powershell
# Abra PowerShell e navegue ao projeto
cd C:\MoB_KML_bkp\MoB_KML_Ingles

# Execute o script de build
.\build_nuitka.ps1
```

O script automaticamente:
1. Ativa o venv e instala dependencias
2. Cria o `launcher.py` (entry point do exe)
3. Compila com Nuitka (~10-20 min)
4. Gera `.\dist\MoB_KML.exe` (~36MB)
5. Cria atalho na desktop

### Notas importantes sobre o build
- O `launcher.py` importa `app.main` **diretamente** (nao como string) para que o Nuitka detecte a dependencia
- O pacote `app/` precisa ter `__init__.py`
- Use `python -m pip` (nao `pip` sozinho) para garantir instalacao no venv correto
- O console esta visivel (`--windows-console-mode=force`) para debug. Apos confirmar que tudo funciona, mude para `--windows-console-mode=disable` no `build_nuitka.ps1`
- Se houver erro no exe, ele grava em `mob_kml_error.log` ao lado do executavel

---

## Fluxo de Uso

1. **Import Data** - Carregue CSV/TXT/XLSX
2. **Column Mapping** - Clique "Auto Map" (mapa aparece automaticamente com Live Mode)
3. **Petal Config** - Ajuste escala global e raios/beamwidth por banda
4. **Labels & View** - Configure rotulos dos sites
5. **Filters** - Filtre por UF, DDD, Regional, Municipio (se disponivel nos dados)
6. **Generate Output** - Download KML (opcional) ou Export Report

---

## Estrutura do Projeto

```
MoB_KML_Ingles/
|-- app/                           # Interface web (FastAPI)
|   |-- __init__.py
|   |-- main.py                    # Servidor FastAPI, endpoints REST
|
|-- cell_kml_generator/            # Modulo core de processamento
|   |-- __init__.py
|   |-- config.py                  # Constantes: cores, raios, beamwidths, EARFCN ranges
|   |-- file_handler.py            # Leitura de CSV/TXT/XLSX com auto-deteccao de delimitador
|   |-- column_mapper.py           # Mapeamento automatico de colunas (fuzzy matching)
|   |-- validators.py              # Validacao de dados (coords, azimute, EARFCN)
|   |-- earfcn_utils.py            # Conversao EARFCN -> Banda, calculo de raio/beamwidth
|   |-- geometry.py                # Calculo geodesico (haversine, petalas, bearing)
|   |-- kml_generator.py           # Geracao de arquivo KML
|   |-- label_configurator.py      # Configuracao de labels (LabelConfig dataclass)
|   |-- main.py                    # GUI Tkinter (legado, nao usado na web edition)
|
|-- templates/
|   |-- index.html                 # UI principal (Jinja2 template)
|
|-- static/
|   |-- css/style.css              # Estilos (tema escuro, layout flexbox)
|   |-- js/app.js                  # Logica frontend (Leaflet, resize, search, measure)
|
|-- profiles/                      # Perfis de configuracao salvos (.json)
|-- venv/                          # Ambiente virtual Python
|-- dist/                          # Executavel compilado
|   |-- MoB_KML.exe
|
|-- run.py                         # Entry point legado (Tkinter GUI)
|-- launcher.py                    # Entry point para o exe (FastAPI + browser)
|-- build_nuitka.ps1               # Script de compilacao Nuitka
|-- requirements.txt               # Dependencias Python
|-- mob.ico                        # Icone da aplicacao
|-- exemplo_teste.csv              # Arquivo de teste (13 setores, 6 sites)
|-- PROJETO_INFO.txt               # Documentacao tecnica detalhada
```

## Dependencias (requirements.txt)

| Pacote | Uso |
|--------|-----|
| pandas | Manipulacao de dados tabulares |
| openpyxl | Leitura de arquivos Excel (.xlsx) |
| rapidfuzz | Fuzzy matching para mapeamento de colunas |
| fastapi | Framework web (API REST) |
| uvicorn | Servidor ASGI |
| jinja2 | Templates HTML |
| python-multipart | Upload de arquivos |

## API Endpoints

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Pagina principal (index.html) |
| GET | `/api/bands` | Lista bandas com cores, raios e beamwidths |
| POST | `/api/upload` | Upload de arquivo CSV/TXT/XLSX |
| POST | `/api/auto-map` | Mapeamento automatico de colunas |
| POST | `/api/validate-mapping` | Validacao do mapeamento |
| POST | `/api/set-config` | Aplica configuracao (mapping, labels, escala) |
| GET | `/api/map-data` | Dados do mapa (celulas, sites, labels) |
| POST | `/api/generate-kml` | Gera e baixa arquivo KML |
| POST | `/api/export-report` | Gera e baixa relatorio TXT |
| POST | `/api/calculate-distance` | Calcula distancia entre dois pontos |
| GET | `/api/search?q=&mode=` | Busca sites ou cidades |
| POST | `/api/filter-values` | Valores unicos de coluna para filtros |
| POST | `/api/apply-filters` | Aplica filtros regionais |
| GET | `/api/profiles` | Lista perfis salvos |
| POST | `/api/save-profile` | Salva perfil de configuracao |
| POST | `/api/load-profile` | Carrega perfil de configuracao |

---

## Licenca

MIT License

## Autor

Desenvolvido para auxiliar engenheiros de RF na visualizacao de dados de rede celular.
