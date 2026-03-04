// ── Shared mutable state ──────────────────────────────────────────────────────
// Primitives that need reassignment are wrapped in a plain object so ES module
// consumers can mutate them via `state.activeTab = …` etc.

export const state = {
  tabs: new Map(),           // path → { name, savedContent, cm, wrap, readonly }
  hopResultsByPath: new Map(), // path → [{step_num, valid, kind}, ...]
  activeTab: null,
primitiveFiles: [],        // { path, name } for all .primitive files, sorted by name
  darkMode: localStorage.getItem("theme") === "dark",
};

// ── DOM refs ──────────────────────────────────────────────────────────────────

export const tabsEl            = document.getElementById("tabs");
export const tabsEmpty         = document.getElementById("tabs-empty");
export const editorsContainer  = document.getElementById("editors-container");
export const welcome           = document.getElementById("welcome");
export const btnSave           = document.getElementById("btn-save");
export const btnParse          = document.getElementById("btn-parse");
export const btnProve          = document.getElementById("btn-prove");
export const btnTheme          = document.getElementById("btn-theme");
export const dirLabel          = document.getElementById("dir-label");
export const outputPane        = document.getElementById("output-pane");
export const outputStatus      = document.getElementById("output-status");
export const outputTitle       = document.getElementById("output-title");
export const outputPre         = document.getElementById("output-pre");
export const fileTreeEl        = document.getElementById("file-tree");
export const wizardPanel       = document.getElementById("wizard-panel");
export const wizardBody        = document.getElementById("wizard-body");

// ── API helper ────────────────────────────────────────────────────────────────

export async function apiFetch(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text();
    let msg;
    try { msg = JSON.parse(text).error; } catch { msg = undefined; }
    throw new Error(msg || `HTTP ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// ── Theme ─────────────────────────────────────────────────────────────────────

export function getCmTheme() { return state.darkMode ? "dracula" : "eclipse"; }

export function applyTheme(dark) {
  state.darkMode = dark;
  localStorage.setItem("theme", dark ? "dark" : "light");
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  btnTheme.textContent = dark ? "Light" : "Dark";
  state.tabs.forEach(tab => {
    if (tab.cms) {
      tab.cms.forEach(cm => cm.setOption("theme", getCmTheme()));
    } else {
      tab.cm.setOption("theme", getCmTheme());
    }
  });
}
