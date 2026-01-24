from .config import BAND_RANGES, BAND_RADIUS_M, BAND_BEAMWIDTH, DEFAULT_BEAMWIDTH


def get_band_info(earfcn):
    if earfcn is None:
        return None
    try:
        value = int(earfcn)
    except (TypeError, ValueError):
        return None
    for info in BAND_RANGES:
        if info["min"] <= value <= info["max"]:
            return info
    return None


def calculate_petal_radius(earfcn, scale=1.0, band_scale_overrides=None):
    band_info = get_band_info(earfcn)
    if not band_info:
        return int(300 * scale)
    key = band_info["key"]
    base = BAND_RADIUS_M.get(key, 300)
    if band_scale_overrides and key in band_scale_overrides:
        base = band_scale_overrides[key]
    return int(base * scale)


def calculate_beamwidth(earfcn, beamwidth_overrides=None):
    """Calculate beamwidth based on band frequency.
    Lower frequencies have wider beamwidth for better coverage visualization.
    """
    band_info = get_band_info(earfcn)
    if not band_info:
        return DEFAULT_BEAMWIDTH
    key = band_info["key"]
    if beamwidth_overrides and key in beamwidth_overrides:
        return beamwidth_overrides[key]
    return BAND_BEAMWIDTH.get(key, DEFAULT_BEAMWIDTH)
