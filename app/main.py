from __future__ import annotations

import datetime
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cell_kml_generator import column_mapper, config, earfcn_utils, file_handler, geometry, kml_generator, validators
from cell_kml_generator.label_configurator import LabelConfig, build_label

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(APP_ROOT, "profiles")

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(APP_ROOT, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(APP_ROOT, "templates"))


CURRENT: Dict[str, Any] = {
    "df_full": None,
    "df": None,
    "meta": {},
    "mapping": {},
    "label_config": LabelConfig(),
    "extra_fields": [],
    "scale": 0.5,
    "band_scale_overrides": {},
    "beamwidth_overrides": {},
    "source_name": "",
    "filter_columns": {},
}


def _require_df() -> pd.DataFrame:
    df = CURRENT.get("df")
    if df is None:
        raise HTTPException(status_code=400, detail="No data loaded. Upload a file first.")
    return df


def _normalize_col(name: str) -> str:
    return name.lower().replace("_", "").replace(" ", "").replace("-", "")


def detect_filter_columns(columns: List[str]) -> Dict[str, str]:
    """Detect columns for common regional filters (UF/State, CN/Area Code, Regional, City)."""
    candidates = {
        "uf": ["uf", "estado", "state"],
        "cn": ["cn", "ddd"],
        "regional": ["regional", "region", "regiao", "região"],
        "municipio": ["municipio", "cidade", "city", "muni", "municipality"],
    }

    normalized = {_normalize_col(col): col for col in columns}
    mapping = {}
    for key, keywords in candidates.items():
        found = None
        for col_norm, original in normalized.items():
            # Prefer exact/whole matches to avoid false positives (e.g., earfcndl)
            if col_norm in keywords:
                found = original
                break
        if not found:
            for col_norm, original in normalized.items():
                for k in keywords:
                    if k == "state" and len(col_norm) > 6:
                        continue
                    if col_norm.startswith(k) or col_norm.endswith(k):
                        found = original
                        break
                if found:
                    break
        if found:
            mapping[key] = found
    return mapping


def _kml_color_to_hex(kml_color: str) -> str:
    # Input AABBGGRR, output #RRGGBB
    if not kml_color or len(kml_color) != 8:
        return "#888888"
    bb = kml_color[2:4]
    gg = kml_color[4:6]
    rr = kml_color[6:8]
    return f"#{rr}{gg}{bb}"


def _get_band_color_hex(band_key: str) -> str:
    kml_color = config.BAND_COLORS.get(band_key, "aa00ff00")
    return _kml_color_to_hex(kml_color)


def _build_popup_html(row: pd.Series, mapping: Dict[str, str], extra_fields: List[str]) -> str:
    site_val = row.get(mapping.get("site_name", ""), "")
    cell_val = row.get(mapping.get("cell_name", ""), "")
    lat_val = row.get(mapping.get("latitude", ""), "")
    lon_val = row.get(mapping.get("longitude", ""), "")
    earfcn_val = row.get(mapping.get("earfcn", ""), "")
    az_val = row.get(mapping.get("azimuth", ""), "")

    band_info = earfcn_utils.get_band_info(earfcn_val)
    band_label = band_info["label"] if band_info else "Unknown"

    lines = [
        f"<b>Site:</b> {site_val}",
        f"<b>Sector:</b> {cell_val}",
        f"<b>Longitude:</b> {lon_val}",
        f"<b>Latitude:</b> {lat_val}",
        f"<b>Azimuth:</b> {az_val}",
        f"<b>EARFCN:</b> {earfcn_val}",
        f"<b>Band:</b> {band_label}",
    ]
    for field in extra_fields:
        lines.append(f"<b>{field}:</b> {row.get(field, '')}")
    return "<br/>".join(lines)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/bands")
async def get_bands():
    bands = []
    for info in config.BAND_RANGES:
        key = info["key"]
        bands.append(
            {
                "key": key,
                "band": info["band"],
                "label": info["label"],
                "freq_mhz": info["freq_mhz"],
                "default_radius": config.BAND_RADIUS_M.get(key, 300),
                "default_beamwidth": config.BAND_BEAMWIDTH.get(key, config.DEFAULT_BEAMWIDTH),
                "color": _get_band_color_hex(key),
            }
        )
    return {"bands": bands}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename.")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df, meta = file_handler.load_file(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    filter_columns = detect_filter_columns(list(df.columns))
    CURRENT["df"] = df
    CURRENT["df_full"] = df.copy()
    CURRENT["meta"] = meta
    CURRENT["source_name"] = file.filename
    CURRENT["filter_columns"] = filter_columns

    preview = df.head(config.PREVIEW_ROWS).to_dict(orient="records")
    return {
        "columns": list(df.columns),
        "preview": preview,
        "total_rows": len(df),
        "meta": meta,
        "source_name": file.filename,
        "filter_columns": filter_columns,
    }


@app.post("/api/auto-map")
async def auto_map():
    df = _require_df()
    mapping = column_mapper.auto_map_columns(df)
    issues = column_mapper.validate_mapping(df, mapping)
    CURRENT["mapping"] = mapping
    return {"mapping": mapping, "issues": issues}


@app.post("/api/validate-mapping")
async def validate_mapping(payload: Dict[str, Any] = Body(...)):
    df = _require_df()
    mapping = payload.get("mapping", {})

    issues = column_mapper.validate_mapping(df, mapping)

    lat_col = mapping.get("latitude")
    lon_col = mapping.get("longitude")
    site_col = mapping.get("site_name")
    az_col = mapping.get("azimuth")
    earfcn_col = mapping.get("earfcn")
    label_col = payload.get("label_field")

    if lat_col and lon_col:
        issues.extend(validators.find_duplicate_coords(df, lat_col, lon_col, site_col))
    if az_col:
        issues.extend(validators.find_invalid_azimuth(df, az_col))
    if earfcn_col:
        issues.extend(validators.find_missing_earfcn(df, earfcn_col))
    if label_col:
        issues.extend(validators.find_empty_labels(df, label_col))

    return {"issues": issues}


@app.post("/api/set-config")
async def set_config(payload: Dict[str, Any] = Body(...)):
    mapping = payload.get("mapping", {})
    label_conf = payload.get("label_config", {})

    CURRENT["mapping"] = mapping
    CURRENT["label_config"] = LabelConfig(
        site_field=label_conf.get("site_field", ""),
        cell_field=label_conf.get("cell_field", ""),
        use_site_for_cell=bool(label_conf.get("use_site_for_cell", False)),
        hide_cell_label=bool(label_conf.get("hide_cell_label", False)),
        show_label=bool(label_conf.get("show_label", True)),
        text_scale=float(label_conf.get("text_scale", 1.0)),
        text_color=str(label_conf.get("text_color", "ffffff")).lstrip("#"),
        shadow=bool(label_conf.get("shadow", False)),
        position=str(label_conf.get("position", "center")),
        template=str(label_conf.get("template", "")),
    )
    CURRENT["extra_fields"] = payload.get("extra_fields", [])
    CURRENT["scale"] = float(payload.get("scale", 1.0))
    CURRENT["band_scale_overrides"] = payload.get("band_scale_overrides", {})
    CURRENT["beamwidth_overrides"] = payload.get("beamwidth_overrides", {})
    return {"ok": True}


@app.post("/api/filter-values")
async def filter_values(payload: Dict[str, Any] = Body(...)):
    df_full = CURRENT.get("df_full")
    if df_full is None:
        raise HTTPException(status_code=400, detail="No data loaded.")
    column = payload.get("column")
    if not column or column not in df_full.columns:
        raise HTTPException(status_code=400, detail="Invalid column.")
    filters = payload.get("filters", {})

    df = df_full.copy()
    for col, values in filters.items():
        if col == column:
            continue
        if col not in df.columns:
            continue
        if not values:
            continue
        df = df[df[col].astype(str).isin([str(v) for v in values])]

    values = df[column].fillna("").astype(str)
    unique_vals = sorted({v.strip() for v in values if v.strip() != ""})
    return {"values": unique_vals[:2000]}


@app.post("/api/apply-filters")
async def apply_filters(payload: Dict[str, Any] = Body(...)):
    df_full = CURRENT.get("df_full")
    if df_full is None:
        raise HTTPException(status_code=400, detail="No data loaded.")
    filters = payload.get("filters", {})
    df = df_full.copy()
    for col, values in filters.items():
        if col not in df.columns:
            continue
        if not values:
            continue
        df = df[df[col].astype(str).isin([str(v) for v in values])]

    CURRENT["df"] = df
    preview = df.head(config.PREVIEW_ROWS).to_dict(orient="records")
    return {"total_rows": len(df), "preview": preview}


@app.get("/api/search")
async def search_sites(q: str, mode: str = "site"):
    df = _require_df()
    mapping = CURRENT.get("mapping", {})
    label_config: LabelConfig = CURRENT.get("label_config")
    filter_columns = CURRENT.get("filter_columns", {})

    lat_field = mapping.get("latitude", "")
    lon_field = mapping.get("longitude", "")
    if not lat_field or not lon_field:
        auto_mapping = column_mapper.auto_map_columns(df)
        lat_field = lat_field or auto_mapping.get("latitude", "")
        lon_field = lon_field or auto_mapping.get("longitude", "")
    if not lat_field or not lon_field:
        return []

    query = q.strip().lower()
    if len(query) < 2:
        return []

    if mode == "city":
        city_col = filter_columns.get("municipio") or detect_filter_columns(list(df.columns)).get("municipio")
        if not city_col:
            return []
        df_city = df[[city_col, lat_field, lon_field]].copy()
        df_city = df_city.dropna()
        df_city[city_col] = df_city[city_col].astype(str)
        df_city = df_city[df_city[city_col].str.lower().str.contains(query, na=False)]
        if df_city.empty:
            return []

        grouped = df_city.groupby(city_col)
        results = []
        for name, group in grouped:
            try:
                lat_mean = group[lat_field].astype(float).mean()
                lon_mean = group[lon_field].astype(float).mean()
            except ValueError:
                continue
            results.append(
                {
                    "label": name,
                    "count": int(len(group)),
                    "lat": float(lat_mean),
                    "lon": float(lon_mean),
                    "kind": "city",
                }
            )
            if len(results) >= 50:
                break
        return results

    site_field = label_config.site_field or mapping.get("site_name", "")
    cell_field = mapping.get("cell_name", "")
    if not site_field:
        auto_mapping = column_mapper.auto_map_columns(df)
        site_field = auto_mapping.get("site_name", "")
        cell_field = cell_field or auto_mapping.get("cell_name", "")
    if not site_field:
        return []

    results = []
    seen = set()

    for _, row in df.iterrows():
        site_val = str(row.get(site_field, "")).strip()
        cell_val = str(row.get(cell_field, "")).strip() if cell_field else ""
        lat = row.get(lat_field, "")
        lon = row.get(lon_field, "")
        if site_val == "" or lat == "" or lon == "":
            continue
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            continue

        haystack = f"{site_val} {cell_val}".lower()
        if query not in haystack:
            continue

        key = f"{site_val}:{cell_val}"
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "site_name": site_val,
                "cell_name": cell_val,
                "lat": lat_f,
                "lon": lon_f,
                "kind": "site",
            }
        )
        if len(results) >= 50:
            break

    return results


@app.get("/api/map-data")
async def map_data():
    df = _require_df()
    mapping = CURRENT.get("mapping", {})
    label_config: LabelConfig = CURRENT.get("label_config")
    extra_fields = CURRENT.get("extra_fields", [])
    scale = CURRENT.get("scale", 1.0)
    band_scale_overrides = CURRENT.get("band_scale_overrides", {})
    beamwidth_overrides = CURRENT.get("beamwidth_overrides", {})

    if not mapping.get("latitude") or not mapping.get("longitude"):
        raise HTTPException(status_code=400, detail="Mapping must include latitude and longitude.")

    cells = []
    sites = {}

    for _, row in df.iterrows():
        lat = row.get(mapping.get("latitude"), "")
        lon = row.get(mapping.get("longitude"), "")
        if lat == "" or lon == "":
            continue
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            continue

        earfcn = row.get(mapping.get("earfcn", ""), "")
        band_info = earfcn_utils.get_band_info(earfcn)
        band_key = band_info["key"] if band_info else "2600"
        band_label = band_info["label"] if band_info else "Unknown"

        az = row.get(mapping.get("azimuth", ""), "0")
        try:
            az_f = float(az)
        except ValueError:
            az_f = 0.0

        beam = row.get(mapping.get("beamwidth", ""), "")
        try:
            beam_f = float(beam)
        except ValueError:
            beam_f = earfcn_utils.calculate_beamwidth(earfcn, beamwidth_overrides)

        radius = earfcn_utils.calculate_petal_radius(earfcn, scale, band_scale_overrides)
        coords = geometry.generate_petal(lat_f, lon_f, az_f, beam_f, radius)
        polygon = [[c[1], c[0]] for c in coords]

        site_label_field = label_config.site_field or mapping.get("site_name", "")
        site_label = build_label(row, site_label_field, label_config.template)

        cell_label = ""
        if not label_config.hide_cell_label:
            field = mapping.get("cell_name", "")
            if label_config.use_site_for_cell:
                field = mapping.get("site_name", "")
            cell_label = build_label(row, field, "")

        popup_html = _build_popup_html(row, mapping, extra_fields)

        cells.append(
            {
                "cell_name": row.get(mapping.get("cell_name", ""), ""),
                "site_name": row.get(mapping.get("site_name", ""), ""),
                "lat": lat_f,
                "lon": lon_f,
                "band_key": band_key,
                "band_label": band_label,
                "color": _get_band_color_hex(band_key),
                "polygon": polygon,
                "popup": popup_html,
                "cell_label": cell_label,
            }
        )

        if site_label:
            site_key = f"{site_label}:{lat_f}:{lon_f}"
            if site_key not in sites:
                sites[site_key] = {
                    "label": site_label,
                    "lat": lat_f,
                    "lon": lon_f,
                }

    return {
        "cells": cells,
        "sites": list(sites.values()),
        "label_config": {
            "show_label": label_config.show_label,
            "text_scale": label_config.text_scale,
            "text_color": f"#{label_config.text_color}",
            "shadow": label_config.shadow,
            "position": label_config.position,
        },
    }


@app.post("/api/generate-kml")
async def generate_kml_endpoint():
    df = _require_df()
    mapping = CURRENT.get("mapping", {})
    label_config: LabelConfig = CURRENT.get("label_config")
    extra_fields = CURRENT.get("extra_fields", [])
    scale = CURRENT.get("scale", 1.0)
    band_scale_overrides = CURRENT.get("band_scale_overrides", {})
    beamwidth_overrides = CURRENT.get("beamwidth_overrides", {})

    if not mapping:
        raise HTTPException(status_code=400, detail="Mapping not set.")

    kml_bytes = kml_generator.generate_kml(
        df,
        mapping,
        label_config,
        extra_fields,
        scale,
        band_scale_overrides,
        beamwidth_overrides,
    )

    filename = f"cell_sites_{datetime.date.today().isoformat()}.kml"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([kml_bytes]), media_type="application/vnd.google-earth.kml+xml", headers=headers)


@app.post("/api/export-report")
async def export_report():
    df = _require_df()
    mapping = CURRENT.get("mapping", {})

    lat_col = mapping.get("latitude")
    lon_col = mapping.get("longitude")
    site_col = mapping.get("site_name")
    cell_col = mapping.get("cell_name")
    earfcn_col = mapping.get("earfcn")

    total_cells = len(df)
    total_sites = len(set(df[site_col])) if site_col else 0

    band_counts: Dict[str, int] = {}
    if earfcn_col:
        for value in df[earfcn_col].tolist():
            band_info = earfcn_utils.get_band_info(value)
            label = band_info["label"] if band_info else "Unknown"
            band_counts[label] = band_counts.get(label, 0) + 1

    lines = [
        "MoB_KML - Report",
        f"Date: {datetime.date.today().isoformat()}",
        f"Source: {CURRENT.get('source_name', '')}",
        "",
        f"Total rows: {total_cells}",
        f"Total sites: {total_sites}",
        "",
        "Band distribution:",
    ]

    for band_label, count in sorted(band_counts.items()):
        lines.append(f"- {band_label}: {count}")

    content = "\n".join(lines).encode("utf-8")
    filename = f"report_{datetime.date.today().isoformat()}.txt"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([content]), media_type="text/plain", headers=headers)


@app.post("/api/calculate-distance")
async def calculate_distance(payload: Dict[str, Any] = Body(...)):
    """
    Calculate the distance between two geographic points.

    Payload:
    {
        "lat1": number,
        "lon1": number,
        "lat2": number,
        "lon2": number
    }
    """
    try:
        lat1 = float(payload.get("lat1"))
        lon1 = float(payload.get("lon1"))
        lat2 = float(payload.get("lat2"))
        lon2 = float(payload.get("lon2"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid coordinates. Must be numbers.")
    
    distance_m = geometry.haversine_distance(lat1, lon1, lat2, lon2)
    
    return {
        "distance_m": distance_m,
        "distance_km": distance_m / 1000,
        "distance_mi": distance_m / 1609.34
    }


@app.get("/api/profiles")
async def list_profiles():
    if not os.path.isdir(PROFILES_DIR):
        return {"profiles": []}
    profiles = [f for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
    return {"profiles": profiles}


@app.post("/api/save-profile")
async def save_profile(payload: Dict[str, Any] = Body(...)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Profile name is required.")
    os.makedirs(PROFILES_DIR, exist_ok=True)
    path = os.path.join(PROFILES_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload.get("data", {}), handle, indent=2)
    return {"ok": True}


@app.post("/api/load-profile")
async def load_profile(payload: Dict[str, Any] = Body(...)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Profile name is required.")
    path = os.path.join(PROFILES_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Profile not found.")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {"data": data}
