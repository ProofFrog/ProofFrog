// ── Shared mutable state ──────────────────────────────────────────────────────
// Primitives that need reassignment are wrapped in a plain object so ES module
// consumers can mutate them via `state.activeTab = …` etc.

export const state = {
  tabs: new Map(),           // path → { name, savedContent, cm, wrap, readonly }
  hopResultsByPath: new Map(), // path → [{step_num, valid, kind}, ...]
  activeTab: null,
primitiveFiles: [],        // { path, name } for all .primitive files, sorted by name
  schemeFiles: [],           // { path, name } for all .scheme files, sorted by name
  gameFiles: [],             // { path, name } for all .game files, sorted by name
  proofFiles: [],            // { path, name } for all .proof files, sorted by name
  darkMode: localStorage.getItem("theme") === "dark",
};

// ── DOM refs ──────────────────────────────────────────────────────────────────

export const tabsEl            = document.getElementById("tabs");
export const tabsEmpty         = document.getElementById("tabs-empty");
export const editorsContainer  = document.getElementById("editors-container");
export const welcome           = document.getElementById("welcome");
export const btnSave           = document.getElementById("btn-save");
export const btnSaveAll        = document.getElementById("btn-save-all");
export const btnParse          = document.getElementById("btn-parse");
export const btnProve          = document.getElementById("btn-prove");
export const btnDescribe       = document.getElementById("btn-describe");
export const btnCheck          = document.getElementById("btn-check");
export const btnInlinedGame    = document.getElementById("btn-inlined-game");
export const insertSelect      = document.getElementById("insert-select");
export const proveVerbosity    = document.getElementById("prove-verbosity");
export const btnTheme          = document.getElementById("btn-theme");
export const dirLabel          = document.getElementById("dir-label");
export const outputPane        = document.getElementById("output-pane");
export const outputStatus      = document.getElementById("output-status");
export const outputTitle       = document.getElementById("output-title");
export const outputPre         = document.getElementById("output-pre");
export const fileTreeEl        = document.getElementById("file-tree");

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
  const iconDark = document.getElementById("theme-icon-dark");
  const iconLight = document.getElementById("theme-icon-light");
  if (iconDark && iconLight) {
    // In dark mode, show moon (click to go light). In light mode, show sun (click to go dark).
    iconDark.style.display = dark ? "" : "none";
    iconLight.style.display = dark ? "none" : "";
  }
  state.tabs.forEach(tab => {
    if (tab.cms) {
      tab.cms.forEach(cm => cm.setOption("theme", getCmTheme()));
    } else {
      tab.cm.setOption("theme", getCmTheme());
    }
  });
}
