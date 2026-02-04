APP_NAME = "Cell KML Generator"
APP_VERSION = "1.0.0"

PREVIEW_ROWS = 10

# KML colors are AABBGGRR (alpha, blue, green, red)
BAND_COLORS = {
    "700": "aa0000ff",
    "850": "aa0088ff",
    "900": "aa00ccff",
    "1800": "aa00ff00",
    "2100": "aaff0000",
    "2600": "aaff00ff",
    "3500": "aaff00aa",
}

BAND_RADIUS_M = {
    "700": 500,
    "850": 700,
    "900": 650,
    "1800": 400,
    "2100": 350,
    "2600": 300,
    "2300": 320,
    "2500": 310,
    "3500": 220,
    "3700": 200,
}

BAND_RANGES = [
    {"band": "28", "label": "Band 28 (700MHz)", "min": 9210, "max": 9659, "freq_mhz": 700, "key": "700"},
    {"band": "5", "label": "Band 5 (850MHz)", "min": 2410, "max": 2649, "freq_mhz": 850, "key": "850"},
    {"band": "8", "label": "Band 8 (900MHz)", "min": 3450, "max": 3799, "freq_mhz": 900, "key": "900"},
    {"band": "3", "label": "Band 3 (1800MHz)", "min": 1200, "max": 1949, "freq_mhz": 1800, "key": "1800"},
    {"band": "1", "label": "Band 1 (2100MHz)", "min": 0, "max": 599, "freq_mhz": 2100, "key": "2100"},
    {"band": "7", "label": "Band 7 (2600MHz)", "min": 2750, "max": 3449, "freq_mhz": 2600, "key": "2600"},
    {"band": "38", "label": "Band 38 (2600MHz TDD)", "min": 37750, "max": 38249, "freq_mhz": 2600, "key": "2600"},
    {"band": "40", "label": "Band 40 (2300MHz TDD)", "min": 38650, "max": 39649, "freq_mhz": 2300, "key": "2300"},
    {"band": "41", "label": "Band 41 (2500MHz TDD)", "min": 39650, "max": 41589, "freq_mhz": 2500, "key": "2500"},
    {"band": "42", "label": "Band 42 (3500MHz)", "min": 41590, "max": 43589, "freq_mhz": 3500, "key": "3500"},
    {"band": "43", "label": "Band 43 (3700MHz)", "min": 43590, "max": 45589, "freq_mhz": 3700, "key": "3700"},
    # Simplified NR ARFCN range for n78
    {"band": "78", "label": "Band 78 (3500MHz 5G NR)", "min": 620000, "max": 680000, "freq_mhz": 3500, "key": "3500"},
]

# Beamwidth (abertura horizontal) por banda - frequências mais baixas = maior cobertura
BAND_BEAMWIDTH = {
    "700": 90,    # Frequência mais baixa, maior cobertura
    "850": 85,
    "900": 80,
    "1800": 65,
    "2100": 65,
    "2300": 60,
    "2500": 60,
    "2600": 55,
    "3500": 50,   # Frequência mais alta, menor cobertura
    "3700": 45,
}

DEFAULT_BEAMWIDTH = 65.0
DEFAULT_LABEL_COLOR = "ffffff"
DEFAULT_LABEL_SCALE = 1.0
