let map;
let baseLayers;
let overlayControl;
let labelLayer;
let bandLayers = {};
let autoRefreshEnabled = false;
let polygonIndex = {};
let siteIndex = {};
let mapContainerEl;
let mapEl;

// Measure tool state
let measureMode = false;
let measurePoints = [];
let measureMarkers = [];
let measureLine = null;
let measureLayerGroup = null;

// Custom marker state
let addMarkerMode = false;
let customMarkers = [];
let customMarkerIdCounter = 0;
let customMarkerLayer = null;
let tempMarkerPreview = null; // preview marker before saving

const state = {
  columns: [],
  mapping: {
    latitude: "",
    longitude: "",
    site_name: "",
    cell_name: "",
    earfcn: "",
    azimuth: "",
    beamwidth: "",
  },
  bands: [],
  filterColumns: {},
  filterSelections: {},
};

function setStatus(text) {
  document.getElementById("status-text").textContent = text;
}

function renderPreview(preview) {
  const table = document.getElementById("preview-table");
  table.innerHTML = "";
  if (!preview || preview.length === 0) {
    table.innerHTML = '<tr><td class="text-muted">No data</td></tr>';
    return;
  }
  const headers = Object.keys(preview[0]);
  const thead = document.createElement("thead");
  thead.innerHTML = "<tr>" + headers.map((h) => `<th>${h}</th>`).join("") + "</tr>";
  const tbody = document.createElement("tbody");
  preview.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = headers.map((h) => `<td>${row[h] ?? ""}</td>`).join("");
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
}

function buildSelectOptions(select, columns, selected) {
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "Select column";
  select.appendChild(empty);
  columns.forEach((col) => {
    const opt = document.createElement("option");
    opt.value = col;
    opt.textContent = col;
    if (col === selected) opt.selected = true;
    select.appendChild(opt);
  });
}

function buildMappingUI(columns) {
  const mappingFields = document.getElementById("mapping-fields");
  mappingFields.innerHTML = "";
  const fields = [
    { key: "latitude", label: "Latitude" },
    { key: "longitude", label: "Longitude" },
    { key: "site_name", label: "Site Name" },
    { key: "cell_name", label: "Cell Name" },
    { key: "earfcn", label: "EARFCN" },
    { key: "azimuth", label: "Azimuth" },
    { key: "beamwidth", label: "Beamwidth (optional)" },
  ];

  fields.forEach((field) => {
    const col = document.createElement("div");
    col.className = "col-md-6";
    col.innerHTML = `
      <label class="form-label">${field.label}</label>
      <select class="form-select" data-map="${field.key}"></select>
    `;
    mappingFields.appendChild(col);
    const select = col.querySelector("select");
    buildSelectOptions(select, columns, state.mapping[field.key]);
  });
}

function updateMappingFromUI() {
  document.querySelectorAll("[data-map]").forEach((select) => {
    const key = select.getAttribute("data-map");
    state.mapping[key] = select.value;
  });
}

function updateMappingUI(mapping) {
  state.mapping = { ...state.mapping, ...mapping };
  document.querySelectorAll("[data-map]").forEach((select) => {
    const key = select.getAttribute("data-map");
    select.value = state.mapping[key] || "";
  });
}

function renderIssues(issues) {
  const list = document.getElementById("mapping-issues");
  list.innerHTML = "";
  if (!issues || issues.length === 0) {
    list.innerHTML = '<li class="list-group-item text-muted">No issues</li>';
    return;
  }
  issues.forEach((issue) => {
    const li = document.createElement("li");
    li.className = "list-group-item";
    li.textContent = issue;
    list.appendChild(li);
  });
}

function buildExtraFields(columns) {
  const container = document.getElementById("extra-fields");
  container.innerHTML = "";
  columns.forEach((col) => {
    const wrapper = document.createElement("div");
    wrapper.className = "col-md-4";
    wrapper.innerHTML = `
      <div class="form-check">
        <input class="form-check-input" type="checkbox" value="${col}" id="extra-${col}">
        <label class="form-check-label" for="extra-${col}">${col}</label>
      </div>
    `;
    container.appendChild(wrapper);
  });
}

function buildLabelSelectors(columns) {
  buildSelectOptions(document.getElementById("site-label-field"), columns, "");
  buildSelectOptions(document.getElementById("cell-label-field"), columns, "");
}

async function buildFilterFields(filterColumns) {
  const container = document.getElementById("filter-fields");
  container.innerHTML = "";
  state.filterSelections = {};

  const labels = {
    uf: "UF / Estado",
    cn: "CN / DDD",
    regional: "Regional",
    municipio: "Município / Cidade",
  };

  for (const [key, column] of Object.entries(filterColumns || {})) {
    const col = document.createElement("div");
    col.className = "col-md-6";
    col.innerHTML = `
      <label class="form-label">${labels[key] || key} (${column})</label>
      <select class="form-select filter-select" multiple data-filter-col="${column}"></select>
    `;
    container.appendChild(col);
    const select = col.querySelector("select");

    const data = await fetchFilterValues(column, {});
    (data.values || []).forEach((value) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      select.appendChild(opt);
    });

    select.addEventListener("change", () => {
      refreshFilterOptions(column);
    });
  }
}

function gatherFilters() {
  const filters = {};
  document.querySelectorAll("[data-filter-col]").forEach((select) => {
    const col = select.getAttribute("data-filter-col");
    const values = Array.from(select.selectedOptions).map((opt) => opt.value);
    if (values.length > 0) {
      filters[col] = values;
    }
  });
  return filters;
}

async function fetchFilterValues(column, filters) {
  const res = await fetch("/api/filter-values", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ column, filters }),
  });
  return res.json();
}

async function refreshFilterOptions(changedColumn) {
  const currentFilters = gatherFilters();
  const selects = Array.from(document.querySelectorAll("[data-filter-col]"));
  for (const select of selects) {
    const col = select.getAttribute("data-filter-col");
    if (!col || col === changedColumn) continue;
    const previous = Array.from(select.selectedOptions).map((opt) => opt.value);
    const data = await fetchFilterValues(col, currentFilters);

    select.innerHTML = "";
    (data.values || []).forEach((value) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      if (previous.includes(value)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }
}

async function applyFilters() {
  const filters = gatherFilters();
  const res = await fetch("/api/apply-filters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filters }),
  });
  const data = await res.json();
  renderPreview(data.preview || []);
  document.getElementById("row-count").textContent = data.total_rows ?? 0;
  refreshMap();
}

function clearFilters() {
  document.querySelectorAll("[data-filter-col]").forEach((select) => {
    select.selectedIndex = -1;
  });
  refreshFilterOptions("");
}

async function loadBands() {
  const res = await fetch("/api/bands");
  const data = await res.json();
  state.bands = data.bands;

  const table = document.getElementById("band-table");
  table.innerHTML = "";
  const thead = document.createElement("thead");
  thead.innerHTML = "<tr><th>Band</th><th>Radius (m)</th><th>Beamwidth</th><th>Color</th></tr>";
  const tbody = document.createElement("tbody");
  state.bands.forEach((band) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${band.label}</td>
      <td><input class="form-control form-control-sm" type="number" data-radius="${band.key}" placeholder="${band.default_radius}"></td>
      <td><input class="form-control form-control-sm" type="number" data-beam="${band.key}" placeholder="${band.default_beamwidth}"></td>
      <td><span class="band-swatch" style="background:${band.color}"></span></td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
}

function gatherConfig() {
  updateMappingFromUI();
  const extra = [];
  document.querySelectorAll('#extra-fields input[type="checkbox"]:checked').forEach((cb) => {
    extra.push(cb.value);
  });

  const bandScaleOverrides = {};
  const beamwidthOverrides = {};
  document.querySelectorAll("[data-radius]").forEach((input) => {
    const key = input.getAttribute("data-radius");
    if (input.value) bandScaleOverrides[key] = parseFloat(input.value);
  });
  document.querySelectorAll("[data-beam]").forEach((input) => {
    const key = input.getAttribute("data-beam");
    if (input.value) beamwidthOverrides[key] = parseFloat(input.value);
  });

  return {
    mapping: state.mapping,
    extra_fields: extra,
    scale: parseFloat(document.getElementById("scale-range").value),
    band_scale_overrides: bandScaleOverrides,
    beamwidth_overrides: beamwidthOverrides,
    label_config: {
      site_field: document.getElementById("site-label-field").value,
      cell_field: document.getElementById("cell-label-field").value,
      use_site_for_cell: document.getElementById("label-use-site").checked,
      hide_cell_label: document.getElementById("label-hide-cell").checked,
      show_label: document.getElementById("label-show").checked,
      text_scale: parseFloat(document.getElementById("label-scale").value || "1.0"),
      text_color: document.getElementById("label-color").value,
      shadow: document.getElementById("label-shadow").checked,
      position: document.getElementById("label-position").value,
      template: document.getElementById("label-template").value,
    },
  };
}

async function applyConfig() {
  const config = gatherConfig();
  await fetch("/api/set-config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return config;
}

function initMap() {
  map = L.map("map").setView([-15.77, -47.92], 4);
  mapContainerEl = document.querySelector(".map-panel");
  mapEl = document.getElementById("map");
  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  });
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "&copy; Esri",
    }
  );

  osm.addTo(map);
  baseLayers = { OpenStreetMap: osm, Satellite: satellite };
  overlayControl = L.control.layers(baseLayers, {}).addTo(map);
  labelLayer = L.layerGroup().addTo(map);
  customMarkerLayer = L.layerGroup().addTo(map);

  // Unified map click handler
  map.on("click", onMapClick);
}

function syncMapSize() {
  if (!mapContainerEl || !mapEl) return;
  const height = mapContainerEl.clientHeight;
  if (height > 0) {
    mapEl.style.height = `${height}px`;
  }
  if (map) {
    map.invalidateSize();
  }
}

function clearLayers() {
  Object.values(bandLayers).forEach((layer) => map.removeLayer(layer));
  bandLayers = {};
  if (overlayControl) {
    map.removeControl(overlayControl);
    overlayControl = L.control.layers(baseLayers, {}).addTo(map);
  }
  labelLayer.clearLayers();
}

function createLabelIcon(label, style) {
  const shadowClass = style.shadow ? "shadow" : "";
  const fontSize = 12 * (style.text_scale || 1);
  return L.divIcon({
    className: `site-label ${shadowClass}`,
    html: `<div style="color:${style.text_color}; font-size:${fontSize}px;">${label}</div>`,
    iconSize: [120, 20],
    iconAnchor: [60, style.position === "above" ? 40 : style.position === "below" ? -5 : 20],
  });
}

async function refreshMap() {
  setStatus("Rendering map...");
  try {
    await applyConfig();
    const res = await fetch("/api/map-data");
    if (!res.ok) {
      setStatus("Error: Map data not available. Ensure mapping is complete.");
      return;
    }
    const data = await res.json();
    clearLayers();
    polygonIndex = {};
    siteIndex = {};

    const bounds = [];
    data.cells.forEach((cell) => {
      if (!bandLayers[cell.band_label]) {
        bandLayers[cell.band_label] = L.layerGroup().addTo(map);
        overlayControl.addOverlay(bandLayers[cell.band_label], cell.band_label);
      }
    const polygon = L.polygon(cell.polygon, {
      color: cell.color,
      fillColor: cell.color,
      fillOpacity: 0.6,
      weight: 1,
    });
    polygon.bindPopup(cell.popup);
    if (cell.cell_label) {
      polygon.bindTooltip(cell.cell_label, { direction: "top", sticky: true });
    }
    polygon.on("click", (e) => {
      if (measureMode) {
        L.DomEvent.stopPropagation(e);
        addMeasurePoint(cell.lat, cell.lon, cell.site_name || cell.cell_name);
      } else if (addMarkerMode) {
        L.DomEvent.stopPropagation(e);
        onMapClickAddMarker({ latlng: { lat: cell.lat, lng: cell.lon } }, cell.site_name || cell.cell_name);
      }
    });
      polygon.addTo(bandLayers[cell.band_label]);
      if (cell.cell_name) {
        polygonIndex[cell.cell_name] = polygon;
      }
      if (cell.site_name && !siteIndex[cell.site_name]) {
        siteIndex[cell.site_name] = polygon;
      }
      bounds.push([cell.lat, cell.lon]);
    });

    if (data.label_config.show_label) {
      data.sites.forEach((site) => {
        const icon = createLabelIcon(site.label, data.label_config);
        const marker = L.marker([site.lat, site.lon], { icon, interactive: false });
        marker.addTo(labelLayer);
      });
    }

    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [30, 30] });
    }

    syncMapSize();
    setStatus(`Map ready (${data.cells.length} sectors)`);
  } catch (error) {
    console.error("Map error:", error);
    setStatus("Map error - check console");
  }
}

function setupSearch() {
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  const searchMode = document.getElementById("search-mode");
  let debounceTimer;

  if (!searchInput || !searchResults || !searchMode) return;

  searchInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    const query = this.value.trim();
    if (query.length < 2) {
      searchResults.classList.remove("show");
      searchResults.innerHTML = "";
      return;
    }

    debounceTimer = setTimeout(async () => {
      const mode = searchMode.value;
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}`);
      const results = await response.json();
      if (results.length > 0) {
        searchResults.innerHTML = results
          .map(
            (r) => `
            <div class="search-result-item" data-kind="${r.kind || "site"}" data-cell="${r.cell_name || ""}" data-site="${r.site_name || ""}" data-lat="${r.lat}" data-lon="${r.lon}">
              <div class="cell-name">${r.kind === "city" ? r.label : (r.site_name || r.cell_name)}</div>
              <div class="site-name">${r.kind === "city" ? `${r.count} sectors` : (r.cell_name || "")}</div>
            </div>
          `
          )
          .join("");
        searchResults.classList.add("show");
      } else {
        searchResults.innerHTML = '<div class="search-result-item text-muted">No results</div>';
        searchResults.classList.add("show");
      }
    }, 250);
  });

  searchResults.addEventListener("click", (e) => {
    const item = e.target.closest(".search-result-item");
    if (!item || item.classList.contains("text-muted")) return;
    const lat = parseFloat(item.dataset.lat);
    const lon = parseFloat(item.dataset.lon);
    const kind = item.dataset.kind;
    const cell = item.dataset.cell;
    const site = item.dataset.site;
    selectSearchResult(cell, site, lat, lon, kind);
  });

  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.classList.remove("show");
    }
  });

  searchMode.addEventListener("change", () => {
    searchResults.classList.remove("show");
    searchResults.innerHTML = "";
    searchInput.value = "";
  });
}

function selectSearchResult(cellName, siteName, lat, lon, kind) {
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  if (searchInput) {
    searchInput.value = siteName || cellName || "";
  }
  if (searchResults) {
    searchResults.classList.remove("show");
  }

  if (map && !Number.isNaN(lat) && !Number.isNaN(lon)) {
    map.setView([lat, lon], kind === "city" ? 11 : 16);
  }

  if (kind !== "city") {
    const polygon = (cellName && polygonIndex[cellName]) || (siteName && siteIndex[siteName]);
    if (polygon) {
      polygon.openPopup();
    }
  }
}

async function uploadFile() {
  const fileInput = document.getElementById("file-input");
  if (!fileInput.files.length) return;
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  setStatus("Uploading...");
  const res = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) {
    setStatus("Upload error");
    return;
  }

  state.columns = data.columns;
  state.filterColumns = data.filter_columns || {};
  renderPreview(data.preview);
  document.getElementById("row-count").textContent = data.total_rows;
  document.getElementById("source-name").textContent = data.source_name || "-";

  buildMappingUI(state.columns);
  buildExtraFields(state.columns);
  buildLabelSelectors(state.columns);
  await buildFilterFields(state.filterColumns);
  setStatus("Data loaded");
}

async function autoMap() {
  updateMappingFromUI();
  const res = await fetch("/api/auto-map", { method: "POST" });
  const data = await res.json();
  updateMappingUI(data.mapping || {});
  renderIssues(data.issues || []);
  
  // Automatically show the map and enable live updates
  if (data.mapping && data.mapping.latitude && data.mapping.longitude) {
    if (!autoRefreshEnabled) {
      autoRefreshEnabled = true;
      const btn = document.getElementById("btn-auto-refresh");
      btn.classList.add("btn-primary");
      btn.classList.remove("btn-outline-light");
      btn.textContent = "✓ Live On";
    }
    refreshMap();
  }
}

async function validateMapping() {
  updateMappingFromUI();
  const payload = {
    mapping: state.mapping,
    label_field: document.getElementById("site-label-field").value,
  };
  const res = await fetch("/api/validate-mapping", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  renderIssues(data.issues || []);
}

async function downloadFile(endpoint, filename) {
  await applyConfig();
  const res = await fetch(endpoint, { method: "POST" });
  if (!res.ok) return;
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

async function loadProfiles() {
  const res = await fetch("/api/profiles");
  const data = await res.json();
  const list = document.getElementById("profile-list");
  list.innerHTML = "";
  (data.profiles || []).forEach((profile) => {
    const opt = document.createElement("option");
    opt.value = profile;
    opt.textContent = profile;
    list.appendChild(opt);
  });
}

async function saveProfile() {
  const name = document.getElementById("profile-name").value.trim();
  if (!name) return;
  const data = gatherConfig();
  await fetch("/api/save-profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, data }),
  });
  loadProfiles();
}

async function loadProfile() {
  const name = document.getElementById("profile-list").value;
  if (!name) return;
  const res = await fetch("/api/load-profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  const data = await res.json();
  const profile = data.data || {};

  if (profile.mapping) {
    updateMappingUI(profile.mapping);
  }

  if (profile.extra_fields) {
    document.querySelectorAll('#extra-fields input[type="checkbox"]').forEach((cb) => {
      cb.checked = profile.extra_fields.includes(cb.value);
    });
  }

  if (profile.scale) {
    document.getElementById("scale-range").value = profile.scale;
    document.getElementById("scale-value").textContent = profile.scale;
  }

  if (profile.band_scale_overrides) {
    Object.entries(profile.band_scale_overrides).forEach(([key, value]) => {
      const input = document.querySelector(`[data-radius="${key}"]`);
      if (input) input.value = value;
    });
  }

  if (profile.beamwidth_overrides) {
    Object.entries(profile.beamwidth_overrides).forEach(([key, value]) => {
      const input = document.querySelector(`[data-beam="${key}"]`);
      if (input) input.value = value;
    });
  }

  const label = profile.label_config || {};
  if (label.site_field) document.getElementById("site-label-field").value = label.site_field;
  if (label.cell_field) document.getElementById("cell-label-field").value = label.cell_field;
  if (label.template) document.getElementById("label-template").value = label.template;
  if (label.text_scale) document.getElementById("label-scale").value = label.text_scale;
  if (label.text_color) document.getElementById("label-color").value = label.text_color;
  if (label.position) document.getElementById("label-position").value = label.position;
  document.getElementById("label-show").checked = label.show_label ?? true;
  document.getElementById("label-shadow").checked = label.shadow ?? false;
  document.getElementById("label-use-site").checked = label.use_site_for_cell ?? false;
  document.getElementById("label-hide-cell").checked = label.hide_cell_label ?? false;
}

// ===== MEASURE TOOL (match Neighbor_Viewer behavior) =====

function toggleMeasureMode() {
  measureMode = !measureMode;
  const btn = document.getElementById("btn-measure");
  const card = document.getElementById("measure-card");
  const mapContainer = document.getElementById("map");

  if (measureMode) {
    // Disable marker mode if active
    if (addMarkerMode) {
      cancelAddMarker();
    }
    btn.classList.add("active");
    card.style.display = "block";
    mapContainer.classList.add("measure-mode");
    clearMeasurePoints();
    updateMeasureInfo();
  } else {
    btn.classList.remove("active");
    card.style.display = "none";
    mapContainer.classList.remove("measure-mode");
    clearMeasure();
  }
}

function clearMeasure() {
  clearMeasurePoints();
  measureMode = false;

  const btn = document.getElementById("btn-measure");
  const card = document.getElementById("measure-card");
  const mapContainer = document.getElementById("map");

  btn.classList.remove("active");
  card.style.display = "none";
  mapContainer.classList.remove("measure-mode");
}

function clearMeasurePoints() {
  measurePoints = [];

  measureMarkers.forEach((marker) => map.removeLayer(marker));
  measureMarkers = [];

  if (measureLine) {
    map.removeLayer(measureLine);
    measureLine = null;
  }

  if (measureTooltip) {
    map.removeLayer(measureTooltip);
    measureTooltip = null;
  }

  document.getElementById("measure-result").style.display = "none";
  updateMeasureInfo();
}

function updateMeasureInfo() {
  const point1Div = document.getElementById("measure-point1");
  const point2Div = document.getElementById("measure-point2");

  if (measurePoints.length === 0) {
    point1Div.innerHTML = '<span class="point-label text-primary">1st point:</span> <span class="text-muted">Click on map...</span>';
    point1Div.classList.add("active");
    point2Div.innerHTML = '<span class="point-label text-danger">2nd point:</span> <span class="text-muted">-</span>';
    point2Div.classList.remove("active");
  } else if (measurePoints.length === 1) {
    const p1 = measurePoints[0];
    point1Div.innerHTML = `<span class="point-label text-primary">1st point:</span> ${p1.name || p1.lat.toFixed(5) + ", " + p1.lon.toFixed(5)}`;
    point1Div.classList.remove("active");
    point2Div.innerHTML = '<span class="point-label text-danger">2nd point:</span> <span class="text-muted">Click on map...</span>';
    point2Div.classList.add("active");
  } else if (measurePoints.length === 2) {
    const p1 = measurePoints[0];
    const p2 = measurePoints[1];
    point1Div.innerHTML = `<span class="point-label text-primary">1st point:</span> ${p1.name || p1.lat.toFixed(5) + ", " + p1.lon.toFixed(5)}`;
    point2Div.innerHTML = `<span class="point-label text-danger">2nd point:</span> ${p2.name || p2.lat.toFixed(5) + ", " + p2.lon.toFixed(5)}`;
    point1Div.classList.remove("active");
    point2Div.classList.remove("active");
  }
}

function addMeasurePoint(lat, lon, name = null) {
  if (!measureMode) return;

  if (measurePoints.length >= 2) {
    clearMeasurePoints();
  }

  measurePoints.push({ lat, lon, name });

  const markerIcon = L.divIcon({
    className: "measure-marker" + (measurePoints.length === 2 ? " point-2" : ""),
    iconSize: [12, 12],
  });

  const marker = L.marker([lat, lon], { icon: markerIcon }).addTo(map);
  measureMarkers.push(marker);

  if (measurePoints.length === 2) {
    drawMeasureLine();
  }

  updateMeasureInfo();
}

function drawMeasureLine() {
  const p1 = measurePoints[0];
  const p2 = measurePoints[1];

  measureLine = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {
    color: "#0066FF",
    weight: 3,
    dashArray: "10, 5",
    opacity: 0.8,
  }).addTo(map);

  const distance = calculateDistance(p1.lat, p1.lon, p2.lat, p2.lon);

  const midLat = (p1.lat + p2.lat) / 2;
  const midLon = (p1.lon + p2.lon) / 2;
  const tooltipIcon = L.divIcon({
    className: "distance-tooltip",
    html: formatDistance(distance),
    iconSize: [80, 24],
    iconAnchor: [40, 12],
  });

  measureTooltip = L.marker([midLat, midLon], {
    icon: tooltipIcon,
    interactive: false,
    zIndexOffset: 2000,
  }).addTo(map);

  const resultDiv = document.getElementById("measure-result");
  resultDiv.style.display = "block";
  resultDiv.querySelector(".distance-value").innerHTML = formatDistance(distance);
}

function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function toRad(deg) {
  return deg * (Math.PI / 180);
}

function formatDistance(meters) {
  if (meters < 1000) {
    return Math.round(meters) + " m";
  } else {
    return (meters / 1000).toFixed(2) + " km";
  }
}

function onMapClick(e) {
  if (addMarkerMode) {
    onMapClickAddMarker(e);
  } else if (measureMode) {
    addMeasurePoint(e.latlng.lat, e.latlng.lng);
  }
}

function wireEvents() {
  document.getElementById("btn-upload").addEventListener("click", uploadFile);
  document.getElementById("btn-auto-map").addEventListener("click", autoMap);
  document.getElementById("btn-validate-map").addEventListener("click", validateMapping);
  document.getElementById("btn-refresh-map").addEventListener("click", refreshMap);
  document.getElementById("btn-auto-refresh").addEventListener("click", toggleAutoRefresh);
  document.getElementById("btn-measure").addEventListener("click", toggleMeasureMode);
  document.getElementById("btn-add-marker").addEventListener("click", toggleAddMarkerMode);
  document.getElementById("btn-apply-filters").addEventListener("click", applyFilters);
  document.getElementById("btn-clear-filters").addEventListener("click", clearFilters);
  document.getElementById("btn-generate-kml").addEventListener("click", () => downloadFile("/api/generate-kml", "cells.kml"));
  document.getElementById("btn-download-kml").addEventListener("click", () => downloadFile("/api/generate-kml", "cells.kml"));
  document.getElementById("btn-export-report").addEventListener("click", () => downloadFile("/api/export-report", "report.txt"));
  document.getElementById("btn-save-profile").addEventListener("click", saveProfile);
  document.getElementById("btn-load-profile").addEventListener("click", loadProfile);

  document.getElementById("scale-range").addEventListener("input", (e) => {
    document.getElementById("scale-value").textContent = e.target.value;
    if (autoRefreshEnabled) refreshMap();
  });

  // Auto-refresh map on config changes
  document.querySelectorAll("[data-map], [data-radius], [data-beam], #extra-fields input[type='checkbox'], #site-label-field, #cell-label-field, #label-show, #label-shadow, #label-use-site, #label-hide-cell, #label-scale, #label-color, #label-position, #label-template").forEach((el) => {
    el.addEventListener("change", () => {
      if (autoRefreshEnabled) refreshMap();
    });
  });
}

function toggleAutoRefresh() {
  autoRefreshEnabled = !autoRefreshEnabled;
  const btn = document.getElementById("btn-auto-refresh");
  if (autoRefreshEnabled) {
    btn.classList.add("btn-primary");
    btn.classList.remove("btn-outline-light");
    btn.textContent = "✓ Live On";
    refreshMap();
  } else {
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-outline-light");
    btn.textContent = "🔄 Live";
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  wireEvents();
  await loadBands();
  await loadProfiles();
  initResizeHandle();
  setupSearch();
  initCustomMarkerForm();
  syncMapSize();
  window.addEventListener("resize", syncMapSize);
  window.addEventListener("load", syncMapSize);
  setStatus("Ready");
});

// ===== CUSTOM MARKER TOOL =====

function toDeg(rad) {
  return rad * (180 / Math.PI);
}

function destinationPoint(lat, lon, bearingDeg, distanceM) {
  const R = 6371000;
  const latRad = toRad(lat);
  const lonRad = toRad(lon);
  const bearing = toRad(bearingDeg);
  const dr = distanceM / R;

  const destLat = Math.asin(
    Math.sin(latRad) * Math.cos(dr) +
    Math.cos(latRad) * Math.sin(dr) * Math.cos(bearing)
  );
  const destLon = lonRad + Math.atan2(
    Math.sin(bearing) * Math.sin(dr) * Math.cos(latRad),
    Math.cos(dr) - Math.sin(latRad) * Math.sin(destLat)
  );

  return [toDeg(destLat), toDeg(destLon)];
}

function generatePetalJS(lat, lon, azimuth, beamwidth, radiusM, points) {
  points = points || 24;
  const half = beamwidth / 2.0;
  const start = azimuth - half;
  const end = azimuth + half;
  const step = Math.max(1, Math.floor(beamwidth / Math.max(1, points)));

  const coords = [[lat, lon]]; // Leaflet [lat, lon]
  let angle = start;
  while (angle <= end) {
    const [dlat, dlon] = destinationPoint(lat, lon, angle, radiusM);
    coords.push([dlat, dlon]);
    angle += step;
  }
  const [eLat, eLon] = destinationPoint(lat, lon, end, radiusM);
  coords.push([eLat, eLon]);
  coords.push([lat, lon]);
  return coords;
}

function toggleAddMarkerMode() {
  addMarkerMode = !addMarkerMode;
  const btn = document.getElementById("btn-add-marker");
  const card = document.getElementById("custom-marker-card");
  const mapContainer = document.getElementById("map");

  if (addMarkerMode) {
    // Disable measure mode if active
    if (measureMode) {
      clearMeasure();
    }
    btn.classList.add("active");
    card.style.display = "block";
    mapContainer.classList.add("add-marker-mode");
    resetMarkerForm();
  } else {
    btn.classList.remove("active");
    card.style.display = "none";
    mapContainer.classList.remove("add-marker-mode");
    removeTempMarkerPreview();
  }
}

function cancelAddMarker() {
  addMarkerMode = false;
  window._editingMarkerId = null;
  const btn = document.getElementById("btn-add-marker");
  const card = document.getElementById("custom-marker-card");
  const mapContainer = document.getElementById("map");

  btn.classList.remove("active");
  card.style.display = "none";
  mapContainer.classList.remove("add-marker-mode");
  removeTempMarkerPreview();
}

function resetMarkerForm() {
  document.getElementById("marker-help").style.display = "block";
  document.getElementById("marker-form").style.display = "none";
  document.getElementById("marker-name").value = "";
  document.getElementById("marker-lat").value = "";
  document.getElementById("marker-lon").value = "";
  document.getElementById("type-pin").checked = true;
  document.getElementById("site-config").style.display = "none";
  document.getElementById("marker-sector-list").innerHTML = "";
  document.getElementById("marker-card-title").textContent = "Custom Marker";
  document.getElementById("btn-save-marker").textContent = "Save Marker";
  window._editingMarkerId = null;
}

function removeTempMarkerPreview() {
  if (tempMarkerPreview) {
    customMarkerLayer.removeLayer(tempMarkerPreview);
    tempMarkerPreview = null;
  }
}

function onMapClickAddMarker(e, refName) {
  if (!addMarkerMode) return;

  const lat = e.latlng.lat;
  const lon = e.latlng.lng;

  // Show preview marker
  removeTempMarkerPreview();
  tempMarkerPreview = L.circleMarker([lat, lon], {
    radius: 8,
    fillColor: "#22d3ee",
    color: "#fff",
    weight: 2,
    fillOpacity: 0.8,
  }).addTo(customMarkerLayer);

  // Populate form
  document.getElementById("marker-help").style.display = "none";
  document.getElementById("marker-form").style.display = "block";
  document.getElementById("marker-lat").value = lat.toFixed(6);
  document.getElementById("marker-lon").value = lon.toFixed(6);
  if (refName && !document.getElementById("marker-name").value) {
    document.getElementById("marker-name").value = "";
  }
  document.getElementById("marker-name").focus();
}

function buildSectorRows() {
  const count = Math.min(6, Math.max(1, parseInt(document.getElementById("marker-sector-count").value) || 3));
  const container = document.getElementById("marker-sector-list");
  container.innerHTML = "";

  const bandOptions = state.bands.map(b =>
    `<option value="${b.key}">${b.label}</option>`
  ).join("");

  for (let i = 0; i < count; i++) {
    const defaultAz = Math.round(i * (360 / count));
    const row = document.createElement("div");
    row.className = "sector-row";
    row.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-1">
        <span class="fw-bold" style="font-size:0.8rem;color:#333;">Sector ${i + 1}</span>
      </div>
      <div class="row g-1">
        <div class="col-5">
          <label>Azimuth</label>
          <input type="number" class="form-control form-control-sm sector-az" min="0" max="359" value="${defaultAz}" />
        </div>
        <div class="col-7">
          <label>Band</label>
          <select class="form-select form-select-sm sector-band">${bandOptions}</select>
        </div>
      </div>
    `;
    container.appendChild(row);
  }
}

function initCustomMarkerForm() {
  // Type toggle
  document.querySelectorAll('input[name="marker-type"]').forEach(radio => {
    radio.addEventListener("change", (e) => {
      const siteConfig = document.getElementById("site-config");
      if (e.target.value === "site") {
        siteConfig.style.display = "block";
        buildSectorRows();
      } else {
        siteConfig.style.display = "none";
      }
    });
  });

  // Sector count change
  document.getElementById("marker-sector-count").addEventListener("change", buildSectorRows);

  // Save button
  document.getElementById("btn-save-marker").addEventListener("click", saveCustomMarker);

  // Cancel button
  document.getElementById("btn-cancel-marker").addEventListener("click", () => {
    removeTempMarkerPreview();
    resetMarkerForm();
  });
}

function saveCustomMarker() {
  const name = document.getElementById("marker-name").value.trim() || "Marker " + (customMarkerIdCounter + 1);
  const lat = parseFloat(document.getElementById("marker-lat").value);
  const lon = parseFloat(document.getElementById("marker-lon").value);
  const type = document.querySelector('input[name="marker-type"]:checked').value;

  if (isNaN(lat) || isNaN(lon)) return;

  removeTempMarkerPreview();

  let sectors = [];
  if (type === "site") {
    const globalScale = parseFloat(document.getElementById("scale-range").value) || 0.5;
    const azInputs = document.querySelectorAll(".sector-az");
    const bandSelects = document.querySelectorAll(".sector-band");
    for (let i = 0; i < azInputs.length; i++) {
      const azimuth = parseFloat(azInputs[i].value) || 0;
      const bandKey = bandSelects[i].value;
      const band = state.bands.find(b => b.key === bandKey);
      // Use override if set, otherwise band default, apply global scale
      const radiusOverride = document.querySelector(`[data-radius="${bandKey}"]`);
      const beamOverride = document.querySelector(`[data-beam="${bandKey}"]`);
      const baseRadius = (radiusOverride && radiusOverride.value) ? parseFloat(radiusOverride.value) : (band ? band.default_radius : 300);
      const beamwidth = (beamOverride && beamOverride.value) ? parseFloat(beamOverride.value) : (band ? band.default_beamwidth : 65);
      sectors.push({
        azimuth,
        bandKey,
        bandLabel: band ? band.label : bandKey,
        beamwidth,
        radius: Math.round(baseRadius * globalScale),
        color: band ? band.color : "#888888",
      });
    }
  }

  // If editing, delete old marker first
  if (window._editingMarkerId) {
    deleteCustomMarker(window._editingMarkerId);
    window._editingMarkerId = null;
  }

  createCustomMarker(lat, lon, name, type, sectors);

  // Exit marker mode after save
  cancelAddMarker();
}

function createCustomMarker(lat, lon, name, type, sectors) {
  const id = "cm-" + (++customMarkerIdCounter);

  const markerData = {
    id, type, name, lat, lon, sectors,
    marker: null,
    petals: [],
  };

  if (type === "pin") {
    const icon = L.divIcon({
      className: "custom-pin-marker",
      html: `<div style="width:20px;height:20px;background:#ef4444;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.5);cursor:pointer;"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
    markerData.marker = L.marker([lat, lon], { icon, draggable: true, interactive: true }).addTo(customMarkerLayer);
  } else {
    markerData.marker = L.circleMarker([lat, lon], {
      radius: 8,
      fillColor: "#a855f7",
      color: "#fff",
      weight: 2,
      fillOpacity: 0.9,
      interactive: true,
    }).addTo(customMarkerLayer);

    // Make circleMarker draggable via custom drag behavior
    enableCircleMarkerDrag(markerData);

    // Generate petals
    sectors.forEach(sector => {
      const coords = generatePetalJS(lat, lon, sector.azimuth, sector.beamwidth, sector.radius);
      const petal = L.polygon(coords, {
        color: sector.color,
        fillColor: sector.color,
        fillOpacity: 0.35,
        weight: 2,
        dashArray: "6, 4",
      }).addTo(customMarkerLayer);
      petal.bindTooltip(`${name} - ${sector.bandLabel}`, { direction: "top", sticky: true });
      // Click on petal opens the site marker popup
      petal.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        markerData.marker.openPopup();
      });
      markerData.petals.push(petal);
    });
  }

  // Popup - bind to marker
  markerData.marker.bindPopup(() => buildMarkerPopup(markerData), { maxWidth: 280 });

  if (type === "pin") {
    // Pin markers have built-in drag
    markerData.marker.on("dragend", () => {
      const pos = markerData.marker.getLatLng();
      updateMarkerPosition(markerData, pos.lat, pos.lng);
    });
  }

  customMarkers.push(markerData);
  updateMarkerListUI();
  return markerData;
}

function enableCircleMarkerDrag(markerData) {
  let dragging = false;
  let hasMoved = false;
  let startLatLng = null;
  const cm = markerData.marker;

  cm.on("mousedown", (e) => {
    startLatLng = e.latlng;
    hasMoved = false;
    dragging = true;
    map.dragging.disable();
    L.DomEvent.preventDefault(e.originalEvent);
  });

  const onMouseMove = (e) => {
    if (!dragging) return;
    hasMoved = true;
    cm.setLatLng(e.latlng);
    markerData.petals.forEach((petal, idx) => {
      const sector = markerData.sectors[idx];
      const coords = generatePetalJS(e.latlng.lat, e.latlng.lng, sector.azimuth, sector.beamwidth, sector.radius);
      petal.setLatLngs(coords);
    });
  };

  const onMouseUp = () => {
    if (!dragging) return;
    dragging = false;
    map.dragging.enable();
    if (hasMoved) {
      const pos = cm.getLatLng();
      updateMarkerPosition(markerData, pos.lat, pos.lng);
    } else {
      // No movement = click, open popup
      cm.openPopup();
    }
  };

  map.on("mousemove", onMouseMove);
  map.on("mouseup", onMouseUp);
}

function updateMarkerPosition(markerData, newLat, newLon) {
  markerData.lat = newLat;
  markerData.lon = newLon;

  // Update petals for site type
  if (markerData.type === "site") {
    markerData.petals.forEach((petal, idx) => {
      const sector = markerData.sectors[idx];
      const coords = generatePetalJS(newLat, newLon, sector.azimuth, sector.beamwidth, sector.radius);
      petal.setLatLngs(coords);
    });
  }
}

function buildMarkerPopup(markerData) {
  const typeLabel = markerData.type === "pin" ? "Pin" : "Simulated Site";
  let html = `<div style="min-width:200px;">
    <div style="font-weight:700;font-size:1rem;margin-bottom:4px;">${markerData.name}</div>
    <div style="font-size:0.8rem;color:#666;margin-bottom:6px;">${typeLabel} &middot; ${markerData.lat.toFixed(5)}, ${markerData.lon.toFixed(5)}</div>`;

  if (markerData.type === "site" && markerData.sectors.length > 0) {
    html += `<div style="font-weight:600;font-size:0.85rem;margin-bottom:2px;">Sectors:</div>`;
    markerData.sectors.forEach((s, i) => {
      html += `<div style="font-size:0.8rem;">${i + 1}. Az: ${s.azimuth}&deg; &mdash; ${s.bandLabel}</div>`;
    });
  }

  html += `<div style="margin-top:8px;display:flex;gap:6px;">
    <button class="btn btn-sm btn-outline-primary" onclick="editCustomMarker('${markerData.id}')">Edit</button>
    <button class="btn btn-sm btn-outline-danger" onclick="deleteCustomMarker('${markerData.id}')">Delete</button>
  </div></div>`;
  return html;
}

function editCustomMarker(id) {
  const m = customMarkers.find(m => m.id === id);
  if (!m) return;

  // Close popup
  m.marker.closePopup();

  // Activate marker mode and show card
  addMarkerMode = true;
  const btn = document.getElementById("btn-add-marker");
  const card = document.getElementById("custom-marker-card");
  const mapContainer = document.getElementById("map");
  btn.classList.add("active");
  card.style.display = "block";
  mapContainer.classList.add("add-marker-mode");

  // Show form, hide help
  document.getElementById("marker-help").style.display = "none";
  document.getElementById("marker-form").style.display = "block";

  // Fill in current values
  document.getElementById("marker-name").value = m.name;
  document.getElementById("marker-lat").value = m.lat.toFixed(6);
  document.getElementById("marker-lon").value = m.lon.toFixed(6);

  // Set type radio
  if (m.type === "site") {
    document.getElementById("type-site").checked = true;
    document.getElementById("site-config").style.display = "block";
    document.getElementById("marker-sector-count").value = m.sectors.length;
    buildSectorRows();
    // Fill sector values
    const azInputs = document.querySelectorAll(".sector-az");
    const bandSelects = document.querySelectorAll(".sector-band");
    m.sectors.forEach((s, i) => {
      if (azInputs[i]) azInputs[i].value = s.azimuth;
      if (bandSelects[i]) bandSelects[i].value = s.bandKey;
    });
  } else {
    document.getElementById("type-pin").checked = true;
    document.getElementById("site-config").style.display = "none";
  }

  // Show preview marker at current position
  removeTempMarkerPreview();
  tempMarkerPreview = L.circleMarker([m.lat, m.lon], {
    radius: 8,
    fillColor: "#22d3ee",
    color: "#fff",
    weight: 2,
    fillOpacity: 0.8,
  }).addTo(customMarkerLayer);

  // Store edit context: save will delete old and create new
  window._editingMarkerId = id;

  // Update card title
  document.getElementById("marker-card-title").textContent = "Edit Marker";
  document.getElementById("btn-save-marker").textContent = "Update Marker";

  // Zoom to marker
  map.setView([m.lat, m.lon], map.getZoom());
}

function deleteCustomMarker(id) {
  const idx = customMarkers.findIndex(m => m.id === id);
  if (idx === -1) return;

  const m = customMarkers[idx];
  if (m.marker) customMarkerLayer.removeLayer(m.marker);
  m.petals.forEach(p => customMarkerLayer.removeLayer(p));

  customMarkers.splice(idx, 1);
  updateMarkerListUI();
}

function clearAllCustomMarkers() {
  [...customMarkers].forEach(m => deleteCustomMarker(m.id));
}

function updateMarkerListUI() {
  const card = document.getElementById("marker-list-card");
  const list = document.getElementById("marker-list");
  const count = document.getElementById("marker-count");

  count.textContent = customMarkers.length;

  if (customMarkers.length === 0) {
    card.style.display = "none";
    return;
  }

  card.style.display = "block";
  list.innerHTML = "";

  customMarkers.forEach(m => {
    const item = document.createElement("div");
    item.className = "marker-list-item";
    item.innerHTML = `
      <span class="ml-icon">${m.type === "pin" ? "\uD83D\uDCCD" : "\uD83D\uDCE1"}</span>
      <span class="ml-name" title="${m.name}">${m.name}</span>
      <button class="btn btn-sm btn-outline-secondary" onclick="zoomToCustomMarker('${m.id}')" title="Zoom">🔍</button>
      <button class="btn btn-sm btn-outline-danger" onclick="deleteCustomMarker('${m.id}')" title="Delete">&times;</button>
    `;
    list.appendChild(item);
  });
}

function zoomToCustomMarker(id) {
  const m = customMarkers.find(m => m.id === id);
  if (!m) return;
  map.setView([m.lat, m.lon], 15);
  if (m.marker) m.marker.openPopup();
}

function initResizeHandle() {
  const resizeHandle = document.getElementById("resize-handle");
  const configPanel = document.getElementById("config-panel");
  const mapPanel = document.getElementById("map-panel");
  const contentWrapper = document.getElementById("content-wrapper");

  if (!resizeHandle || !configPanel || !mapPanel || !contentWrapper) return;

  let isResizing = false;

  const isVertical = () => window.innerWidth <= 900;

  const onMouseMove = (moveEvent, startPos, startSize) => {
    if (!isResizing) return;
    const delta = isVertical() ? moveEvent.clientY - startPos : moveEvent.clientX - startPos;
    const wrapperSize = isVertical()
      ? contentWrapper.getBoundingClientRect().height
      : contentWrapper.getBoundingClientRect().width;
    const handleSize = isVertical() ? resizeHandle.offsetHeight : resizeHandle.offsetWidth;

    const minSize = 220;
    const newConfigSize = Math.max(minSize, startSize + delta);
    const newMapSize = Math.max(minSize, wrapperSize - newConfigSize - handleSize);

    if (isVertical()) {
      configPanel.style.flex = `0 0 ${newConfigSize}px`;
      mapPanel.style.flex = `0 0 ${newMapSize}px`;
    } else {
      configPanel.style.flex = `0 0 ${newConfigSize}px`;
      mapPanel.style.flex = `0 0 ${newMapSize}px`;
    }

    if (map) {
      requestAnimationFrame(() => map.invalidateSize());
    }
  };

  const onMouseUp = () => {
    isResizing = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  const handleMouseMove = (moveEvent) => {
    onMouseMove(moveEvent, startPos, startSize);
  };

  let startPos = 0;
  let startSize = 0;

  resizeHandle.addEventListener("mousedown", (e) => {
    isResizing = true;
    document.body.style.cursor = isVertical() ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";

    startPos = isVertical() ? e.clientY : e.clientX;
    startSize = isVertical() ? configPanel.offsetHeight : configPanel.offsetWidth;

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });
}
