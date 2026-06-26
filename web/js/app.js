"use strict";

/* ── State ──────────────────────────────────────────────────────────────── */
let cfg = { theme: "System", palette: "indigo", language: "en",
            ocr_language: "English", auto_ocr: true, auto_bijoy: true,
            use_windows_colors: false };
let files = [];          // {path, name, is_image, status, text, steps, error}
let selected = -1;
let outMode = "preview"; // preview | edit
let LOCALES = {};        // { en: {...}, bn: {...} }
let lang = "en";         // active UI language
let _updateInfo = null;  // cached update info for banner re-render on lang switch
const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

/* ── i18n ─────────────────────────────────────────────────────────────────── */
function hasKey(key) {
  return (LOCALES[lang] && key in LOCALES[lang]) || (LOCALES.en && key in LOCALES.en);
}
function t(key, vars) {
  const dict = LOCALES[lang] || {};
  const fallback = LOCALES.en || {};
  let s = (key in dict ? dict[key] : (key in fallback ? fallback[key] : key));
  if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}
function applyI18n(root) {
  const scope = root || document;
  // When locales failed to load, leave the English HTML defaults untouched.
  scope.querySelectorAll("[data-i18n]").forEach(el => { if (hasKey(el.dataset.i18n)) el.textContent = t(el.dataset.i18n); });
  scope.querySelectorAll("[data-i18n-ph]").forEach(el => { if (hasKey(el.dataset.i18nPh)) el.placeholder = t(el.dataset.i18nPh); });
  scope.querySelectorAll("[data-i18n-title]").forEach(el => {
    if (!hasKey(el.dataset.i18nTitle)) return;
    const v = t(el.dataset.i18nTitle); el.title = v; el.setAttribute("aria-label", v);
  });
}
function applyLang() {
  document.documentElement.setAttribute("lang", lang === "bn" ? "bn" : "en");
  document.documentElement.setAttribute("data-lang", lang);
  document.querySelectorAll("#lang-seg button").forEach(b => {
    const on = b.dataset.lang === lang;
    b.classList.toggle("active", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
  });
  applyI18n();
  // Re-render anything whose text is built in JS.
  renderFiles();
  renderOutput();
  refreshDetectPill();
  populateAbout();
  renderUpdateBanner();
  const histView = $("view-history");
  if (histView && histView.classList.contains("active")) renderHistory();
}

/* ── Boot ───────────────────────────────────────────────────────────────── */
function boot() {
  if (!window.pywebview || !window.pywebview.api) {
    return window.addEventListener("pywebviewready", start, { once: true });
  }
  start();
}
async function start() {
  try { cfg = Object.assign(cfg, await api().get_config()); } catch (e) {}
  try { LOCALES = await api().get_locales(); } catch (e) { LOCALES = {}; }
  lang = (cfg.language === "bn") ? "bn" : "en";
  applyTheme(); applyPalette();
  wireNav(); wireMode(); wireLang(); wirePalette(); wireConvert(); wireBijoy();
  wireHistory(); wireSettings(); wireOffline();
  syncSettingsControls();
  applyLang();
  renderFiles(); renderOutput();
  await applyWindowsColors();
  checkForUpdate();
  if (!cfg.onboarding_seen) showOnboarding();
}

async function populateAbout() {
  try {
    const ver = await api().get_version();
    const el = $("about-ver");
    if (el) el.textContent = t("settings.about.version", { version: ver });
  } catch (e) {}
}

function showOnboarding() {
  const el = $("onboard");
  if (!el) return;
  el.style.display = "flex";
  const close = () => { el.style.display = "none"; save({ onboarding_seen: true }); };
  $("onboard-close").onclick = close;
  el.addEventListener("click", (e) => { if (e.target === el) close(); });
  document.addEventListener("keydown", function esc(e) {
    if (e.key === "Escape" && el.style.display !== "none") { close(); document.removeEventListener("keydown", esc); }
  });
}

function renderUpdateBanner() {
  if (!_updateInfo || !_updateInfo.has_update) return;
  const info = _updateInfo;
  $("update-msg").textContent = t("update.available", { version: info.latest });
  const link = $("update-link");
  // Always open in browser — prefer installer asset, fall back to release page.
  const dlUrl = info.installer || info.url;
  link.href = dlUrl || "#";
  link.textContent = t("update.download");
  link.onclick = (e) => { e.preventDefault(); doUpdate(dlUrl, info.url); };
}
async function checkForUpdate() {
  try {
    const info = await api().check_update();
    if (!info || !info.has_update) return;
    _updateInfo = info;
    renderUpdateBanner();
    $("update-banner").style.display = "flex";
  } catch (e) {}
}
async function doUpdate(downloadUrl, pageUrl) {
  const msg = $("update-msg");
  msg.textContent = t("update.downloading");
  try {
    const res = await api().install_update(downloadUrl || pageUrl);
    msg.textContent = (res && res.ok) ? t("update.starting") : t("update.failed");
    if (res && !res.ok && pageUrl) setTimeout(() => window.open(pageUrl), 800);
  } catch (e) {
    msg.textContent = t("update.failed");
    if (pageUrl) setTimeout(() => window.open(pageUrl), 800);
  }
}

/* ── Windows accent colour ───────────────────────────────────────────────────── */
function _linearize(c) {
  c /= 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}
async function applyWindowsColors() {
  const root = document.documentElement;
  if (!cfg.use_windows_colors) {
    ["--primary", "--primary-hover", "--primary-soft", "--on-primary", "--focus-ring"].forEach(v => root.style.removeProperty(v));
    return;
  }
  try {
    const res = await api().get_windows_accent();
    if (!res || !res.ok || !res.hex) return;
    const hex = res.hex;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const lum = 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b);
    const onPrimary = lum > 0.18 ? "#16201C" : "#FFFFFF";
    root.style.setProperty("--primary", hex);
    root.style.setProperty("--primary-hover", `rgba(${r},${g},${b},0.82)`);
    root.style.setProperty("--primary-soft", `rgba(${r},${g},${b},0.14)`);
    root.style.setProperty("--on-primary", onPrimary);
    root.style.setProperty("--focus-ring", `rgba(${r},${g},${b},0.5)`);
  } catch (e) {}
}

/* ── Offline awareness ──────────────────────────────────────────────────────── */
function wireOffline() {
  const update = () => { $("offline-banner").style.display = navigator.onLine ? "none" : "flex"; };
  window.addEventListener("online", update);
  window.addEventListener("offline", update);
  update();
}

/* ── Theme + palette + language ───────────────────────────────────────────── */
function resolveMode(theme) {
  if (theme === "System") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return theme.toLowerCase();
}
function applyTheme() {
  document.documentElement.setAttribute("data-mode", resolveMode(cfg.theme));
  document.querySelectorAll("#mode-seg button").forEach(b => {
    const on = b.dataset.mode === cfg.theme;
    b.classList.toggle("active", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
  });
}
function applyPalette() {
  document.documentElement.setAttribute("data-palette", cfg.palette);
  document.querySelectorAll(".palette-card").forEach(c => {
    const on = c.dataset.palette === cfg.palette;
    c.classList.toggle("active", on);
    c.setAttribute("aria-checked", on ? "true" : "false");
  });
}
function save(patch) { Object.assign(cfg, patch); if (window.pywebview) api().save_config(patch); }

/* ── Error translation ────────────────────────────────────────────────────── */
function friendlyError(raw) {
  if (!raw) return t("error.generic");
  const r = raw.toLowerCase();
  if (r.includes("file not found") || r.includes("no such file")) return t("error.fileNotFound");
  if (r.includes("missingdependency")) return t("error.unsupportedType");
  if (r.includes("tesseract not found")) return t("error.tesseractMissing");
  if (r.includes("pdf ocr requires pymupdf") || r.includes("no module named 'pymupdf'")) return t("error.pymupdfMissing");
  if (r.includes("failed to open") || r.includes("could not open pdf")) return t("error.pdfOpenFailed");
  if (r.includes("ocr failed") || r.includes("image_to_string")) return t("error.ocrFailed");
  if (r.includes("permission") || r.includes("access is denied")) return t("error.permissionDenied");
  if (r.includes("unicodedecodeerror") || r.includes("codec can")) return t("error.encoding");
  if (r.includes("timeout") || r.includes("timed out")) return t("error.timeout");
  if (r.includes("unsupported format") || r.includes("no text can be extracted"))
    return raw.replace(/^ValueError:\s*/i, "").split(/[\n\r]/)[0].trim();
  if (r.includes("too large") || r.includes("maximum allowed size"))
    return raw.replace(/^ValueError:\s*/i, "").split(/[\n\r]/)[0].trim();
  if (r.includes("path is a directory")) return t("error.pathIsDirectory");
  if (r.includes("invalid file path")) return t("error.invalidPath");
  const first = raw.split(/[\n\r]/)[0].replace(/^[A-Za-z]+Error:\s*/i, "").trim();
  return first.length > 120 ? first.slice(0, 117) + "…" : first || t("error.genericShort");
}

/* ── Navigation ───────────────────────────────────────────────────────────── */
const VIEW_KEYS = {
  convert:  ["convert.title",  "convert.sub"],
  bijoy:    ["bijoy.title",    "bijoy.sub"],
  history:  ["history.title",  "history.sub"],
  settings: ["settings.title", "settings.sub"],
};
let currentView = "convert";
function wireNav() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
}
function switchView(v) {
  currentView = v;
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  document.querySelectorAll(".view").forEach(s => s.classList.remove("active"));
  const sec = $("view-" + v); sec.classList.add("active"); sec.classList.add("fade-in");
  setTimeout(() => sec.classList.remove("fade-in"), 300);
  $("view-title").textContent = t(VIEW_KEYS[v][0]);
  $("view-sub").textContent = t(VIEW_KEYS[v][1]);
  if (v === "history") renderHistory();
}

function wireMode() {
  document.querySelectorAll("#mode-seg button").forEach(b =>
    b.addEventListener("click", () => { save({ theme: b.dataset.mode }); applyTheme(); }));
  window.matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => { if (cfg.theme === "System") applyTheme(); });
}
function wireLang() {
  document.querySelectorAll("#lang-seg button").forEach(b =>
    b.addEventListener("click", () => {
      if (b.dataset.lang === lang) return;
      lang = b.dataset.lang; save({ language: lang }); applyLang();
      $("view-title").textContent = t(VIEW_KEYS[currentView][0]);
      $("view-sub").textContent = t(VIEW_KEYS[currentView][1]);
    }));
}
function wirePalette() {
  document.querySelectorAll(".palette-card").forEach(c => {
    const choose = () => { save({ palette: c.dataset.palette }); applyPalette(); };
    c.addEventListener("click", choose);
    c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(); } });
  });
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
    if (selected >= 0) { files[selected].text = $("editor").value; updateWordCount(files[selected].text); }
  });
  document.addEventListener("keydown", (e) => {
    const isConvert = currentView === "convert";
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "o" && !e.shiftKey) { if (isConvert) { e.preventDefault(); addFiles(); } }
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { if (isConvert) { e.preventDefault(); convertAll(); } }
  });
}
async function addFiles() {
  try { addMetas(await api().pick_files()); }
  catch (e) { toast(t("toast.pickerFailed"), "err"); }
}
async function onFilesDropped(paths) {
  try { addMetas(await api().add_dropped(paths)); }
  catch (e) { toast(t("toast.dropFailed"), "err"); }
}
function addMetas(metas) {
  let added = 0;
  (metas || []).forEach(m => {
    if (!files.some(f => f.path === m.path)) {
      files.push({ ...m, status: "pending", text: "", steps: [], error: "" });
      added++;
    }
  });
  if (added) renderFiles();
}
function clearFiles() { files = []; selected = -1; renderFiles(); renderOutput(); }

async function convertAll() {
  const todo = files.filter(f => f.status === "pending" || f.status === "error");
  if (!todo.length) return toast(t("toast.nothingToConvert"), "err");
  const btn = $("convert-btn");
  btn.disabled = true; btn.setAttribute("aria-busy", "true");
  let doneCount = 0;
  btn.textContent = t("convert.converting", { done: 0, total: todo.length });
  for (const f of files) {
    if (f.status !== "pending" && f.status !== "error") continue;
    f.status = "doing"; f.error = ""; renderFiles();
    const res = await api().convert(f.path);
    if (res.ok) {
      f.text = res.text; f.steps = res.steps;
      f.status = res.steps.some(s => EMPTY_STEPS.has(s)) ? "warn" : "done";
    } else {
      f.status = "error"; f.error = friendlyError(res.error);
    }
    doneCount++;
    btn.textContent = t("convert.converting", { done: doneCount, total: todo.length });
    renderFiles();
    if (selected === files.indexOf(f) || selected < 0) selectFile(files.indexOf(f));
  }
  btn.disabled = false; btn.removeAttribute("aria-busy");
  btn.innerHTML = '<i class="ti ti-bolt"></i><span>' + esc(t("btn.convertAll")) + '</span>';
  const ok   = files.filter(f => f.status === "done").length;
  const warn = files.filter(f => f.status === "warn").length;
  const err  = files.filter(f => f.status === "error").length;
  const parts = [];
  if (ok)   parts.push(t("convert.result.converted", { count: ok }));
  if (warn) parts.push(t("convert.result.empty", { count: warn }));
  if (err)  parts.push(t("convert.result.failed", { count: err }));
  toast(parts.join(", "), err ? "err" : warn ? "warn" : "ok");
}
function retryFailed() { convertAll(); }

function stepLabel(s) { return t("step." + s); }
const EMPTY_STEPS = new Set(["ocr_empty", "doc_empty", "pdf_empty", "image_ocr_disabled", "xlsx_empty", "plaintext_empty"]);
const STAT_ICON = {
  pending: "ti-circle", doing: "ti-loader-2",
  done: "ti-circle-check", warn: "ti-alert-triangle", error: "ti-alert-circle",
};
function renderFiles() {
  $("file-count").textContent = files.length;
  $("retry-btn").disabled = !files.some(f => f.status === "error");
  const list = $("file-list");
  if (!files.length) {
    list.innerHTML = '<div class="empty"><i class="ti ti-files-off" aria-hidden="true"></i><span>' + esc(t("convert.empty")) + '</span></div>';
    return;
  }
  list.innerHTML = "";
  files.forEach((f, i) => {
    const row = document.createElement("div");
    row.className = "file-row" + (i === selected ? " selected" : "");
    row.draggable = true;
    const kind = f.is_image ? t("convert.fileType.image") : t("convert.fileType.document");
    const sizeStr = f.size ? " · " + formatBytes(f.size) : "";
    const steps = f.status === "pending"
      ? kind + sizeStr
      : (f.steps.length ? f.steps.map(stepLabel).join(" · ") : (f.error || kind));
    row.innerHTML =
      `<div class="ficon"><i class="ti ${f.is_image ? "ti-photo" : "ti-file-text"}"></i></div>
       <div class="fmeta"><div class="fname">${esc(f.name)}</div>
         <div class="fsteps">${esc(steps)}</div>
         ${f.status === "doing" ? '<div class="progress-track" role="progressbar"><div class="progress-bar" style="width:65%"></div></div>' : ""}
       </div>
       <i class="ti ${STAT_ICON[f.status]} fstat ${f.status}" aria-hidden="true"></i>
       <button class="fx" data-x="${i}" aria-label="${esc(t('convert.removeFile'))}"><i class="ti ti-x"></i></button>`;
    row.addEventListener("click", (e) => { if (!e.target.closest(".fx")) selectFile(i); });
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
  document.querySelectorAll("#out-tabs button").forEach(b => {
    const on = b.dataset.tab === m;
    b.classList.toggle("active", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
  });
  renderOutput();
}
function updateWordCount(text) {
  const wc = $("word-count");
  if (!wc) return;
  if (!text) { wc.textContent = ""; return; }
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  wc.textContent = t("count.words", { words: words, chars: text.length });
}
function renderOutput() {
  const ed = $("editor"), pv = $("preview");
  const f = selected >= 0 ? files[selected] : null;
  $("out-name").textContent = f ? f.name : t("convert.output.title");
  const text = f ? (f.text || "") : "";
  if (outMode === "edit") {
    ed.style.display = "block"; pv.style.display = "none"; ed.value = text;
  } else {
    ed.style.display = "none"; pv.style.display = "block";
    pv.innerHTML = text ? marked.parse(text)
      : '<div class="empty"><i class="ti ti-file-text" aria-hidden="true"></i><span>' + esc(t("preview.selectFile")) + '</span></div>';
    pv.classList.toggle("bn", /[ঀ-৿]/.test(text));
  }
  updateWordCount(text);
}
async function exportCurrent() {
  const f = selected >= 0 ? files[selected] : null;
  if (!f || !f.text) return toast(t("toast.nothingToExport"), "err");
  const fmt = await pickFormat();
  if (!fmt) return;
  const base = f.name.replace(/\.[^.]+$/, "");
  const res = await api().export_text(f.text, fmt, `${base}.${fmt}`);
  if (res.ok) toast(t("toast.saved", { name: res.path.split(/[\\/]/).pop() }), "ok");
  else if (!res.cancelled) toast(res.error || t("toast.exportFailed"), "err");
}
async function exportAll() {
  const done = files.filter(f => f.status === "done" && f.text);
  if (!done.length) return toast(t("toast.noConvertedFiles"), "err");
  const fmt = await pickFormat();
  if (!fmt) return;
  const res = await api().export_combined(done.map(f => ({ name: f.name, text: f.text })), fmt);
  if (res.ok) toast(t("toast.savedCombined", { format: fmt }), "ok");
  else if (!res.cancelled) toast(res.error || t("toast.exportFailed"), "err");
}

/* ── Bijoy view ───────────────────────────────────────────────────────────── */
function wireBijoy() {
  $("bj-in").addEventListener("input", detectBijoy);
  $("bj-run").addEventListener("click", runBijoy);
  $("bj-copy").addEventListener("click", () => copyText($("bj-out").value));
  $("bj-export").addEventListener("click", () => saveText($("bj-out").value, "unicode.txt"));
}
let detectTimer = null;
let lastDetect = "idle";   // idle | bijoy | unicode_bn | latin | other
function setDetectPill(state) {
  lastDetect = state;
  const pill = $("bj-detect");
  if (state === "idle") { pill.className = "detect-pill"; pill.textContent = t("bijoy.detect.idle"); return; }
  const key = { bijoy: "bijoy.detect.bijoy", unicode_bn: "bijoy.detect.unicode",
                latin: "bijoy.detect.latin", other: "bijoy.detect.other" }[state] || "bijoy.detect.other";
  pill.className = "detect-pill " + state;
  pill.textContent = t(key);
}
function refreshDetectPill() { setDetectPill(($("bj-in") && $("bj-in").value.trim()) ? lastDetect : "idle"); }
function detectBijoy() {
  clearTimeout(detectTimer);
  detectTimer = setTimeout(async () => {
    const txt = $("bj-in").value.trim();
    if (!txt) return setDetectPill("idle");
    const s = await api().detect(txt);
    setDetectPill(s || "other");
  }, 250);
}
async function runBijoy() {
  const txt = $("bj-in").value.trim();
  if (!txt) return;
  const res = await api().bijoy_convert(txt);
  $("bj-out").value = res.text;
}

/* ── History view ─────────────────────────────────────────────────────────── */
function wireHistory() {
  $("hist-clear").addEventListener("click", async () => { await api().clear_history(); renderHistory(); });
}
async function renderHistory() {
  const items = await api().get_history();
  $("hist-count").textContent = items.length
    ? t(items.length === 1 ? "history.count.one" : "history.count.many", { count: items.length })
    : t("history.count.none");
  $("hist-list").innerHTML = items.map(h => {
    const steps = (h.steps || []).map(s => `<span class="badge">${esc(stepLabel(s))}</span>`).join("");
    return `<div class="hist-item">
      <div class="hicon ${h.ok ? "ok" : "err"}"><i class="ti ${h.ok ? "ti-check" : "ti-x"}"></i></div>
      <div class="hmeta"><div class="hname">${esc(h.name)}</div>
        <div class="hsub">${esc(h.ts || "")} ${h.ok ? steps : esc(h.error || t("history.failed"))}</div></div>
    </div>`;
  }).join("");
}

/* ── Settings controls ─────────────────────────────────────────────────────── */
function wireSettings() {
  $("set-auto-ocr").addEventListener("change", e => save({ auto_ocr: e.target.checked }));
  $("set-auto-bijoy").addEventListener("change", e => save({ auto_bijoy: e.target.checked }));
  document.querySelectorAll("#set-ocr-lang button").forEach(b =>
    b.addEventListener("click", () => { segPick("#set-ocr-lang", b); save({ ocr_language: b.dataset.lang }); }));
  $("set-win-colors").addEventListener("change", async e => {
    const on = e.target.checked;
    save({ use_windows_colors: on });
    if (on) { save({ theme: "System" }); applyTheme(); }
    await applyWindowsColors();
  });
}
function syncSettingsControls() {
  $("set-auto-ocr").checked = cfg.auto_ocr !== false;
  $("set-auto-bijoy").checked = cfg.auto_bijoy !== false;
  $("set-win-colors").checked = cfg.use_windows_colors === true;
  document.querySelectorAll("#set-ocr-lang button").forEach(b => {
    const on = b.dataset.lang === cfg.ocr_language;
    b.classList.toggle("active", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
  });
}

/* ── Shared helpers ───────────────────────────────────────────────────────── */
function segPick(sel, btn) {
  document.querySelectorAll(sel + " button").forEach(b => {
    b.classList.remove("active"); b.setAttribute("aria-checked", "false");
  });
  btn.classList.add("active"); btn.setAttribute("aria-checked", "true");
}
async function pickFormat() {
  return new Promise(resolve => {
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `<div class="modal-card">
      <div class="modal-title">${esc(t("export.title"))}</div>
      <div class="row" style="gap:8px;">
        ${["md", "html", "txt"].map(f => `<button class="btn" data-f="${f}" style="flex:1;justify-content:center;">${f.toUpperCase()}</button>`).join("")}
      </div></div>`;
    document.body.appendChild(wrap);
    const dismiss = (val) => { resolve(val); wrap.remove(); document.removeEventListener("keydown", onKey); };
    const onKey = (e) => { if (e.key === "Escape") dismiss(null); };
    document.addEventListener("keydown", onKey);
    wrap.addEventListener("click", e => {
      if (e.target.dataset.f) dismiss(e.target.dataset.f);
      else if (e.target === wrap) dismiss(null);
    });
  });
}
async function copyText(txt) {
  if (!txt) return toast(t("toast.nothingToCopy"), "err");
  try { await navigator.clipboard.writeText(txt); toast(t("toast.copied"), "ok"); }
  catch (e) { toast(t("toast.copyFailed"), "err"); }
}
async function saveText(txt, name) {
  if (!txt) return toast(t("toast.nothingToSave"), "err");
  const res = await api().export_text(txt, "txt", name);
  if (res.ok) toast(t("toast.saved", { name: res.path.split(/[\\/]/).pop() }), "ok");
  else if (!res.cancelled) toast(res.error || t("toast.saveFailed"), "err");
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
    else toast(t("toast.dropUnavailable"), "err");
  });
}
function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function toast(msg, kind) {
  const el = document.createElement("div");
  el.className = "toast " + (kind || "");
  el.setAttribute("role", kind === "err" ? "alert" : "status");
  el.innerHTML = `<i class="ti ${kind === "ok" ? "ti-check" : kind === "err" ? "ti-alert-circle" : kind === "warn" ? "ti-alert-triangle" : "ti-info-circle"}"></i>${esc(msg)}`;
  $("toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 2600);
}
function formatBytes(b) {
  if (b < 1024) return b + " B";
  if (b < 1024 * 1024) return (b / 1024).toFixed(0) + " KB";
  return (b / (1024 * 1024)).toFixed(1) + " MB";
}

boot();
