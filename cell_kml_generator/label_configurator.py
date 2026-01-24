from dataclasses import dataclass


@dataclass
class LabelConfig:
    site_field: str = ""
    cell_field: str = ""
    use_site_for_cell: bool = False
    hide_cell_label: bool = False
    show_label: bool = True
    text_scale: float = 1.0
    text_color: str = "ffffff"
    shadow: bool = False
    position: str = "center"
    template: str = ""


def build_label(row, field, template):
    if template:
        try:
            return template.format_map(row)
        except Exception:
            return ""
    if not field:
        return ""
    return str(row.get(field, ""))
