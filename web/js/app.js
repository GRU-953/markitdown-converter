"use strict";

/* ── State ──────────────────────────────────────────────────────────────── */
let cfg = { theme: "System", palette: "indigo", ocr_language: "English",
            auto_ocr: true, auto_bijoy: true };
let files = [];          // {path, name, is_image, status, text, steps, error}
let selected = -1;
let ocrPath = null;
let outMode = "preview"; // preview | edit
const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

/* ── Boot ───────────────────────────────────────────────────────────────── */
function boot() {
  if (!window.pywebview || !window.pywebview.api) {
    return window.addEventListener("pywebviewready", start, { once: true });
  }
  start();
}
async function start() {
  try { cfg = Object.assign(cfg, await api().get_config()); } catch (e) {}
  applyTheme(); applyPalette();
  wireNav(); wireMode(); wirePalette(); wireConvert(); wireOcr(); wireBijoy();
  wireHistory(); wireSettings();
  syncSettingsControls();
  renderFiles(); renderOutput();
  checkForUpdate();
}

async function checkForUpdate() {
  try {
    const info = await api().check_update();
    if (!info || !info.has_update) return;
    const banner = document.getElementById("update-banner");
    const msg = document.getElementById("update-msg");
    const link = document.getElementById("update-link");
    msg.textContent = `Update available: ${info.latest}`;
    link.href = info.url;
    link.onclick = (e) => { e.preventDefault(); window.open(info.url); };
    banner.style.display = "flex";
  } catch (e) {}
}

/* ── Theme + palette ──────────────────────────────────────────────────────── */
function resolveMode(theme) {
  if (theme === "System") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return theme.toLowerCase();
}
function applyTheme() {
  document.documentElement.setAttribute("data-mode", resolveMode(cfg.theme));
  document.querySelectorAll("#mode-seg button").forEach(b =>
    b.classList.toggle("active", b.dataset.mode === cfg.theme));
}
function applyPalette() {
  document.documentElement.setAttribute("data-palette", cfg.palette);
  document.querySelectorAll(".palette-card").forEach(c =>
    c.classList.toggle("active", c.dataset.palette === cfg.palette));
}
function save(patch) { Object.assign(cfg, patch); if (window.pywebview) api().save_config(patch); }

/* ── Navigation ───────────────────────────────────────────────────────────── */
const VIEW_META = {
  convert:  ["Convert",  "Documents, images & spreadsheets → Markdown"],
  ocr:      ["OCR",      "Extract text from images (English + Bengali)"],
  bijoy:    ["Bijoy → Unicode", "Convert legacy SutonnyMJ text to Unicode"],
  history:  ["History",  "Your recent conversions"],
  settings: ["Settings", "Appearance & smart-conversion options"],
};
function wireNav() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
}
function switchView(v) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  document.querySelectorAll(".view").forEach(s => s.classList.remove("active"));
  const sec = $("view-" + v); sec.classList.add("active"); sec.classList.add("fade-in");
  setTimeout(() => sec.classList.remove("fade-in"), 300);
  $("view-title").textContent = VIEW_META[v][0];
  $("view-sub").textContent = VIEW_META[v][1];
  if (v === "history") renderHistory();
}

function wireMode() {
  document.querySelectorAll("#mode-seg button").forEach(b =>
    b.addEventListener("click", () => { save({ theme: b.dataset.mode }); applyTheme(); }));
  window.matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => { if (cfg.theme === "System") applyTheme(); });
}
function wirePalette() {
  document.querySelectorAll(".palette-card").forEach(c =>
    c.addEventListener("click", () => { save({ palette: c.dataset.palette }); applyPalette(); }));
}

/* ── Convert view ─────────────────────────────────────────────────────────── */
function wireConvert() {
  $("dropzone").addEventListener("click", addFiles);
  setupDrop($("dropzone"), addFiles, onFilesDropped);
  $("convert-btn").addEventListener("click", convertAll);
  $("clear-btn").addEventListener("click", clearFiles);
  $("retry-btn").addEventListener("click", retryFailed);
  $("copy-btn").addEventListener("click", () => copyText(currentText()));
  $("export-btn").addEventListener("click", exportCurrent);
  $("export-all-btn").addEventListener("click", exportAll);
  document.querySelectorAll("#out-tabs button").forEach(b =>
    b.addEventListener("click", () => setOutMode(b.dataset.tab)));
  $("editor").addEventListener("input", () => {
    if (selected >= 0) files[selected].text = $("editor").value;
  });
}
async function addFiles() {
  try {
    const picked = await api().pick_files();
    addMetas(picked);
  } catch (e) { toast("Could not open file picker", "err"); }
}
async function onFilesDropped(paths) {
  try { addMetas(await api().add_dropped(paths)); }
  catch (e) { toast("Drop failed — click to browse instead", "err"); }
}
function addMetas(metas) {
  let added = 0;
  (metas || []).forEach(m => {
    if (!files.some(f => f.path === m.path)) {
      files.push({ ...m, status: "pending", text: "", steps: [], error: "" });
      added++;
    }
  });
  if (added) { renderFiles(); }
}
function clearFiles() { files = []; selected = -1; renderFiles(); renderOutput(); }

async function convertAll() {
  const todo = files.filter(f => f.status === "pending" || f.status === "error");
  if (!todo.length) return toast("Nothing to convert", "err");
  $("convert-btn").disabled = true;
  for (const f of files) {
    if (f.status !== "pending" && f.status !== "error") continue;
    f.status = "doing"; f.error = ""; renderFiles();
    const res = await api().convert(f.path);
    if (res.ok) { f.status = "done"; f.text = res.text; f.steps = res.steps; }
    else { f.status = "error"; f.error = res.error; }
    renderFiles();
    if (selected === files.indexOf(f) || selected < 0) selectFile(files.indexOf(f));
  }
  $("convert-btn").disabled = false;
  const ok = files.filter(f => f.status === "done").length;
  const err = files.filter(f => f.status === "error").length;
  toast(err ? `${ok} converted, ${err} failed` : `All ${ok} converted`, err ? "err" : "ok");
}
function retryFailed() { convertAll(); }

const STEP_LABEL = { markitdown: "MarkItDown", ocr: "OCR", bijoy: "Bijoy→Unicode" };
const STAT_ICON = { pending: "ti-circle", doing: "ti-loader-2", done: "ti-circle-check", error: "ti-alert-circle" };
function renderFiles() {
  $("file-count").textContent = files.length;
  $("retry-btn").disabled = !files.some(f => f.status === "error");
  const list = $("file-list");
  if (!files.length) {
    list.innerHTML = '<div class="empty"><i class="ti ti-files-off"></i>No files yet</div>';
    return;
  }
  list.innerHTML = "";
  files.forEach((f, i) => {
    const row = document.createElement("div");
    row.className = "file-row" + (i === selected ? " selected" : "");
    row.draggable = true;
    const steps = f.steps.length ? f.steps.map(s => STEP_LABEL[s] || s).join(" · ")
                                 : (f.error || (f.is_image ? "image" : "document"));
    row.innerHTML =
      `<div class="ficon"><i class="ti ${f.is_image ? "ti-photo" : "ti-file-text"}"></i></div>
       <div class="fmeta"><div class="fname">${esc(f.name)}</div>
         <div class="fsteps">${esc(steps)}</div>
         ${f.status === "doing" ? '<div class="progress-track"><div class="progress-bar" style="width:65%"></div></div>' : ""}
       </div>
       <i class="ti ${STAT_ICON[f.status]} fstat ${f.status}"></i>
       <i class="ti ti-x fx" data-x="${i}"></i>`;
    row.addEventListener("click", (e) => { if (!e.target.dataset.x) selectFile(i); });
    row.querySelector(".fx").addEventListener("click", () => removeFile(i));
    setupRowDrag(row, i);
    list.appendChild(row);
  });
}
function selectFile(i) { selected = i; renderFiles(); renderOutput(); }
function removeFile(i) {
  files.splice(i, 1);
  if (selected >= files.length) selected = files.length - 1;
  renderFiles(); renderOutput();
}

/* drag-reorder */
let dragIdx = -1;
function setupRowDrag(row, i) {
  row.addEventListener("dragstart", () => { dragIdx = i; row.classList.add("dragging"); });
  row.addEventListener("dragend", () => row.classList.remove("dragging"));
  row.addEventListener("dragover", (e) => e.preventDefault());
  row.addEventListener("drop", (e) => {
    e.preventDefault(); e.stopPropagation();
    if (dragIdx < 0 || dragIdx === i) return;
    const [m] = files.splice(dragIdx, 1);
    files.splice(i, 0, m);
    selected = files.indexOf(m);
    dragIdx = -1; renderFiles(); renderOutput();
  });
}

/* output panel */
function currentText() { return selected >= 0 ? (files[selected].text || "") : ""; }
function setOutMode(m) {
  outMode = m;
  document.querySelectorAll("#out-tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === m));
  renderOutput();
}
function renderOutput() {
  const ed = $("editor"), pv = $("preview");
  const f = selected >= 0 ? files[selected] : null;
  $("out-name").textContent = f ? f.name : "Output";
  const text = f ? (f.text || "") : "";
  if (outMode === "edit") {
    ed.style.display = "block"; pv.style.display = "none"; ed.value = text;
  } else {
    ed.style.display = "none"; pv.style.display = "block";
    pv.innerHTML = text ? marked.parse(text) : '<div class="empty"><i class="ti ti-file-text"></i>Select a converted file</div>';
    pv.classList.toggle("bn", /[ঀ-৿]/.test(text));
  }
}
async function exportCurrent() {
  const f = selected >= 0 ? files[selected] : null;
  if (!f || !f.text) return toast("Nothing to export", "err");
  const fmt = await pickFormat();
  if (!fmt) return;
  const base = f.name.replace(/\.[^.]+$/, "");
  const res = await api().export_text(f.text, fmt, `${base}.${fmt}`);
  if (res.ok) toast("Saved " + res.path.split(/[\\/]/).pop(), "ok");
  else if (!res.cancelled) toast(res.error || "Export failed", "err");
}
async function exportAll() {
  const done = files.filter(f => f.status === "done" && f.text);
  if (!done.length) return toast("No converted files", "err");
  const fmt = await pickFormat();
  if (!fmt) return;
  const res = await api().export_combined(done.map(f => ({ name: f.name, text: f.text })), fmt);
  if (res.ok) toast("Saved combined." + fmt, "ok");
  else if (!res.cancelled) toast(res.error || "Export failed", "err");
}

/* ── OCR view ─────────────────────────────────────────────────────────────── */
function wireOcr() {
  $("ocr-drop").addEventListener("click", pickOcr);
  setupDrop($("ocr-drop"), pickOcr, (paths) => { if (paths[0]) setOcr({ path: paths[0], name: paths[0].split(/[\\/]/).pop() }); });
  document.querySelectorAll("#ocr-lang button").forEach(b =>
    b.addEventListener("click", () => segPick("#ocr-lang", b)));
  $("ocr-run").addEventListener("click", runOcr);
  $("ocr-copy").addEventListener("click", () => copyText($("ocr-out").value));
  $("ocr-export").addEventListener("click", () => saveText($("ocr-out").value, "ocr.txt"));
}
async function pickOcr() {
  try { const m = await api().pick_image(); if (m && m.path) setOcr(m); } catch (e) {}
}
function setOcr(m) { ocrPath = m.path; $("ocr-file").textContent = m.name; }
async function runOcr() {
  if (!ocrPath) return toast("Choose an image first", "err");
  const lang = document.querySelector("#ocr-lang button.active").dataset.lang;
  $("ocr-out").value = "Extracting…";
  const res = await api().ocr(ocrPath, lang, $("ocr-bijoy").checked);
  $("ocr-out").value = res.ok ? res.text : ("Error: " + res.error);
}

/* ── Bijoy view ───────────────────────────────────────────────────────────── */
function wireBijoy() {
  $("bj-in").addEventListener("input", detectBijoy);
  $("bj-run").addEventListener("click", runBijoy);
  $("bj-copy").addEventListener("click", () => copyText($("bj-out").value));
  $("bj-export").addEventListener("click", () => saveText($("bj-out").value, "unicode.txt"));
}
let detectTimer = null;
function detectBijoy() {
  clearTimeout(detectTimer);
  detectTimer = setTimeout(async () => {
    const t = $("bj-in").value.trim();
    const pill = $("bj-detect");
    if (!t) { pill.className = "detect-pill"; pill.textContent = "Type to auto-detect"; return; }
    const s = await api().detect(t);
    const map = { bijoy: "Bijoy detected ✓", unicode_bn: "Already Unicode", latin: "Latin / English", other: "Unrecognised" };
    pill.className = "detect-pill " + s;
    pill.textContent = map[s] || "Unrecognised";
  }, 250);
}
async function runBijoy() {
  const t = $("bj-in").value.trim();
  if (!t) return;
  const res = await api().bijoy_convert(t);
  $("bj-out").value = res.text;
}

/* ── History view ─────────────────────────────────────────────────────────── */
function wireHistory() {
  $("hist-clear").addEventListener("click", async () => { await api().clear_history(); renderHistory(); });
}
async function renderHistory() {
  const items = await api().get_history();
  $("hist-count").textContent = items.length ? `${items.length} conversion${items.length > 1 ? "s" : ""}` : "No conversions yet";
  $("hist-list").innerHTML = items.map(h => {
    const steps = (h.steps || []).map(s => `<span class="badge">${STEP_LABEL[s] || s}</span>`).join("");
    return `<div class="hist-item">
      <div class="hicon ${h.ok ? "ok" : "err"}"><i class="ti ${h.ok ? "ti-check" : "ti-x"}"></i></div>
      <div class="hmeta"><div class="hname">${esc(h.name)}</div>
        <div class="hsub">${esc(h.ts || "")} ${h.ok ? steps : esc(h.error || "failed")}</div></div>
    </div>`;
  }).join("");
}

/* ── Settings controls ─────────────────────────────────────────────────────── */
function wireSettings() {
  $("set-auto-ocr").addEventListener("change", e => save({ auto_ocr: e.target.checked }));
  $("set-auto-bijoy").addEventListener("change", e => save({ auto_bijoy: e.target.checked }));
  document.querySelectorAll("#set-ocr-lang button").forEach(b =>
    b.addEventListener("click", () => { segPick("#set-ocr-lang", b); save({ ocr_language: b.dataset.lang }); }));
}
function syncSettingsControls() {
  $("set-auto-ocr").checked = cfg.auto_ocr !== false;
  $("set-auto-bijoy").checked = cfg.auto_bijoy !== false;
  document.querySelectorAll("#set-ocr-lang button").forEach(b =>
    b.classList.toggle("active", b.dataset.lang === cfg.ocr_language));
}

/* ── Shared helpers ───────────────────────────────────────────────────────── */
function segPick(sel, btn) {
  document.querySelectorAll(sel + " button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}
async function pickFormat() {
  return new Promise(resolve => {
    const wrap = document.createElement("div");
    wrap.style.cssText = "position:absolute;inset:0;background:var(--overlay);display:flex;align-items:center;justify-content:center;z-index:60;";
    wrap.innerHTML = `<div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;box-shadow:var(--shadow);min-width:260px;">
      <div style="font-size:14px;font-weight:600;margin-bottom:14px;">Export format</div>
      <div class="row" style="gap:8px;">
        ${["md", "html", "txt"].map(f => `<button class="btn" data-f="${f}" style="flex:1;justify-content:center;">${f.toUpperCase()}</button>`).join("")}
      </div></div>`;
    document.body.appendChild(wrap);
    wrap.addEventListener("click", e => {
      if (e.target.dataset.f) { resolve(e.target.dataset.f); wrap.remove(); }
      else if (e.target === wrap) { resolve(null); wrap.remove(); }
    });
  });
}
async function copyText(t) {
  if (!t) return toast("Nothing to copy", "err");
  try { await navigator.clipboard.writeText(t); toast("Copied to clipboard", "ok"); }
  catch (e) { toast("Copy failed", "err"); }
}
async function saveText(t, name) {
  if (!t) return toast("Nothing to save", "err");
  const res = await api().export_text(t, "txt", name);
  if (res.ok) toast("Saved " + res.path.split(/[\\/]/).pop(), "ok");
  else if (!res.cancelled) toast(res.error || "Save failed", "err");
}
function setupDrop(el, onClick, onPaths) {
  el.addEventListener("dragover", e => { e.preventDefault(); el.classList.add("drag"); });
  el.addEventListener("dragleave", () => el.classList.remove("drag"));
  el.addEventListener("drop", e => {
    e.preventDefault(); el.classList.remove("drag");
    const paths = [];
    for (const f of e.dataTransfer.files) {
      const p = f.pywebviewFullPath || f.path || "";
      if (p) paths.push(p);
    }
    if (paths.length) onPaths(paths);
    else toast("Drag-drop unavailable — click to browse", "err");
  });
}
function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function toast(msg, kind) {
  const t = document.createElement("div");
  t.className = "toast " + (kind || "");
  t.innerHTML = `<i class="ti ${kind === "ok" ? "ti-check" : kind === "err" ? "ti-alert-triangle" : "ti-info-circle"}"></i>${esc(msg)}`;
  $("toasts").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 300); }, 2600);
}

boot();
