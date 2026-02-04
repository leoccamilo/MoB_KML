import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

import pandas as pd

from .config import APP_NAME, PREVIEW_ROWS, DEFAULT_LABEL_COLOR, BAND_RADIUS_M, BAND_BEAMWIDTH


def get_resource_path(filename):
    """Get path to resource, works for dev and compiled with Nuitka."""
    if getattr(sys, 'frozen', False):
        # Running as compiled (Nuitka onefile/on-dir)
        base_path = getattr(sys, "_MEIPASS", "")
        if not base_path:
            base_path = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, filename)
from .file_handler import load_file
from .column_mapper import auto_map_columns, validate_mapping
from .label_configurator import LabelConfig
from .validators import (
    find_duplicate_coords,
    find_invalid_azimuth,
    find_missing_earfcn,
    find_empty_labels,
)
from .earfcn_utils import get_band_info
from .kml_generator import generate_kml


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Set window icon
        icon_path = get_resource_path("mob.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Catppuccin Mocha colors
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.card_bg = "#313244"
        self.card_hover = "#45475a"
        self.success_color = "#a6e3a1"
        self.warning_color = "#f9e2af"
        self.error_color = "#f38ba8"
        self.subtext_color = "#7f849c"

        self.configure(bg=self.bg_color)

        self.df = None
        self.file_path = ""
        self.mapping = {}
        self.extra_fields = []
        self.band_overrides = {}
        self.beamwidth_overrides = {}
        self.label_config = LabelConfig()
        self.beamwidth_override_vars = {}
        self.last_dir = os.path.expanduser("~")
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configure notebook
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab",
            background=self.card_bg,
            foreground=self.fg_color,
            padding=[20, 10],
            font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
            background=[("selected", self.accent_color)],
            foreground=[("selected", self.bg_color)])

        # Configure frames
        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg)

        # Configure labels
        style.configure("TLabel",
            background=self.bg_color,
            foreground=self.fg_color,
            font=("Segoe UI", 10))
        style.configure("Title.TLabel",
            background=self.bg_color,
            foreground=self.accent_color,
            font=("Segoe UI", 14, "bold"))
        style.configure("Card.TLabel",
            background=self.card_bg,
            foreground=self.fg_color,
            font=("Segoe UI", 10))
        style.configure("Subtext.TLabel",
            background=self.bg_color,
            foreground=self.subtext_color,
            font=("Segoe UI", 9))

        # Configure buttons
        style.configure("TButton",
            background=self.card_bg,
            foreground=self.fg_color,
            font=("Segoe UI", 10),
            padding=[15, 8])
        style.map("TButton",
            background=[("active", self.card_hover)])

        style.configure("Accent.TButton",
            background=self.accent_color,
            foreground=self.bg_color,
            font=("Segoe UI", 11, "bold"),
            padding=[20, 10])
        style.map("Accent.TButton",
            background=[("active", "#74c7ec")])

        style.configure("Success.TButton",
            background=self.success_color,
            foreground=self.bg_color,
            font=("Segoe UI", 10, "bold"),
            padding=[15, 8])

        # Configure entry
        style.configure("TEntry",
            fieldbackground=self.card_bg,
            foreground=self.fg_color,
            insertcolor=self.fg_color,
            font=("Segoe UI", 10))

        # Configure combobox
        style.configure("TCombobox",
            fieldbackground=self.card_bg,
            background=self.card_bg,
            foreground=self.fg_color,
            font=("Segoe UI", 10))
        style.map("TCombobox",
            fieldbackground=[("readonly", self.card_bg)],
            selectbackground=[("readonly", self.accent_color)])

        # Configure checkbutton
        style.configure("TCheckbutton",
            background=self.bg_color,
            foreground=self.fg_color,
            font=("Segoe UI", 10))
        style.map("TCheckbutton",
            background=[("active", self.bg_color)])

        # Configure scale
        style.configure("TScale",
            background=self.bg_color,
            troughcolor=self.card_bg)

        # Configure progressbar
        style.configure("TProgressbar",
            background=self.accent_color,
            troughcolor=self.card_bg)

        # Configure scrollbar
        style.configure("TScrollbar",
            background=self.card_bg,
            troughcolor=self.bg_color)

        # Configure treeview
        style.configure("Treeview",
            background=self.card_bg,
            foreground=self.fg_color,
            fieldbackground=self.card_bg,
            font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
            background=self.card_hover,
            foreground=self.accent_color,
            font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
            background=[("selected", self.accent_color)],
            foreground=[("selected", self.bg_color)])

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.bg_color)
        header.pack(fill=tk.X, padx=20, pady=(15, 10))

        title = tk.Label(header,
            text="Cell KML Generator",
            font=("Segoe UI", 22, "bold"),
            bg=self.bg_color,
            fg=self.accent_color)
        title.pack(side=tk.TOP, anchor=tk.W)

        developer = tk.Label(header,
            text="Developed by Leonardo Camilo",
            font=("Segoe UI", 10, "italic"),
            bg=self.bg_color,
            fg=self.subtext_color)
        developer.pack(side=tk.TOP, anchor=tk.W, pady=(5, 0))

        # Separator
        sep = tk.Frame(self, height=2, bg=self.card_bg)
        sep.pack(fill=tk.X, padx=20, pady=(0, 10))

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.tab_import = ttk.Frame(self.notebook)
        self.tab_mapping = ttk.Frame(self.notebook)
        self.tab_petals = ttk.Frame(self.notebook)
        self.tab_params = ttk.Frame(self.notebook)
        self.tab_labels = ttk.Frame(self.notebook)
        self.tab_generate = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_import, text="  1. Import Data  ")
        self.notebook.add(self.tab_mapping, text="  2. Mapping  ")
        self.notebook.add(self.tab_petals, text="  3. Petals  ")
        self.notebook.add(self.tab_params, text="  4. Parameters  ")
        self.notebook.add(self.tab_labels, text="  5. Labels  ")
        self.notebook.add(self.tab_generate, text="  6. Generate KML  ")

        self._build_import_tab()
        self._build_mapping_tab()
        self._build_petals_tab()
        self._build_params_tab()
        self._build_labels_tab()
        self._build_generate_tab()

    def _build_import_tab(self):
        frame = tk.Frame(self.tab_import, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header section
        header = tk.Frame(frame, bg=self.bg_color)
        header.pack(fill=tk.X, pady=(0, 15))

        tk.Label(header,
            text="Import Data File",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(header,
            text="Supported formats: TXT, CSV, XLSX (automatic delimiter detection)",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 0))

        # File selection card
        file_card = tk.Frame(frame, bg=self.card_bg)
        file_card.pack(fill=tk.X, pady=(0, 15), ipady=15, ipadx=15)

        btn_frame = tk.Frame(file_card, bg=self.card_bg)
        btn_frame.pack(fill=tk.X, pady=(10, 5))

        select_btn = tk.Button(btn_frame,
            text="Select File",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_color,
            fg=self.bg_color,
            activebackground="#74c7ec",
            activeforeground=self.bg_color,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.on_load_file,
            padx=25,
            pady=10)
        select_btn.pack(side=tk.LEFT, padx=(5, 15))

        self.file_label = tk.Label(btn_frame,
            text="No file loaded",
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.subtext_color)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Preview section
        preview_header = tk.Frame(frame, bg=self.bg_color)
        preview_header.pack(fill=tk.X, pady=(10, 8))

        tk.Label(preview_header,
            text="Data preview",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_color,
            fg=self.fg_color).pack(side=tk.LEFT)

        self.preview_info = tk.Label(preview_header,
            text="(0 records)",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.subtext_color)
        self.preview_info.pack(side=tk.LEFT, padx=(10, 0))

        # Treeview container
        tree_frame = tk.Frame(frame, bg=self.card_bg)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_tree = ttk.Treeview(tree_frame, show="headings", height=14)
        yscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_mapping_tab(self):
        frame = tk.Frame(self.tab_mapping, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        tk.Label(frame,
            text="Column Mapping",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(frame,
            text="Mapping is done automatically. Adjust if needed.",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 15))

        # Mapping card
        card = tk.Frame(frame, bg=self.card_bg)
        card.pack(fill=tk.X, pady=(0, 15), ipadx=20, ipady=15)

        self.mapping_vars = {}
        self.mapping_combos = {}
        fields = [
            ("latitude", "Latitude", True),
            ("longitude", "Longitude", True),
            ("site_name", "Site Name", True),
            ("cell_name", "Cell Name", True),
            ("earfcn", "EARFCN DL", True),
            ("azimuth", "Azimuth", True),
            ("beamwidth", "Beamwidth", False),
        ]

        grid_frame = tk.Frame(card, bg=self.card_bg)
        grid_frame.pack(fill=tk.X, padx=15, pady=10)

        for idx, (key, label, required) in enumerate(fields):
            row_frame = tk.Frame(grid_frame, bg=self.card_bg)
            row_frame.pack(fill=tk.X, pady=5)

            label_text = label + (" *" if required else " (optional)")
            label_color = self.fg_color if required else self.subtext_color

            lbl = tk.Label(row_frame,
                text=label_text,
                font=("Segoe UI", 10, "bold" if required else "normal"),
                bg=self.card_bg,
                fg=label_color,
                width=20,
                anchor=tk.W)
            lbl.pack(side=tk.LEFT, padx=(0, 15))

            var = tk.StringVar()
            self.mapping_vars[key] = var
            combo = ttk.Combobox(row_frame, textvariable=var, width=45, state="readonly")
            combo["values"] = []
            combo.pack(side=tk.LEFT)
            self.mapping_combos[key] = combo

        # Status and validate button
        status_frame = tk.Frame(frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        validate_btn = tk.Button(status_frame,
            text="Validate Mapping",
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            activebackground=self.card_hover,
            activeforeground=self.fg_color,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.on_validate_mapping,
            padx=20,
            pady=8)
        validate_btn.pack(side=tk.LEFT)

        self.mapping_status = tk.Label(status_frame,
            text="",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.success_color)
        self.mapping_status.pack(side=tk.LEFT, padx=(15, 0))

    def _build_petals_tab(self):
        frame = tk.Frame(self.tab_petals, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        tk.Label(frame,
            text="Petal Configuration",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(frame,
            text="Configure radius and beamwidth per band",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 15))

        # Scale card
        scale_card = tk.Frame(frame, bg=self.card_bg)
        scale_card.pack(fill=tk.X, pady=(0, 15), ipadx=20, ipady=15)

        scale_inner = tk.Frame(scale_card, bg=self.card_bg)
        scale_inner.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(scale_inner,
            text="Global radius scale:",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.fg_color).pack(side=tk.LEFT)

        self.scale_var = tk.DoubleVar(value=0.5)
        self.scale_label = tk.Label(scale_inner,
            text=f"{self.scale_var.get():.1f}x",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.accent_color,
            width=5)
        self.scale_label.pack(side=tk.RIGHT, padx=(15, 0))

        scale = ttk.Scale(scale_inner, from_=0.1, to=2.0, variable=self.scale_var,
            command=lambda v: self.scale_label.config(text=f"{float(v):.1f}x"))
        scale.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=15)

        # Main content - scrollable area
        container = tk.Frame(frame, bg=self.bg_color)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.bg_color)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Bands configuration
        bands_card = tk.Frame(scrollable, bg=self.card_bg)
        bands_card.pack(fill=tk.X, pady=(0, 10), ipadx=15, ipady=10)

        # Header row
        header_frame = tk.Frame(bands_card, bg=self.card_bg)
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        tk.Label(header_frame, text="Band",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_color,
            width=22, anchor=tk.W).pack(side=tk.LEFT)

        tk.Label(header_frame, text="Radius (m)",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_color,
            width=12, anchor=tk.CENTER).pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(header_frame, text="Beamwidth (deg)",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_color,
            width=12, anchor=tk.CENTER).pack(side=tk.LEFT, padx=(10, 0))

        # Separator
        tk.Frame(bands_card, bg=self.card_hover, height=1).pack(fill=tk.X, padx=15, pady=5)

        self.band_override_vars = {}
        self.beamwidth_override_vars = {}

        bands = [
            ("700", "Band 28 (700 MHz)", BAND_RADIUS_M.get("700", 800), BAND_BEAMWIDTH.get("700", 90)),
            ("850", "Band 5 (850 MHz)", BAND_RADIUS_M.get("850", 700), BAND_BEAMWIDTH.get("850", 85)),
            ("900", "Band 8 (900 MHz)", BAND_RADIUS_M.get("900", 650), BAND_BEAMWIDTH.get("900", 80)),
            ("1800", "Band 3 (1800 MHz)", BAND_RADIUS_M.get("1800", 400), BAND_BEAMWIDTH.get("1800", 65)),
            ("2100", "Band 1 (2100 MHz)", BAND_RADIUS_M.get("2100", 350), BAND_BEAMWIDTH.get("2100", 65)),
            ("2300", "Band 40 (2300 MHz TDD)", BAND_RADIUS_M.get("2300", 320), BAND_BEAMWIDTH.get("2300", 60)),
            ("2500", "Band 41 (2500 MHz TDD)", BAND_RADIUS_M.get("2500", 310), BAND_BEAMWIDTH.get("2500", 60)),
            ("2600", "Band 7/38 (2600 MHz)", BAND_RADIUS_M.get("2600", 300), BAND_BEAMWIDTH.get("2600", 55)),
            ("3500", "Band 42/78 (3500 MHz)", BAND_RADIUS_M.get("3500", 220), BAND_BEAMWIDTH.get("3500", 50)),
            ("3700", "Band 43 (3700 MHz)", BAND_RADIUS_M.get("3700", 200), BAND_BEAMWIDTH.get("3700", 45)),
        ]

        for key, label, default_radius, default_beam in bands:
            row = tk.Frame(bands_card, bg=self.card_bg)
            row.pack(fill=tk.X, padx=15, pady=4)

            tk.Label(row, text=label,
                font=("Segoe UI", 10), bg=self.card_bg, fg=self.fg_color,
                width=22, anchor=tk.W).pack(side=tk.LEFT)

            # Radius entry
            radius_var = tk.StringVar(value=str(default_radius))
            self.band_override_vars[key] = radius_var

            radius_entry = tk.Entry(row, textvariable=radius_var,
                font=("Segoe UI", 10), bg=self.bg_color, fg=self.fg_color,
                insertbackground=self.fg_color, relief=tk.FLAT, width=8, justify=tk.CENTER)
            radius_entry.pack(side=tk.LEFT, padx=(10, 0))

            tk.Label(row, text="m", font=("Segoe UI", 9),
                bg=self.card_bg, fg=self.subtext_color, width=3).pack(side=tk.LEFT)

            # Beamwidth entry
            beam_var = tk.StringVar(value=str(default_beam))
            self.beamwidth_override_vars[key] = beam_var

            beam_entry = tk.Entry(row, textvariable=beam_var,
                font=("Segoe UI", 10), bg=self.bg_color, fg=self.fg_color,
                insertbackground=self.fg_color, relief=tk.FLAT, width=8, justify=tk.CENTER)
            beam_entry.pack(side=tk.LEFT, padx=(10, 0))

            tk.Label(row, text="deg", font=("Segoe UI", 9),
                bg=self.card_bg, fg=self.subtext_color, width=3).pack(side=tk.LEFT)

        # Info note
        note_frame = tk.Frame(scrollable, bg=self.bg_color)
        note_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Label(note_frame,
            text="Note: Lower frequencies (700-900 MHz) have greater coverage and beamwidth.",
            font=("Segoe UI", 9), bg=self.bg_color, fg=self.subtext_color).pack(anchor=tk.W)

        tk.Label(note_frame,
            text="Beamwidth defines the sector angle relative to the azimuth.",
            font=("Segoe UI", 9), bg=self.bg_color, fg=self.subtext_color).pack(anchor=tk.W)

    def _build_params_tab(self):
        frame = tk.Frame(self.tab_params, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        tk.Label(frame,
            text="Additional Parameters",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(frame,
            text="Select extra columns to include in the KML description",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 15))

        # Buttons
        buttons = tk.Frame(frame, bg=self.bg_color)
        buttons.pack(fill=tk.X, pady=(0, 10))

        sel_btn = tk.Button(buttons,
            text="Select All",
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            activebackground=self.card_hover,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self._toggle_all_params(True),
            padx=15,
            pady=6)
        sel_btn.pack(side=tk.LEFT)

        clr_btn = tk.Button(buttons,
            text="Clear Selection",
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            activebackground=self.card_hover,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self._toggle_all_params(False),
            padx=15,
            pady=6)
        clr_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Scrollable list
        list_frame = tk.Frame(frame, bg=self.card_bg)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.params_canvas = tk.Canvas(list_frame, bg=self.card_bg, highlightthickness=0)
        self.params_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.params_canvas.yview)
        self.params_canvas.configure(yscrollcommand=self.params_scroll.set)
        self.params_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.params_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.params_frame = tk.Frame(self.params_canvas, bg=self.card_bg)
        self.params_canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        self.params_frame.bind("<Configure>", lambda e: self.params_canvas.configure(scrollregion=self.params_canvas.bbox("all")))

        # Mouse wheel scroll
        def _on_mousewheel(event):
            self.params_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.params_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.param_vars = {}

    def _build_labels_tab(self):
        frame = tk.Frame(self.tab_labels, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        tk.Label(frame,
            text="Labels and Visualization",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(frame,
            text="Configure how labels appear in Google Earth",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 15))

        self.site_label_var = tk.StringVar()
        self.cell_label_var = tk.StringVar()
        self.use_site_for_cell_var = tk.BooleanVar(value=False)
        self.hide_cell_label_var = tk.BooleanVar(value=False)
        self.show_label_var = tk.BooleanVar(value=True)
        self.label_scale_var = tk.DoubleVar(value=1.0)
        self.label_color_var = tk.StringVar(value=DEFAULT_LABEL_COLOR)
        self.shadow_var = tk.BooleanVar(value=False)
        self.position_var = tk.StringVar(value="center")
        self.template_var = tk.StringVar()

        # Main content - two columns
        content = tk.Frame(frame, bg=self.bg_color)
        content.pack(fill=tk.BOTH, expand=True)

        # Left column - Label fields
        left = tk.Frame(content, bg=self.bg_color)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        # Site label field
        card1 = tk.Frame(left, bg=self.card_bg)
        card1.pack(fill=tk.X, pady=(0, 10), ipadx=15, ipady=12)

        tk.Label(card1, text="Field for Site Label",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(8, 5))

        self.site_label_combo = ttk.Combobox(card1, textvariable=self.site_label_var, state="readonly", width=35)
        self.site_label_combo.pack(anchor=tk.W, padx=10, pady=(0, 8))

        # Cell label field
        card2 = tk.Frame(left, bg=self.card_bg)
        card2.pack(fill=tk.X, pady=(0, 10), ipadx=15, ipady=12)

        tk.Label(card2, text="Field for Cell Label",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(8, 5))

        self.cell_label_combo = ttk.Combobox(card2, textvariable=self.cell_label_var, state="readonly", width=35)
        self.cell_label_combo.pack(anchor=tk.W, padx=10, pady=(0, 5))

        checks = tk.Frame(card2, bg=self.card_bg)
        checks.pack(anchor=tk.W, padx=10, pady=(0, 8))

        tk.Checkbutton(checks, text="Use same field as Site",
            variable=self.use_site_for_cell_var,
            font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_color,
            selectcolor=self.bg_color, activebackground=self.card_bg).pack(side=tk.LEFT)

        tk.Checkbutton(checks, text="Do not show labels on cells",
            variable=self.hide_cell_label_var,
            font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_color,
            selectcolor=self.bg_color, activebackground=self.card_bg).pack(side=tk.LEFT, padx=(15, 0))

        # Template
        card3 = tk.Frame(left, bg=self.card_bg)
        card3.pack(fill=tk.X, pady=(0, 10), ipadx=15, ipady=12)

        tk.Label(card3, text="Custom template (optional)",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(8, 3))

        tk.Label(card3, text="Use {column_name} to insert values. Ex: {sitename} - {cellname}",
            font=("Segoe UI", 8), bg=self.card_bg, fg=self.subtext_color).pack(anchor=tk.W, padx=10, pady=(0, 5))

        template_entry = tk.Entry(card3, textvariable=self.template_var,
            font=("Segoe UI", 10), bg=self.bg_color, fg=self.fg_color,
            insertbackground=self.fg_color, relief=tk.FLAT, width=45)
        template_entry.pack(anchor=tk.W, padx=10, pady=(0, 8))

        # Right column - Style options
        right = tk.Frame(content, bg=self.bg_color)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Style card
        card4 = tk.Frame(right, bg=self.card_bg)
        card4.pack(fill=tk.X, pady=(0, 10), ipadx=15, ipady=12)

        tk.Label(card4, text="Text Style",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(8, 10))

        style_row = tk.Frame(card4, bg=self.card_bg)
        style_row.pack(fill=tk.X, padx=10, pady=3)

        tk.Checkbutton(style_row, text="Show label permanently",
            variable=self.show_label_var,
            font=("Segoe UI", 10), bg=self.card_bg, fg=self.fg_color,
            selectcolor=self.bg_color, activebackground=self.card_bg).pack(side=tk.LEFT)

        # Scale row
        scale_row = tk.Frame(card4, bg=self.card_bg)
        scale_row.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(scale_row, text="Size:",
            font=("Segoe UI", 10), bg=self.card_bg, fg=self.fg_color).pack(side=tk.LEFT)

        self.label_scale_display = tk.Label(scale_row, text="1.0x",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_color, width=4)
        self.label_scale_display.pack(side=tk.RIGHT)

        label_scale = ttk.Scale(scale_row, from_=0.5, to=2.0, variable=self.label_scale_var,
            command=lambda v: self.label_scale_display.config(text=f"{float(v):.1f}x"))
        label_scale.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        # Color row
        color_row = tk.Frame(card4, bg=self.card_bg)
        color_row.pack(fill=tk.X, padx=10, pady=8)

        color_btn = tk.Button(color_row, text="Text Color",
            font=("Segoe UI", 10), bg=self.accent_color, fg=self.bg_color,
            activebackground="#74c7ec", relief=tk.FLAT, cursor="hand2",
            command=self.on_pick_color, padx=15, pady=5)
        color_btn.pack(side=tk.LEFT)

        self.color_preview = tk.Label(color_row, text="  ",
            font=("Segoe UI", 10), bg="#ffffff", width=4)
        self.color_preview.pack(side=tk.LEFT, padx=(10, 0))

        # Preview card
        preview_card = tk.Frame(right, bg=self.card_bg)
        preview_card.pack(fill=tk.X, pady=(10, 0), ipadx=15, ipady=12)

        tk.Label(preview_card, text="Preview (1st row of file)",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color).pack(anchor=tk.W, padx=10, pady=(8, 8))

        preview_box = tk.Frame(preview_card, bg=self.bg_color)
        preview_box.pack(fill=tk.X, padx=10, pady=(0, 10), ipady=15)

        self.preview_label = tk.Label(preview_box, text="(load a file to see the preview)",
            font=("Segoe UI", 12), bg=self.bg_color, fg=self.fg_color)
        self.preview_label.pack()

        for var in [
            self.site_label_var,
            self.cell_label_var,
            self.use_site_for_cell_var,
            self.hide_cell_label_var,
            self.show_label_var,
            self.label_scale_var,
            self.label_color_var,
            self.template_var,
        ]:
            var.trace_add("write", lambda *args: self._update_label_preview())

    def _build_generate_tab(self):
        frame = tk.Frame(self.tab_generate, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        tk.Label(frame,
            text="Generate KML File",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color).pack(anchor=tk.W)

        tk.Label(frame,
            text="Set output paths and generate the KML file",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.subtext_color).pack(anchor=tk.W, pady=(3, 15))

        # Output paths card
        paths_card = tk.Frame(frame, bg=self.card_bg)
        paths_card.pack(fill=tk.X, pady=(0, 15), ipadx=15, ipady=12)

        # KML path
        kml_row = tk.Frame(paths_card, bg=self.card_bg)
        kml_row.pack(fill=tk.X, padx=10, pady=(10, 8))

        tk.Label(kml_row, text="Output KML file:",
            font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color, width=22, anchor=tk.W).pack(side=tk.LEFT)

        self.kml_path_var = tk.StringVar()
        kml_entry = tk.Entry(kml_row, textvariable=self.kml_path_var,
            font=("Segoe UI", 10), bg=self.bg_color, fg=self.fg_color,
            insertbackground=self.fg_color, relief=tk.FLAT, width=50)
        kml_entry.pack(side=tk.LEFT, padx=(0, 10))

        kml_btn = tk.Button(kml_row, text="Browse...",
            font=("Segoe UI", 9), bg=self.accent_color, fg=self.bg_color,
            activebackground="#74c7ec", relief=tk.FLAT, cursor="hand2",
            command=self.on_choose_kml, padx=10, pady=3)
        kml_btn.pack(side=tk.LEFT)

        # Report path
        report_row = tk.Frame(paths_card, bg=self.card_bg)
        report_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(report_row, text="TXT report (optional):",
            font=("Segoe UI", 10), bg=self.card_bg, fg=self.subtext_color, width=22, anchor=tk.W).pack(side=tk.LEFT)

        self.report_path_var = tk.StringVar()
        report_entry = tk.Entry(report_row, textvariable=self.report_path_var,
            font=("Segoe UI", 10), bg=self.bg_color, fg=self.fg_color,
            insertbackground=self.fg_color, relief=tk.FLAT, width=50)
        report_entry.pack(side=tk.LEFT, padx=(0, 10))

        report_btn = tk.Button(report_row, text="Browse...",
            font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_color,
            activebackground=self.card_hover, relief=tk.FLAT, cursor="hand2",
            command=self.on_choose_report, padx=10, pady=3)
        report_btn.pack(side=tk.LEFT)

        # Action buttons
        buttons_frame = tk.Frame(frame, bg=self.bg_color)
        buttons_frame.pack(fill=tk.X, pady=(5, 15))

        generate_btn = tk.Button(buttons_frame, text="Generate KML",
            font=("Segoe UI", 12, "bold"), bg=self.success_color, fg=self.bg_color,
            activebackground="#94e2d5", activeforeground=self.bg_color,
            relief=tk.FLAT, cursor="hand2", command=self.on_generate, padx=30, pady=12)
        generate_btn.pack(side=tk.LEFT)

        save_profile_btn = tk.Button(buttons_frame, text="Save Profile",
            font=("Segoe UI", 10), bg=self.card_bg, fg=self.fg_color,
            activebackground=self.card_hover, relief=tk.FLAT, cursor="hand2",
            command=self.on_save_profile, padx=15, pady=8)
        save_profile_btn.pack(side=tk.LEFT, padx=(15, 0))

        load_profile_btn = tk.Button(buttons_frame, text="Load Profile",
            font=("Segoe UI", 10), bg=self.card_bg, fg=self.fg_color,
            activebackground=self.card_hover, relief=tk.FLAT, cursor="hand2",
            command=self.on_load_profile, padx=15, pady=8)
        load_profile_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Progress bar
        self.progress = ttk.Progressbar(frame, length=500, mode="determinate")
        self.progress.pack(anchor=tk.W, pady=(0, 15))

        # Log area
        log_header = tk.Frame(frame, bg=self.bg_color)
        log_header.pack(fill=tk.X, pady=(0, 5))

        tk.Label(log_header, text="Execution Log",
            font=("Segoe UI", 11, "bold"), bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

        clear_btn = tk.Button(log_header, text="Clear",
            font=("Segoe UI", 9), bg=self.card_bg, fg=self.fg_color,
            activebackground=self.card_hover, relief=tk.FLAT, cursor="hand2",
            command=lambda: self.log_text.delete(1.0, tk.END), padx=10, pady=3)
        clear_btn.pack(side=tk.RIGHT)

        log_frame = tk.Frame(frame, bg=self.card_bg)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=10,
            font=("Consolas", 9), bg=self.card_bg, fg=self.fg_color,
            insertbackground=self.fg_color, relief=tk.FLAT, wrap=tk.WORD)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def on_load_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Data files", "*.txt *.csv *.xlsx *.xls"),
            ("All files", "*.*"),
        ])
        if not path:
            return
        try:
            df, info = load_file(path)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.df = df
        self.file_path = path
        filename = os.path.basename(path)
        self.file_label.configure(text=filename, fg=self.success_color)
        self._update_preview()
        self.mapping = auto_map_columns(df)
        self._update_mapping_controls()
        self._update_params_list()
        self._update_label_controls()
        self.log("File loaded: %s (%s) - %d records" % (filename, info.get("format"), len(df)))

    def _update_preview(self):
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_tree["columns"] = list(self.df.columns)
        for col in self.df.columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=120, minwidth=80)
        for _, row in self.df.head(PREVIEW_ROWS).iterrows():
            values = [str(row.get(col, "")) for col in self.df.columns]
            self.preview_tree.insert("", tk.END, values=values)
        self.preview_info.configure(text="(%s records)" % len(self.df))

    def _update_mapping_controls(self):
        columns = list(self.df.columns)
        for key, var in self.mapping_vars.items():
            combo = self.mapping_combos.get(key)
            if combo:
                combo["values"] = columns
            var.set(self.mapping.get(key, "") or "")

    def _update_params_list(self):
        for child in self.params_frame.winfo_children():
            child.destroy()
        self.param_vars = {}
        if self.df is None:
            return
        mapped = set([v for v in self.mapping.values() if v])
        for col in self.df.columns:
            if col in mapped:
                continue
            sample = self.df[col].dropna().astype(str).head(1)
            sample_val = sample.iloc[0] if not sample.empty else ""
            if len(sample_val) > 30:
                sample_val = sample_val[:30] + "..."
            col_type = "num" if self._is_numeric_column(col) else "txt"

            item_frame = tk.Frame(self.params_frame, bg=self.card_bg)
            item_frame.pack(fill=tk.X, pady=2, ipady=5, ipadx=8)

            var = tk.BooleanVar(value=False)
            self.param_vars[col] = var

            cb = tk.Checkbutton(item_frame, variable=var,
                bg=self.card_bg, activebackground=self.card_bg,
                fg=self.accent_color, selectcolor=self.bg_color, cursor="hand2")
            cb.pack(side=tk.LEFT, padx=(5, 10))

            text_frame = tk.Frame(item_frame, bg=self.card_bg)
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(text_frame, text=col,
                font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color,
                anchor=tk.W).pack(anchor=tk.W)

            tk.Label(text_frame, text=f"[{col_type}] sample: {sample_val}",
                font=("Segoe UI", 8), bg=self.card_bg, fg=self.subtext_color,
                anchor=tk.W).pack(anchor=tk.W)

            # Click anywhere to toggle
            for widget in [item_frame, text_frame]:
                widget.bind("<Button-1>", lambda e, v=var: v.set(not v.get()))
                widget.config(cursor="hand2")

    def _is_numeric_column(self, col):
        try:
            pd.to_numeric(self.df[col].dropna().head(20))
            return True
        except Exception:
            return False

    def _toggle_all_params(self, state):
        for var in self.param_vars.values():
            var.set(state)

    def _update_label_controls(self):
        columns = list(self.df.columns)
        self.site_label_combo["values"] = columns
        self.cell_label_combo["values"] = columns
        if self.mapping.get("site_name"):
            self.site_label_var.set(self.mapping["site_name"])
        if self.mapping.get("cell_name"):
            self.cell_label_var.set(self.mapping["cell_name"])
        self._update_label_preview()

    def _update_label_preview(self):
        if self.df is None or self.df.empty:
            self.preview_label.configure(text="(load a file to see the preview)")
            return
        row = self.df.iloc[0].to_dict()
        template = self.template_var.get()
        field = self.site_label_var.get()
        if template:
            try:
                label = template.format_map(row)
            except Exception:
                label = "(invalid template)"
        else:
            label = str(row.get(field, "")) if field else "(select a field)"

        if not label:
            label = "(empty)"

        self.preview_label.configure(text=label)

        # Update color preview if exists
        if hasattr(self, 'color_preview'):
            color = self.label_color_var.get()
            if len(color) == 6:
                try:
                    self.color_preview.configure(bg="#" + color)
                except tk.TclErrorr:
                    pass

    def on_validate_mapping(self):
        if self.df is None:
            return
        mapping = {key: var.get() for key, var in self.mapping_vars.items()}
        issues = validate_mapping(self.df, mapping)
        if issues:
            self.mapping_status.configure(text="; ".join(issues), fg=self.warning_color)
        else:
            self.mapping_status.configure(text="Mapping validated successfully!", fg=self.success_color)
        self.mapping = mapping

    def on_pick_color(self):
        color = colorchooser.askcolor()
        if color and color[1]:
            self.label_color_var.set(color[1].replace("#", ""))

    def _collect_label_config(self):
        return LabelConfig(
            site_field=self.site_label_var.get(),
            cell_field=self.cell_label_var.get(),
            use_site_for_cell=self.use_site_for_cell_var.get(),
            hide_cell_label=self.hide_cell_label_var.get(),
            show_label=self.show_label_var.get(),
            text_scale=float(self.label_scale_var.get()),
            text_color=self.label_color_var.get(),
            shadow=self.shadow_var.get(),
            position=self.position_var.get(),
            template=self.template_var.get(),
        )

    def on_choose_kml(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".kml",
            filetypes=[("KML", "*.kml")],
            initialdir=self.last_dir,
        )
        if path:
            self.kml_path_var.set(path)
            self.last_dir = os.path.dirname(path)

    def on_choose_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt")],
            initialdir=self.last_dir,
        )
        if path:
            self.report_path_var.set(path)
            self.last_dir = os.path.dirname(path)

    def _collect_band_overrides(self):
        overrides = {}
        for key, var in self.band_override_vars.items():
            value = var.get().strip()
            if not value:
                continue
            try:
                val = int(float(value))
                overrides[key] = val
            except ValueErrorr:
                continue
        return overrides

    def _collect_beamwidth_overrides(self):
        overrides = {}
        for key, var in self.beamwidth_override_vars.items():
            value = var.get().strip()
            if not value:
                continue
            try:
                val = float(value)
                overrides[key] = val
            except ValueErrorr:
                continue
        return overrides

    def on_generate(self):
        if self.df is None:
            messagebox.showerror("Error", "Load a file first.")
            return
        kml_path = self.kml_path_var.get().strip()
        if not kml_path:
            messagebox.showerror("Error", "Select the output KML file.")
            return
        kml_dir = os.path.dirname(kml_path)
        if kml_dir and not os.path.isdir(kml_dir):
            messagebox.showerror("Error", "Output folder does not exist.")
            return

        self.progress["value"] = 10
        self.mapping = {key: var.get() for key, var in self.mapping_vars.items()}
        label_config = self._collect_label_config()
        extra_fields = [col for col, var in self.param_vars.items() if var.get()]
        scale = float(self.scale_var.get())
        band_overrides = self._collect_band_overrides()
        beamwidth_overrides = self._collect_beamwidth_overrides()

        required = ["latitude", "longitude", "azimuth", "earfcn"]
        missing = [key for key in required if not self.mapping.get(key)]
        if missing:
            messagebox.showerror("Error", "Required fields missing mapping: %s" % ", ".join(missing))
            return

        issues = validate_mapping(self.df, self.mapping)
        if issues:
            messagebox.showwarning("Mapping", "; ".join(issues))

        warnings = []
        if self.mapping.get("latitude") and self.mapping.get("longitude"):
            warnings.extend(find_duplicate_coords(self.df, self.mapping["latitude"], self.mapping["longitude"], self.mapping.get("site_name")))
        if self.mapping.get("azimuth"):
            warnings.extend(find_invalid_azimuth(self.df, self.mapping["azimuth"]))
        if self.mapping.get("earfcn"):
            warnings.extend(find_missing_earfcn(self.df, self.mapping["earfcn"]))
        if label_config.site_field:
            warnings.extend(find_empty_labels(self.df, label_config.site_field))
        if warnings:
            self.log("Warnings: %s" % len(warnings))
            for warn in warnings[:20]:
                self.log(warn)

        self.progress["value"] = 40
        kml_bytes = generate_kml(self.df, self.mapping, label_config, extra_fields, scale, band_overrides, beamwidth_overrides)
        try:
            with open(kml_path, "wb") as handle:
                handle.write(kml_bytes)
        except PermissionError:
            messagebox.showerror(
                "Error",
                "You don't have permission to save in this location. Choose another folder or run as administrator.",
            )
            return
        except OSError as exc:
            messagebox.showerror("Error", "Failed to save KML file: %s" % exc)
            return
        self.progress["value"] = 70

        report_path = self.report_path_var.get().strip()
        if report_path:
            self._write_report(report_path, label_config)
        self.progress["value"] = 100
        self.log("KML generated: %s" % kml_path)
        messagebox.showinfo("Completed", "KML generated successfully.")

    def _write_report(self, path, label_config):
        total_cells = len(self.df)
        site_col = self.mapping.get("site_name")
        total_sites = len(self.df[site_col].unique()) if site_col else total_cells

        band_counts = {}
        earfcn_col = self.mapping.get("earfcn")
        if earfcn_col:
            for value in self.df[earfcn_col].values:
                info = get_band_info(value)
                key = info["label"] if info else "Unknown Band"
                band_counts[key] = band_counts.get(key, 0) + 1

        lines = [
            "Total sites: %s" % total_sites,
            "Total cells: %s" % total_cells,
            "Label field: %s" % label_config.site_field,
            "",
            "Distribution by band:",
        ]
        for band, count in band_counts.items():
            lines.append("- %s: %s" % (band, count))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        self.log("Report saved: %s" % path)

    def on_save_profile(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        profile = {
            "mapping": {key: var.get() for key, var in self.mapping_vars.items()},
            "extra_fields": [col for col, var in self.param_vars.items() if var.get()],
            "label_config": self._collect_label_config().__dict__,
            "scale": self.scale_var.get(),
            "band_overrides": self._collect_band_overrides(),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=2)
        self.log("Profile saved: %s" % path)

    def on_load_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            profile = json.load(handle)
        for key, value in profile.get("mapping", {}).items():
            if key in self.mapping_vars:
                self.mapping_vars[key].set(value)
        for col, var in self.param_vars.items():
            var.set(col in profile.get("extra_fields", []))
        label_conf = profile.get("label_config", {})
        self.site_label_var.set(label_conf.get("site_field", ""))
        self.cell_label_var.set(label_conf.get("cell_field", ""))
        self.use_site_for_cell_var.set(label_conf.get("use_site_for_cell", False))
        self.hide_cell_label_var.set(label_conf.get("hide_cell_label", False))
        self.show_label_var.set(label_conf.get("show_label", True))
        self.label_scale_var.set(label_conf.get("text_scale", 1.0))
        self.label_color_var.set(label_conf.get("text_color", DEFAULT_LABEL_COLOR))
        self.shadow_var.set(label_conf.get("shadow", False))
        self.position_var.set(label_conf.get("position", "center"))
        self.template_var.set(label_conf.get("template", ""))
        self.scale_var.set(profile.get("scale", 0.5))
        for key, value in profile.get("band_overrides", {}).items():
            if key in self.band_override_vars:
                self.band_override_vars[key].set(str(value))
        self._update_label_preview()
        self.log("Profile loaded: %s" % path)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
