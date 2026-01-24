# Cell KML Generator

Ferramenta desktop para engenheiros de RF e telecomunicações que converte dados de inventário de rede celular em arquivos KML para visualização no Google Earth.

## Funcionalidades

- **Importacao de dados**: CSV, TXT (deteccao automatica de delimitador) e Excel (.xlsx, .xls)
- **Mapeamento automatico de colunas**: Latitude, Longitude, Azimute, EARFCN, eNB, Cell, etc.
- **Petalas direcionais**: Visualizacao de setores com abertura configuravel por banda de frequencia
- **Cores por banda**: Diferenciacao visual para bandas de 700MHz a 3700MHz (LTE/5G)
- **Estrutura hierarquica**: Organizacao Site -> Celulas no Google Earth
- **Labels configuraveis**: Personalizacao de textos e parametros exibidos
- **Relatorio**: Exportacao de resumo em TXT

## Bandas Suportadas

| Banda | Frequencia | Cor | Raio Padrao | Abertura Padrao |
|-------|------------|-----|-------------|-----------------|
| 28 | 700 MHz | Vermelho | 800m | 90° |
| 5 | 850 MHz | Laranja | 700m | 85° |
| 8 | 900 MHz | Amarelo | 650m | 80° |
| 3 | 1800 MHz | Verde | 400m | 65° |
| 1 | 2100 MHz | Azul | 350m | 65° |
| 7/38 | 2600 MHz | Magenta | 300m | 55° |
| 42/78 | 3500 MHz | Rosa | 220m | 50° |

## Instalacao

### Requisitos
- Python 3.8+
- Windows 10/11

### Setup
```bash
# Clonar repositorio
git clone https://github.com/SEU_USUARIO/MoB_KML.git
cd MoB_KML

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
# Executar aplicacao
python run.py
```

### Fluxo de trabalho

1. **Importar Dados**: Carregue arquivo CSV, TXT ou Excel com dados dos sites
2. **Mapeamento**: Verifique/ajuste o mapeamento automatico das colunas
3. **Petalas**: Configure raio e abertura por banda de frequencia
4. **Parametros**: Selecione campos extras para incluir na descricao
5. **Labels**: Configure como os labels aparecerao no Google Earth
6. **Gerar KML**: Exporte o arquivo KML e abra no Google Earth

## Estrutura do Projeto

```
MoB_KML/
├── cell_kml_generator/
│   ├── __init__.py
│   ├── main.py              # Interface grafica (Tkinter)
│   ├── config.py            # Configuracoes e constantes
│   ├── column_mapper.py     # Mapeamento automatico de colunas
│   ├── file_handler.py      # Leitura de arquivos
│   ├── geometry.py          # Calculo de petalas geodesicas
│   ├── kml_generator.py     # Geracao do arquivo KML
│   ├── label_configurator.py # Configuracao de labels
│   ├── earfcn_utils.py      # Utilitarios para EARFCN/bandas
│   └── validators.py        # Validacoes de dados
├── run.py                   # Ponto de entrada
├── requirements.txt         # Dependencias Python
└── README.md
```

## Dependencias

- pandas - Manipulacao de dados
- openpyxl - Leitura de arquivos Excel (.xlsx)
- xlrd - Leitura de arquivos Excel (.xls)
- rapidfuzz - Fuzzy matching para mapeamento de colunas

## Screenshots

*Em breve*

## Licenca

MIT License

## Autor

Desenvolvido para auxiliar engenheiros de RF na visualizacao de dados de rede celular.
