try:
    from rapidfuzz import fuzz
except Exception:  # noqa: E722
    fuzz = None

from difflib import SequenceMatcher


def _score(name, target):
    name = name.lower()
    target = target.lower()
    if fuzz:
        return fuzz.partial_ratio(name, target)
    return int(SequenceMatcher(None, name, target).ratio() * 100)


def _find_best(columns, keywords, exclude=None):
    """Find best matching column for given keywords.

    Args:
        columns: List of column names
        keywords: List of keywords to match (first keywords have priority)
        exclude: Set of column names to exclude from matching
    """
    if exclude is None:
        exclude = set()

    best = (None, 0)
    for col in columns:
        if col in exclude:
            continue
        col_lower = col.lower().replace("_", "").replace(" ", "").replace("-", "")

        # Exact match gets highest priority
        for key in keywords:
            key_clean = key.lower().replace("_", "").replace(" ", "").replace("-", "")
            if col_lower == key_clean:
                return col

        # Partial matching
        for idx, key in enumerate(keywords):
            score = _score(col, key)
            # Give bonus to earlier keywords (more specific)
            bonus = (len(keywords) - idx) * 5
            adjusted_score = score + bonus
            if adjusted_score > best[1]:
                best = (col, adjusted_score)

    return best[0] if best[1] > 60 else None


def _is_numeric_series(values):
    try:
        for value in values:
            if value == "" or value is None:
                continue
            float(value)
        return True
    except ValueError:
        return False


def auto_map_columns(df):
    columns = list(df.columns)
    used = set()

    # Map in order of importance, tracking used columns
    # Latitude - prioritize exact match, avoid "long" columns
    lat = _find_best(columns, ["latitude", "lat", "northing", "y"], exclude=used)
    if lat:
        used.add(lat)

    # Longitude - after latitude to avoid confusion
    lon = _find_best(columns, ["longitude", "long", "lon", "easting", "x"], exclude=used)
    if lon:
        used.add(lon)

    # Site name - prioritize SiteID, then eNB/gNB (exact match), then fuzzy match
    site = None
    for col in columns:
        col_lower = col.lower()
        if col_lower.replace("_", "").replace(" ", "").replace("-", "") in ["siteid"]:
            site = col
            break
    if not site:
        for col in columns:
            col_lower = col.lower()
            if col_lower in ["enb", "gnb", "enodeb", "gnodeb", "enb_id", "gnb_id"]:
                site = col
                break
    if not site:
        site = _find_best(
            columns,
            ["siteid", "site_id", "site id", "site_name", "sitename", "site", "node", "bts"],
            exclude=used,
        )
    if site:
        used.add(site)

    # Cell name
    cell = _find_best(columns, ["cellname", "cell_name", "cell", "sector", "sectorname", "celula", "eutrancell", "nrcell"], exclude=used)
    if cell:
        used.add(cell)

    # EARFCN - prioritize "earfcndl" and "dl_earfcn" over generic matches
    earfcn = _find_best(columns, ["earfcndl", "dl_earfcn", "earfcn_dl", "earfcn", "arfcn", "nrarfcn", "frequency_dl", "freq"], exclude=used)
    if earfcn:
        used.add(earfcn)

    # Azimuth
    azimuth = _find_best(columns, ["azimuth", "azim", "bearing", "direction", "heading", "orientation"], exclude=used)
    if azimuth:
        used.add(azimuth)

    # Beamwidth - only match specific beamwidth columns, avoid bandwidth columns
    beamwidth = _find_best(columns, ["beamwidth", "hbw", "horizontalbeamwidth", "beam_width", "h_beamwidth"], exclude=used)
    # Validate it's not a bandwidth column
    if beamwidth and "bandwidth" in beamwidth.lower():
        beamwidth = None

    mapping = {
        "latitude": lat,
        "longitude": lon,
        "site_name": site,
        "cell_name": cell,
        "earfcn": earfcn,
        "azimuth": azimuth,
        "beamwidth": beamwidth,
    }
    return mapping


def validate_mapping(df, mapping):
    issues = []
    lat_col = mapping.get("latitude")
    lon_col = mapping.get("longitude")
    if lat_col:
        sample = df[lat_col].head(50)
        if not _is_numeric_series(sample):
            issues.append("Latitude column does not look numeric.")
        else:
            for value in sample:
                if value == "":
                    continue
                try:
                    val = float(value)
                except ValueError:
                    continue
                if val < -90 or val > 90:
                    issues.append("Latitude values out of range (-90 to 90).")
                    break
    if lon_col:
        sample = df[lon_col].head(50)
        if not _is_numeric_series(sample):
            issues.append("Longitude column does not look numeric.")
        else:
            for value in sample:
                if value == "":
                    continue
                try:
                    val = float(value)
                except ValueError:
                    continue
                if val < -180 or val > 180:
                    issues.append("Longitude values out of range (-180 to 180).")
                    break
    earfcn_col = mapping.get("earfcn")
    if earfcn_col:
        sample = df[earfcn_col].head(50)
        if not _is_numeric_series(sample):
            issues.append("EARFCN column does not look numeric.")
    az_col = mapping.get("azimuth")
    if az_col:
        sample = df[az_col].head(50)
        if not _is_numeric_series(sample):
            issues.append("Azimuth column does not look numeric.")
    return issues
