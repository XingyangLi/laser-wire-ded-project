const MATERIALS = ["Invar36", "SS304", "316L", "Ti6Al4V", "IN718", "Fe", "Ni"];

const BASE = {
  case: "studio_case",
  laser_config: "transitional_r",
  power_w: 600,
  scan_mm_s: 5.8,
  wfs_mm_s: 29,
  track_length_mm: "",
  end_time_s: "",
  dim: "3d",
  beam_angle_deg: 25,
  focus_mm: 0.5,
  beam_radius_mm: 0.5,
  rayleigh_mm: "",
  beam_direction: "-",
  spot_radius_mm: 1.2,
  profile: "gaussian",
  absorptivity_substrate: "",
  absorptivity_wire: "",
  alpha_hit: 0.5,
  laser_ramp_ms: 2,
  wire_type: "solid",
  wire_diameter_mm: 0.9,
  feed_angle_deg: 90,
  feed_side: "front",
  wire_aim_mm: 0,
  wire_gap_mm: 0.05,
  feed_start_s: 0.02,
  strands: 7,
  strand_layout: "auto",
  strand_diameter_mm: "",
  strand_gap_mm: 0.04,
  lay_length_mm: "",
  lay_direction: "right",
  strand_feed_basis: "metal",
  strand_materials: "",
  feed_scale: 1,
  max_wfs_mm_s: 100,
  wire_material: "Invar36",
  substrate_material: "SS304",
  strand_k_factor: 1,
  unmelted_k_factor: 1,
  liquidus: "table",
  liquidus_unmixed: "",
  preheat_k: 300,
  resolution: "medium",
  dx_um: "",
  wire_refine: "",
  domain_y: "auto",
  upstream_mm: 3.5,
  downstream_mm: 6.5,
  half_width_mm: 3,
  substrate_mm: 2,
  gas_height_mm: 2.5,
  np: 8,
  write_interval_s: 0.01,
  max_co: 0.4,
  capillary_dt_factor: 0.8,
  no_marangoni: false,
  no_recoil: false,
  no_evaporation: false,
  no_radiation: false,
  no_convection: false,
  buoyancy: false,
  no_shadowing: false,
  no_wire_stubbing: false,
  no_melted_follow_substrate: false,
  gas_viscosity_factor: 20,
  mushy_C: 1e8,
};

function preset(over) {
  return Object.assign({}, BASE, over);
}

const PRESETS = {
  "Transitional-R, solid wire": preset({}),
  "Transitional-R, 7-strand, tip on the plate": preset({
    wire_type: "stranded", strands: 7, strand_layout: "auto",
    focus_mm: 0, wire_gap_mm: 0, feed_start_s: 0, wire_diameter_mm: 0.9,
  }),
  "Fe+Ni 5-strand validation": preset({
    wire_type: "stranded", strands: 5, strand_layout: "ring",
    strand_diameter_mm: 0.3, strand_materials: "Fe,Ni,Fe,Ni,Fe",
    strand_gap_mm: 0.08, wire_material: "Fe", substrate_material: "Invar36",
    power_w: 600, scan_mm_s: 2.667, wfs_mm_s: 10.1,
    focus_mm: -1.5, rayleigh_mm: 1.2, beam_direction: "-",
    absorptivity_substrate: 0.35, absorptivity_wire: 0.25, alpha_hit: 0.25,
    strand_k_factor: 0.4, unmelted_k_factor: 0.3, liquidus_unmixed: 0.85,
    wire_gap_mm: 0, feed_start_s: 0, feed_angle_deg: 90,
    track_length_mm: 3, wire_diameter_mm: "",
  }),
  "Normal, solid wire": preset({
    laser_config: "normal", power_w: 600, scan_mm_s: 6.7, wfs_mm_s: 11.4, beam_direction: "+",
  }),
  "Lack of fusion, solid wire": preset({
    laser_config: "lof", power_w: 400, scan_mm_s: 10, wfs_mm_s: 17, beam_direction: "+",
  }),
  "Single beam, 316L": preset({
    laser_config: "single", power_w: 2000, scan_mm_s: 10, wfs_mm_s: 25,
    wire_material: "316L", substrate_material: "316L",
    wire_diameter_mm: 1.0, feed_angle_deg: 45, wire_gap_mm: 0.3, feed_start_s: 0.02,
    upstream_mm: 4.5, downstream_mm: 7, half_width_mm: 4, substrate_mm: 2.5,
    beam_direction: "+",
  }),
};

const GROUPS = [
  {
    id: "process", title: "Process",
    blurb: "How hard the laser is, how fast the plate moves, and how long the track is. The plate moves; the laser and the wire stay put.",
    fields: [
      { key: "laser_config", label: "Process window", type: "select", options: ["transitional_r", "normal", "lof", "single"],
        help: "The first three are the Gao et al. triple-beam settings. Single is one vertical beam and a side-fed wire." },
      { key: "power_w", label: "Laser power", unit: "W", step: "10", help: "Total power, shared across the beams." },
      { key: "scan_mm_s", label: "Scan speed", unit: "mm/s", step: "0.1", help: "How fast the substrate moves in +x." },
      { key: "wfs_mm_s", label: "Wire feed", unit: "mm/s", step: "0.1", help: "Nominal feed. Stranded wire with “metal” basis is sped up so the same amount of metal arrives." },
      { key: "track_length_mm", label: "Track length", unit: "mm", step: "0.5", help: "Leave blank to let the end time decide. Fill this to set the end time from the scan speed." },
      { key: "end_time_s", label: "End time", unit: "s", step: "0.05", help: "Simulation clock at which the run stops. Leave blank if you set a track length." },
      { key: "dim", label: "Dimension", type: "select", options: ["3d", "2d"], help: "2D is a single slice for a quick look. It is hotter and longer than the real pool." },
    ],
  },
  {
    id: "laser", title: "Laser",
    blurb: "Where the light is aimed. Focus height is where the beams cross the wire axis. Negative focus is below the plate, which spreads the spot.",
    fields: [
      { key: "beam_angle_deg", label: "Beam angle from vertical", unit: "deg", step: "1", when: (s) => s.laser_config !== "single",
        help: "The paper does not state this. 25° is the assumption used so far." },
      { key: "focus_mm", label: "Focus height", unit: "mm", step: "0.1", when: (s) => s.laser_config !== "single",
        help: "0 = on the plate. Positive = up the wire, which can melt a neck and ball the tip. Negative = below the plate." },
      { key: "beam_radius_mm", label: "Beam waist radius", unit: "mm", step: "0.05", when: (s) => s.laser_config !== "single",
        help: "1/e² radius of each beam at the focus. Diameter is twice this." },
      { key: "rayleigh_mm", label: "Rayleigh length", unit: "mm", step: "0.1", when: (s) => s.laser_config !== "single",
        help: "Blank = the beam does not spread. A value (for example 1.2 mm) makes a defocused spot larger on the plate." },
      { key: "beam_direction", label: "Which side has two beams", type: "select", options: ["-", "+"], when: (s) => s.laser_config !== "single",
        help: "Minus: one beam in front of the wire, two behind. Plus: two in front, one behind." },
      { key: "spot_radius_mm", label: "Spot radius", unit: "mm", step: "0.1", when: (s) => s.laser_config === "single",
        help: "1/e² radius of the single vertical beam." },
      { key: "profile", label: "Profile", type: "select", options: ["gaussian", "tophat"], when: (s) => s.laser_config === "single" },
      { key: "absorptivity_substrate", label: "Plate absorptivity", step: "0.01", help: "Blank uses the material preset. Validation runs use about 0.35." },
      { key: "absorptivity_wire", label: "Wire absorptivity", step: "0.01", help: "Blank uses the material preset. A lower value (0.25) leaves more of the wire unmelted." },
      { key: "alpha_hit", label: "Shadowing threshold", step: "0.05", help: "A ray stops at the first cell this full of metal. Lower means outer strands shade inner ones more." },
      { key: "laser_ramp_ms", label: "Power ramp", unit: "ms", step: "0.5", help: "Time for the laser to reach full power." },
    ],
  },
  {
    id: "wire", title: "Wire",
    blurb: "The wire is real geometry in the model, not a mass source. Gap is the starting space between the tip and the plate.",
    fields: [
      { key: "wire_type", label: "Wire", type: "select", options: ["solid", "stranded"] },
      { key: "wire_diameter_mm", label: "Overall diameter", unit: "mm", step: "0.05", help: "For a fixed strand diameter this is computed from the strands and can be left blank." },
      { key: "feed_angle_deg", label: "Feed angle", unit: "deg", step: "1", help: "90 is straight down, through the laser. 45 comes in from the side." },
      { key: "feed_side", label: "Feed side", type: "select", options: ["front", "back"], help: "Front means the wire arrives from the direction the plate is coming from." },
      { key: "wire_aim_mm", label: "Aim offset", unit: "mm", step: "0.1", help: "Shifts where the wire axis meets the plate, relative to the laser." },
      { key: "wire_gap_mm", label: "Tip gap", unit: "mm", step: "0.01", help: "0 means the tip starts on the plate. A gap lets the tip melt in the air and ball." },
      { key: "feed_start_s", label: "Feed starts at", unit: "s", step: "0.01", help: "0 feeds immediately. A delay holds the wire still while the laser preheats it." },
      { key: "strands", label: "Strand count", step: "1", when: (s) => s.wire_type === "stranded" },
      { key: "strand_layout", label: "Layout", type: "select", options: ["auto", "ring", "centre"], when: (s) => s.wire_type === "stranded",
        help: "Ring puts every strand on one circle. Centre adds a strand in the middle when the count allows." },
      { key: "strand_diameter_mm", label: "Strand diameter", unit: "mm", step: "0.05", when: (s) => s.wire_type === "stranded",
        help: "Blank fits equal strands inside the overall diameter. 0.3 mm is the Fe/Ni wire." },
      { key: "strand_gap_mm", label: "Gap between strands", unit: "mm", step: "0.01", when: (s) => s.wire_type === "stranded" },
      { key: "lay_length_mm", label: "Lay length", unit: "mm", step: "0.5", when: (s) => s.wire_type === "stranded",
        help: "Axial distance of one full twist. Blank uses 10× the wire diameter." },
      { key: "lay_direction", label: "Lay", type: "select", options: ["right", "left"], when: (s) => s.wire_type === "stranded" },
      { key: "strand_feed_basis", label: "Feed basis", type: "select", options: ["metal", "wfs"], when: (s) => s.wire_type === "stranded",
        help: "Metal raises the feed so the volume of metal per second matches a solid wire of the reference diameter." },
      { key: "strand_materials", label: "Strand materials", type: "text", when: (s) => s.wire_type === "stranded",
        help: "Comma list, one per strand, for example Fe,Ni,Fe,Ni,Fe. Blank means every strand is the wire material." },
      { key: "max_wfs_mm_s", label: "Feed cap", unit: "mm/s", step: "1", when: (s) => s.wire_type === "stranded" },
    ],
  },
  {
    id: "materials", title: "Materials",
    blurb: "Properties come from materials.py. Changing a name here picks that preset. Editing a number inside materials.py needs a new case, not a solver rebuild.",
    fields: [
      { key: "wire_material", label: "Wire material", type: "select", options: MATERIALS },
      { key: "substrate_material", label: "Plate material", type: "select", options: MATERIALS },
      { key: "preheat_k", label: "Starting temperature", unit: "K", step: "10" },
      { key: "strand_k_factor", label: "Strand conductivity factor", step: "0.05", when: (s) => s.wire_type === "stranded",
        help: "1 is the full solid conductivity. 0.4 weakens heat flow from strand to strand." },
      { key: "unmelted_k_factor", label: "Unmelted-wire conductivity factor", step: "0.05", when: (s) => s.wire_type === "stranded",
        help: "Extra reduction inside wire that has never melted." },
      { key: "liquidus", label: "Melting range", type: "select", options: ["table", "mixture"], when: (s) => s.wire_type === "stranded",
        help: "Table uses the Fe–Ni diagram. Mixture blends the pure melting points." },
      { key: "liquidus_unmixed", label: "Stay pure until mixed", step: "0.05", when: (s) => s.wire_type === "stranded",
        help: "Blank uses the mixture everywhere. 0.85 keeps a cell that is mostly Fe at iron’s melting point." },
    ],
  },
  {
    id: "mesh", title: "Domain and mesh",
    blurb: "The box is small on purpose: a few millimetres around the pool. Finer cells make a smaller time step and a much longer run.",
    fields: [
      { key: "resolution", label: "Resolution", type: "select", options: ["coarse", "medium", "fine"],
        help: "Coarse 150 µm, medium 100 µm, fine 75 µm. A number below overrides this." },
      { key: "dx_um", label: "Cell size override", unit: "µm", step: "5", help: "Blank uses the resolution above." },
      { key: "wire_refine", label: "Extra refinement at the wire", step: "1",
        help: "Blank: one level for stranded wire (cells cut in half), none for solid wire. Each level quarters the cell face." },
      { key: "domain_y", label: "Width", type: "select", options: ["auto", "half", "full"],
        help: "Half keeps y ≥ 0 and mirrors it. A twisted wire has no mirror, so auto uses the full width." },
      { key: "upstream_mm", label: "Upstream of the laser", unit: "mm", step: "0.5" },
      { key: "downstream_mm", label: "Downstream of the laser", unit: "mm", step: "0.5" },
      { key: "half_width_mm", label: "Half width", unit: "mm", step: "0.5" },
      { key: "substrate_mm", label: "Plate thickness", unit: "mm", step: "0.5" },
      { key: "gas_height_mm", label: "Gas above the plate", unit: "mm", step: "0.5" },
      { key: "np", label: "CPU cores", step: "1", help: "MPI ranks. 4 or 8 is typical on this PC." },
    ],
  },
  {
    id: "time", title: "Time step",
    blurb: "You do not set a fixed step. The solver shrinks or grows it every iteration, and it will not go past the capillary ceiling.",
    fields: [
      { key: "capillary_dt_factor", label: "Capillary factor", step: "0.05",
        help: "0.8 is the stable default. Higher allows a larger step and is more likely to make the surface wobble or crash. Applied on the next case, not on a run that has already started." },
      { key: "max_co", label: "Max Courant number", step: "0.05",
        help: "A second ceiling, from how far the metal moves in one step. It only bites when the capillary limit is not already smaller." },
      { key: "write_interval_s", label: "Snapshot every", unit: "s", step: "0.01",
        help: "How often a 3D frame is saved for ParaView. This does not change the solver step. 0.01 s of simulation time is the usual spacing." },
    ],
  },
  {
    id: "physics", title: "Physics switches",
    blurb: "These turn pieces of the model off. Leave them on unless you are testing what that piece does.",
    fields: [
      { key: "no_marangoni", label: "Turn off Marangoni flow", type: "check" },
      { key: "no_recoil", label: "Turn off recoil pressure", type: "check" },
      { key: "no_evaporation", label: "Turn off evaporation cooling", type: "check" },
      { key: "no_radiation", label: "Turn off radiation loss", type: "check" },
      { key: "no_convection", label: "Turn off gas convection loss", type: "check" },
      { key: "buoyancy", label: "Add buoyancy in the liquid", type: "check" },
      { key: "no_shadowing", label: "Let the beam pass through the wire", type: "check" },
      { key: "gas_viscosity_factor", label: "Argon viscosity multiplier", step: "1",
        help: "20 damps useless gas swirls so the step can be larger. 1 is the real gas." },
      { key: "mushy_C", label: "Mushy-zone drag", step: "1e7",
        help: "How firmly solid metal is held to the plate speed or the feed speed." },
    ],
  },
];

let state = preset({});
let scene = null;
let groupId = "process";
let selectedPart = "wire";
let cam = { az: -0.55, el: 0.42, zoom: 1 };
let drag = null;
let previewTimer = null;

const $ = (id) => document.getElementById(id);

function fmt(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a !== 0 && (a < 0.001 || a >= 10000)) return n.toExponential(2);
  return n.toFixed(digits);
}

function sciTime(s) {
  if (!s) return "—";
  if (s < 1e-3) return `${(s * 1e6).toFixed(1)} µs`;
  if (s < 1) return `${(s * 1e3).toFixed(2)} ms`;
  return `${s.toFixed(2)} s`;
}

function fillPresetSelect() {
  const sel = $("preset");
  sel.innerHTML = "";
  Object.keys(PRESETS).forEach((name) => {
    const o = document.createElement("option");
    o.value = name;
    o.textContent = name;
    sel.appendChild(o);
  });
}

function renderTree() {
  const nav = $("tree");
  nav.innerHTML = "<h3>Model</h3>";
  GROUPS.forEach((g) => {
    const b = document.createElement("button");
    b.textContent = g.title;
    b.className = g.id === groupId ? "on" : "";
    b.onclick = () => { groupId = g.id; renderTree(); renderFields(); };
    nav.appendChild(b);
  });
  nav.insertAdjacentHTML("beforeend", "<h3>Geometry</h3>");
  const parts = geometryParts();
  parts.forEach((p) => {
    const b = document.createElement("button");
    b.className = "part" + (selectedPart === p.id ? " on" : "");
    b.innerHTML = `${p.title}<small>${p.detail}</small>`;
    b.onclick = () => { selectedPart = p.id; renderTree(); draw(); };
    nav.appendChild(b);
  });
}

function geometryParts() {
  if (!scene || !scene.ok) {
    return [{ id: "domain", title: "Domain", detail: "waiting for a valid model" }];
  }
  const d = scene.domain;
  const parts = [
    { id: "domain", title: "Domain", detail: `${fmt(d.x1 - d.x0, 1)} × ${fmt(d.y1 - d.y0, 1)} × ${fmt(d.z1 - d.z0, 1)} mm` },
    { id: "plate", title: "Plate", detail: `${scene.derived.substrate_material}, ${fmt(Math.abs(d.z0), 1)} mm thick` },
    { id: "wire", title: "Wire", detail: scene.derived.n_strands ? `${scene.derived.n_strands} strands, ${fmt(scene.derived.strand_mm, 2)} mm` : `${fmt(scene.derived.wire_mm, 2)} mm solid` },
  ];
  (scene.beams || []).forEach((b, i) => {
    parts.push({ id: "beam" + i, title: `Beam ${i + 1}`, detail: `${b.power.toFixed(0)} W, spot Ø ${fmt(2 * (b.spot_plate || b.radius), 2)} mm on the plate` });
  });
  if (scene.refine) parts.push({ id: "refine", title: "Fine cells", detail: `${scene.derived.dx_min_um.toFixed(0)} µm around the wire` });
  return parts;
}

function renderFields() {
  const g = GROUPS.find((x) => x.id === groupId);
  $("groupTitle").textContent = g.title;
  $("groupBlurb").textContent = g.blurb;
  const form = $("fields");
  form.innerHTML = "";
  if (g.id === "time") {
    const note = document.createElement("div");
    note.className = "time-note";
    const dt = scene && scene.ok ? scene.derived.capillary_dt_s : null;
    const steps = scene && scene.ok ? scene.derived.steps : null;
    note.innerHTML = dt
      ? `With these cells the step will sit near <b>${sciTime(dt)}</b>. Reaching the end takes about <b>${steps ? steps.toLocaleString() : "—"}</b> steps. A coarser mesh is what makes that number smaller. The run already on this PC will not change.`
      : "The capillary ceiling appears here once the model checks out.";
    form.appendChild(note);
  }
  g.fields.forEach((f) => {
    if (f.when && !f.when(state)) return;
    const wrap = document.createElement("div");
    wrap.className = "field" + (f.type === "check" ? " check" : "");
    if (f.type === "check") {
      wrap.innerHTML = `<input type="checkbox" id="f_${f.key}"><label for="f_${f.key}">${f.label}</label>`;
      wrap.querySelector("input").checked = !!state[f.key];
    } else if (f.type === "select") {
      wrap.innerHTML = `<label>${f.label}</label><select id="f_${f.key}"></select>` + (f.help ? `<p class="help">${f.help}</p>` : "");
      const sel = wrap.querySelector("select");
      f.options.forEach((op) => {
        const o = document.createElement("option");
        o.value = op;
        o.textContent = op;
        sel.appendChild(o);
      });
      sel.value = state[f.key];
    } else {
      const unit = f.unit ? ` <span class="unit">${f.unit}</span>` : "";
      wrap.innerHTML = `<label>${f.label}${unit}</label><input id="f_${f.key}" ${f.type === "text" ? 'type="text"' : 'type="number"'} step="${f.step || "any"}" value="${state[f.key] ?? ""}">` + (f.help ? `<p class="help">${f.help}</p>` : "");
    }
    const input = wrap.querySelector("input, select");
    input.addEventListener("input", () => {
      if (f.type === "check") state[f.key] = input.checked;
      else if (f.type === "select" || f.type === "text") state[f.key] = input.value;
      else state[f.key] = input.value === "" ? "" : Number(input.value);
      schedulePreview();
      if (f.key === "wire_type" || f.key === "laser_config") renderFields();
    });
    form.appendChild(wrap);
  });
}

function payload() {
  const body = Object.assign({}, state);
  body.case = $("caseName").value.trim() || "studio_case";
  return body;
}

function schedulePreview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, 160);
}

async function runPreview() {
  let data;
  try {
    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    data = await res.json();
  } catch (err) {
    $("banner").hidden = false;
    $("banner").textContent = "The studio lost contact with its Python server. Leave the server window open.";
    return;
  }
  if (!data.ok) {
    $("banner").hidden = false;
    $("banner").textContent = data.error || "These settings do not make a valid case.";
    $("headline").textContent = "The picture is the last valid model.";
    return;
  }
  $("banner").hidden = true;
  scene = data;
  $("headline").textContent = data.one_line;
  renderDerived();
  renderTree();
  draw();
  drawSection();
}

function renderDerived() {
  const d = scene.derived;
  const dom = scene.domain;
  $("derived").innerHTML =
    `<b>${d.cells.toLocaleString()}</b> cells · ${d.dx_um.toFixed(0)} µm` +
    (d.dx_min_um < d.dx_um ? ` (${d.dx_min_um.toFixed(0)} µm at the wire)` : "") +
    ` · step ceiling <b>${sciTime(d.capillary_dt_s)}</b>` +
    ` · track <b>${fmt(d.track_mm, 1)} mm</b> in ${fmt(d.end_s, 2)} s` +
    ` · bead area <b>${fmt(d.bead_mm2, 2)} mm²</b>` +
    ` · spot on plate <b>Ø ${fmt(d.spot_plate_mm, 2)} mm</b>` +
    ` · feed used <b>${fmt(d.wfs_mm_s, 1)} mm/s</b>` +
    (Math.abs(d.wfs_mm_s - d.wfs_nominal_mm_s) > 0.05 ? ` (nominal ${fmt(d.wfs_nominal_mm_s, 1)})` : "") +
    `<br>Domain ${fmt(dom.x1 - dom.x0, 1)} mm along the track` +
    (dom.half ? ", mirrored about the centreline" : ", full width") +
    (scene.notes ? `<br><span style="color:#8a5a12">${scene.notes.replace(/\n/g, " · ")}</span>` : "");
  $("legend").innerHTML =
    `Plate top is z = 0.<br>Orange is the laser.<br>` +
    (dom.half ? "Only the near half is meshed; the far half is a mirror." : "Full width, no mirror.");
}

const canvas = $("view");
const ctx = canvas.getContext("2d");

function resize() {
  const r = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, r.width * scale);
  canvas.height = Math.max(1, r.height * scale);
  draw();
}

function projectAll(points) {
  if (!scene || !scene.ok) return { pts: [], scale: 1, ox: 0, oy: 0 };
  const d = scene.domain;
  const cx = (d.x0 + d.x1) / 2, cy = (d.y0 + d.y1) / 2, cz = (d.z0 + d.z1) / 2;
  const ca = Math.cos(cam.az), sa = Math.sin(cam.az);
  const ce = Math.cos(cam.el), se = Math.sin(cam.el);
  const rot = (p) => {
    const x = p[0] - cx, y = p[1] - cy, z = p[2] - cz;
    const x1 = ca * x - sa * y, y1 = sa * x + ca * y;
    const y2 = ce * y1 - se * z, z2 = se * y1 + ce * z;
    return [x1, -y2, z2];
  };
  const corners = [
    [d.x0, d.y0, d.z0], [d.x1, d.y0, d.z0], [d.x0, d.y1, d.z0], [d.x1, d.y1, d.z0],
    [d.x0, d.y0, d.z1], [d.x1, d.y0, d.z1], [d.x0, d.y1, d.z1], [d.x1, d.y1, d.z1],
  ].map(rot);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  corners.forEach((p) => {
    minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]);
    minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]);
  });
  const pad = 54 * (window.devicePixelRatio || 1);
  const scale = cam.zoom * Math.min(
    (canvas.width - pad * 2) / Math.max(maxX - minX, 0.1),
    (canvas.height - pad * 2) / Math.max(maxY - minY, 0.1),
  );
  const ox = canvas.width / 2 - scale * (minX + maxX) / 2;
  const oy = canvas.height / 2 - scale * (minY + maxY) / 2;
  return {
    pts: points.map((p) => {
      const r = rot(p);
      return { x: ox + scale * r[0], y: oy + scale * r[1], z: r[2], w: p };
    }),
    scale, rot, ox, oy,
  };
}

function boxEdges(d) {
  const c = [
    [d.x0, d.y0, d.z0], [d.x1, d.y0, d.z0], [d.x1, d.y1, d.z0], [d.x0, d.y1, d.z0],
    [d.x0, d.y0, d.z1], [d.x1, d.y0, d.z1], [d.x1, d.y1, d.z1], [d.x0, d.y1, d.z1],
  ];
  const e = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]];
  return e.map(([a, b]) => [c[a], c[b]]);
}

function face(d, z) {
  return [[d.x0, d.y0, z], [d.x1, d.y0, z], [d.x1, d.y1, z], [d.x0, d.y1, z]];
}

function draw() {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#14181f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!scene || !scene.ok) return;
  const d = scene.domain;
  const hi = selectedPart;

  function poly(pts, fill, stroke) {
    const p = projectAll(pts).pts;
    ctx.beginPath();
    p.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y)));
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); }
  }
  function lines(pairs, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    pairs.forEach(([a, b]) => {
      const p = projectAll([a, b]).pts;
      ctx.beginPath();
      ctx.moveTo(p[0].x, p[0].y);
      ctx.lineTo(p[1].x, p[1].y);
      ctx.stroke();
    });
  }

  poly(face(d, 0), hi === "plate" ? "rgba(196,164,106,0.55)" : "rgba(90,108,128,0.55)", "rgba(210,220,230,0.35)");
  poly(face(d, d.z0), "rgba(60,72,88,0.35)", null);
  lines(boxEdges(d), hi === "domain" ? "#f0d7b0" : "rgba(232,226,214,0.55)", hi === "domain" ? 2.2 : 1.2);

  if (d.half) {
    lines([[[d.x0, 0, d.z0], [d.x1, 0, d.z0]], [[d.x0, 0, 0], [d.x1, 0, 0]], [[d.x0, 0, d.z1], [d.x1, 0, d.z1]]], "rgba(140,170,210,0.35)", 1);
  }

  if (scene.refine) {
    const r = scene.refine;
    const box = {
      x0: r.x0, x1: r.x1, y0: r.y0, y1: r.y1, z0: d.z0, z1: d.z1,
    };
    lines(boxEdges(box), hi === "refine" ? "#9ad7ff" : "rgba(120,180,220,0.35)", hi === "refine" ? 2 : 1);
  }

  const disks = [];
  (scene.strands || []).forEach((s) => {
    s.line.forEach((p) => disks.push({ p, r: s.radius, color: s.color, kind: "wire" }));
  });
  (scene.beams || []).forEach((b, i) => {
    (b.stations || []).forEach((st) => disks.push({
      p: st.c, r: st.r, color: "rgba(255,176,70,0.22)", kind: "beam" + i, ring: true,
    }));
    disks.push({ p: b.focus, r: 0.12, color: "#ffb703", kind: "beam" + i });
  });
  const proj = projectAll(disks.map((o) => o.p));
  disks.forEach((o, i) => { o.s = proj.pts[i]; o.px = proj.scale * o.r; });
  disks.sort((a, b) => a.s.z - b.s.z);
  disks.forEach((o) => {
    const on = (o.kind === "wire" && hi === "wire") || hi === o.kind;
    ctx.beginPath();
    ctx.arc(o.s.x, o.s.y, Math.max(1.5, o.px), 0, Math.PI * 2);
    ctx.fillStyle = o.color;
    ctx.globalAlpha = o.ring ? (on ? 0.45 : 0.18) : 0.92;
    ctx.fill();
    if (on && !o.ring) {
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#fff6e8";
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  });

  (scene.beams || []).forEach((b, i) => {
    const stations = b.stations || [];
    if (!stations.length) return;
    const ends = projectAll([stations[0].c, b.focus, stations[stations.length - 1].c]).pts;
    const on = hi === "beam" + i;
    ctx.strokeStyle = on ? "#ffe1a8" : "rgba(255, 186, 72, 0.95)";
    ctx.lineWidth = on ? 3 : 1.8;
    ctx.beginPath();
    ctx.moveTo(ends[0].x, ends[0].y);
    ctx.lineTo(ends[1].x, ends[1].y);
    ctx.lineTo(ends[2].x, ends[2].y);
    ctx.stroke();
  });

  // Travel arrow on the plate.
  const arrow = projectAll([[d.x0 + 0.4, (d.y0 + d.y1) / 2, 0.05], [d.x0 + 1.6, (d.y0 + d.y1) / 2, 0.05]]).pts;
  ctx.strokeStyle = "#9be7c4";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(arrow[0].x, arrow[0].y);
  ctx.lineTo(arrow[1].x, arrow[1].y);
  ctx.stroke();
  ctx.fillStyle = "#9be7c4";
  ctx.font = `${13 * (window.devicePixelRatio || 1)}px Segoe UI`;
  ctx.fillText("plate moves →", arrow[0].x, arrow[0].y - 8);
}

function drawSection() {
  const c = $("section");
  const g = c.getContext("2d");
  const scale = window.devicePixelRatio || 1;
  c.width = 180 * scale;
  c.height = 180 * scale;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, c.width, c.height);
  g.fillStyle = "#10141a";
  g.fillRect(0, 0, c.width, c.height);
  if (!scene || !scene.ok) return;
  const secs = scene.section || [];
  const R = Math.max(scene.envelope_radius || 0.5, ...secs.map((s) => Math.hypot(s.x, s.y) + s.r), 0.2);
  const pix = (0.38 * c.width) / R;
  const ox = c.width / 2, oy = c.height / 2;
  g.strokeStyle = "rgba(255,255,255,0.25)";
  g.lineWidth = 1;
  g.beginPath();
  g.arc(ox, oy, pix * (scene.envelope_radius || R), 0, Math.PI * 2);
  g.stroke();
  secs.forEach((s) => {
    g.beginPath();
    g.arc(ox + pix * s.x, oy - pix * s.y, Math.max(2, pix * s.r), 0, Math.PI * 2);
    g.fillStyle = s.color;
    g.fill();
    g.fillStyle = "#1b140f";
    g.font = `${11 * scale}px Segoe UI`;
    g.textAlign = "center";
    g.fillText(s.name, ox + pix * s.x, oy - pix * s.y + 4 * scale);
  });
}

function setView(name) {
  const views = {
    iso: { az: -0.55, el: 0.42 },
    side: { az: -Math.PI / 2, el: 0.08 },
    front: { az: Math.PI, el: 0.08 },
    top: { az: -Math.PI / 2, el: Math.PI / 2 - 0.02 },
  };
  Object.assign(cam, views[name] || views.iso);
  cam.zoom = 1;
  document.querySelectorAll(".viewbar button").forEach((b) => b.classList.toggle("on", b.dataset.view === name));
  draw();
}

canvas.addEventListener("pointerdown", (ev) => {
  drag = { x: ev.clientX, y: ev.clientY, az: cam.az, el: cam.el, moved: false };
  canvas.setPointerCapture(ev.pointerId);
});
canvas.addEventListener("pointermove", (ev) => {
  if (!drag) return;
  const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
  if (Math.hypot(dx, dy) > 3) drag.moved = true;
  cam.az = drag.az + dx * 0.01;
  cam.el = Math.max(-1.2, Math.min(1.35, drag.el + dy * 0.01));
  document.querySelectorAll(".viewbar button").forEach((b) => b.classList.remove("on"));
  draw();
});
canvas.addEventListener("pointerup", (ev) => {
  if (drag && !drag.moved) pick(ev);
  drag = null;
});
canvas.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  cam.zoom *= ev.deltaY > 0 ? 0.92 : 1.08;
  cam.zoom = Math.max(0.4, Math.min(6, cam.zoom));
  draw();
}, { passive: false });

function pick(ev) {
  if (!scene || !scene.ok) return;
  const rect = canvas.getBoundingClientRect();
  const scale = canvas.width / rect.width;
  const x = (ev.clientX - rect.left) * scale;
  const y = (ev.clientY - rect.top) * scale;
  const anchors = [{ id: "wire", p: scene.wire_tip }, { id: "plate", p: [0, 0, 0] }, { id: "domain", p: scene.origin }];
  (scene.beams || []).forEach((b, i) => anchors.push({ id: "beam" + i, p: b.focus }));
  let best = null;
  anchors.forEach((a) => {
    const q = projectAll([a.p]).pts[0];
    const dist = Math.hypot(q.x - x, q.y - y);
    if (!best || dist < best.dist) best = { id: a.id, dist };
  });
  if (best && best.dist < 40 * scale) {
    selectedPart = best.id;
    renderTree();
    draw();
  }
}

async function launch(steps) {
  const name = $("caseName").value.trim();
  if (!name) { alert("Type a new case name first."); return; }
  if (steps !== "generate") {
    const ok = confirm(
      steps === "mesh"
        ? `Build the mesh for “${name}” in WSL? This does not start the solver.`
        : `Start “${name}” on this PC? A full track can take many hours. The run already going is left alone if the name is different.`
    );
    if (!ok) return;
  }
  const buttons = document.querySelectorAll(".actions button");
  buttons.forEach((b) => { b.disabled = true; });
  $("status").textContent = steps === "generate" ? "Writing the case…" : "Starting the job…";
  try {
    const res = await fetch("/api/launch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ steps, model: payload() }),
    });
    const data = await res.json();
    $("status").className = "status" + (data.ok ? "" : " bad");
    $("status").textContent = data.ok ? data.text : (data.error || "The job did not start.");
  } catch (err) {
    $("status").className = "status bad";
    $("status").textContent = "Could not reach the studio server.";
  }
  buttons.forEach((b) => { b.disabled = false; });
}

async function pollStatus() {
  try {
    const res = await fetch("/api/status?case=" + encodeURIComponent($("caseName").value.trim()));
    const data = await res.json();
    if (!data.ok || !data.focus) return;
    const f = data.focus;
    const el = $("status");
    if (f.stage === "running") {
      el.className = "status running";
      el.textContent = `${f.name} is running on this PC. ${f.progress_caption}. ${f.facts.eta}. Pool: ${f.facts.pool}. Changing the form does not affect it.`;
    } else if (f.stage === "finished") {
      el.className = "status";
      el.textContent = `${f.name} has finished. ${f.next_step}`;
    } else if (f.stage === "absent") {
      el.className = "status";
      el.textContent = "No solver is running. Write a case, then Run solver. ParaView (Open_in_ParaView.bat) is how you rotate and play a finished or running result.";
    } else {
      el.className = "status";
      el.textContent = `${f.name}: ${f.headline} ${f.facts.clock}.`;
    }
  } catch (err) {
    /* server still coming up */
  }
}

document.querySelectorAll(".viewbar button").forEach((b) => {
  b.onclick = () => setView(b.dataset.view);
});
$("preset").onchange = () => {
  state = preset(PRESETS[$("preset").value]);
  renderFields();
  schedulePreview();
};
$("caseName").addEventListener("input", () => { state.case = $("caseName").value; });
$("btnCheck").onclick = () => runPreview();
$("btnWrite").onclick = () => launch("generate");
$("btnMesh").onclick = () => launch("mesh");
$("btnRun").onclick = () => launch("all");

fillPresetSelect();
$("preset").value = "Transitional-R, solid wire";
renderTree();
renderFields();
new ResizeObserver(resize).observe(canvas.parentElement);
runPreview();
pollStatus();
setInterval(pollStatus, 8000);
