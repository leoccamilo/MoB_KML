def find_duplicate_coords(df, lat_col, lon_col, site_col=None):
    seen = {}
    warnings = []
    for idx, row in df.iterrows():
        lat = row.get(lat_col, "")
        lon = row.get(lon_col, "")
        if lat == "" or lon == "":
            continue
        key = (lat, lon)
        site = row.get(site_col, "") if site_col else ""
        if key in seen and seen[key] != site:
            warnings.append("Duplicate coordinates with different sites at row %s." % idx)
        else:
            seen[key] = site
    return warnings


def find_invalid_azimuth(df, az_col):
    issues = []
    for idx, value in df[az_col].items():
        if value == "":
            continue
        try:
            az = float(value)
        except ValueError:
            issues.append("Invalid azimuth at row %s." % idx)
            continue
        if az < 0 or az > 360:
            issues.append("Azimuth out of range at row %s." % idx)
    return issues


def find_missing_earfcn(df, earfcn_col):
    missing = []
    for idx, value in df[earfcn_col].items():
        if value == "":
            missing.append("Missing EARFCN at row %s." % idx)
    return missing


def find_empty_labels(df, label_col):
    warnings = []
    for idx, value in df[label_col].items():
        if str(value).strip() == "":
            warnings.append("Empty label value at row %s." % idx)
    return warnings
