import datetime
import xml.etree.ElementTree as ET

from .earfcn_utils import calculate_petal_radius, calculate_beamwidth, get_band_info
from .geometry import generate_petal
from .label_configurator import build_label
from .config import BAND_COLORS, DEFAULT_BEAMWIDTH


def _kml_color(hex_rgb, alpha="ff"):
    # Input hex_rgb is RRGGBB, output is AABBGGRR
    rr = hex_rgb[0:2]
    gg = hex_rgb[2:4]
    bb = hex_rgb[4:6]
    return "%s%s%s%s" % (alpha, bb, gg, rr)


def _add_style(parent, style_id, poly_color, line_color=None, label_color=None, label_scale=None, hide_icon=False):
    style = ET.SubElement(parent, "Style", id=style_id)
    if poly_color:
        polystyle = ET.SubElement(style, "PolyStyle")
        ET.SubElement(polystyle, "color").text = poly_color
    if line_color:
        linestyle = ET.SubElement(style, "LineStyle")
        ET.SubElement(linestyle, "color").text = line_color
    if label_color or label_scale:
        labelstyle = ET.SubElement(style, "LabelStyle")
        if label_color:
            ET.SubElement(labelstyle, "color").text = label_color
        if label_scale:
            ET.SubElement(labelstyle, "scale").text = str(label_scale)
    if hide_icon:
        iconstyle = ET.SubElement(style, "IconStyle")
        ET.SubElement(iconstyle, "scale").text = "0"
    return style


def generate_kml(df, mapping, label_config, extra_fields, scale, band_scale_overrides, beamwidth_overrides=None):
    doc_name = "Cell Sites - %s" % datetime.date.today().isoformat()
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, "Document")
    ET.SubElement(document, "name").text = doc_name

    label_color = _kml_color(label_config.text_color, alpha="ff")
    _add_style(
        document,
        "label_site",
        None,
        label_color=label_color,
        label_scale=label_config.text_scale if label_config.show_label else 0.0,
        hide_icon=True,
    )

    for key, color in BAND_COLORS.items():
        _add_style(document, "band_%s" % key, color, line_color=color, hide_icon=True)

    folders = {}
    for _, row in df.iterrows():
        lat = row.get(mapping["latitude"], "")
        lon = row.get(mapping["longitude"], "")
        if lat == "" or lon == "":
            continue
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            continue

        earfcn = row.get(mapping.get("earfcn", ""), "")
        band_info = get_band_info(earfcn)
        if band_info:
            folder_name = band_info["label"]
            band_key = band_info["key"]
        else:
            folder_name = "Unknown Band"
            band_key = "2600"

        if folder_name not in folders:
            folders[folder_name] = ET.SubElement(document, "Folder")
            ET.SubElement(folders[folder_name], "name").text = folder_name

        folder = folders[folder_name]

        site_label = build_label(row, mapping.get("site_name", ""), label_config.template)
        if site_label:
            pm_site = ET.SubElement(folder, "Placemark")
            ET.SubElement(pm_site, "name").text = site_label
            ET.SubElement(pm_site, "styleUrl").text = "#label_site"
            point = ET.SubElement(pm_site, "Point")
            ET.SubElement(point, "coordinates").text = "%s,%s,0" % (lon_f, lat_f)

        if label_config.hide_cell_label:
            cell_label = ""
        else:
            field = mapping.get("cell_name", "")
            if label_config.use_site_for_cell:
                field = mapping.get("site_name", "")
            cell_label = build_label(row, field, "")

        az = row.get(mapping.get("azimuth", ""), "0")
        try:
            az_f = float(az)
        except ValueError:
            az_f = 0.0

        # Get beamwidth from mapped column or calculate based on band
        beam = row.get(mapping.get("beamwidth", ""), "")
        try:
            beam_f = float(beam)
        except ValueError:
            # Use band-specific beamwidth if no column mapped
            beam_f = calculate_beamwidth(earfcn, beamwidth_overrides)

        radius = calculate_petal_radius(earfcn, scale, band_scale_overrides)
        coords = generate_petal(lat_f, lon_f, az_f, beam_f, radius)

        pm_cell = ET.SubElement(folder, "Placemark")
        ET.SubElement(pm_cell, "name").text = cell_label
        ET.SubElement(pm_cell, "styleUrl").text = "#band_%s" % band_key
        desc = ET.SubElement(pm_cell, "description")

        # Format description as "Field = Value" - one per line
        site_val = row.get(mapping.get("site_name", ""), "")
        cell_val = row.get(mapping.get("cell_name", ""), "")
        lat_val = row.get(mapping.get("latitude", ""), "")
        lon_val = row.get(mapping.get("longitude", ""), "")

        lines = [
            "Site = %s" % site_val,
            "Sector = %s" % cell_val,
            "Longitude = %s" % lon_val,
            "Latitude = %s" % lat_val,
            "Azimuth = %s" % az,
            "EARFCN = %s" % earfcn,
            "Band = %s" % (band_info["label"] if band_info else "Unknown"),
        ]
        for field in extra_fields:
            lines.append("%s = %s" % (field, row.get(field, "")))
        desc.text = "\n".join(lines)

        polygon = ET.SubElement(pm_cell, "Polygon")
        outer = ET.SubElement(polygon, "outerBoundaryIs")
        ring = ET.SubElement(outer, "LinearRing")
        coord_text = "\n".join(["%s,%s,0" % (c[0], c[1]) for c in coords])
        ET.SubElement(ring, "coordinates").text = coord_text

    raw = ET.tostring(kml, encoding="utf-8", xml_declaration=True).decode("utf-8")
    raw = raw.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
    return raw.encode("utf-8")
