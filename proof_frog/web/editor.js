// ── Editor, tab management, save, parse/prove ─────────────────────────────────
// CodeMirror is a CDN global loaded before the module entry point.

/* global CodeMirror */

import {
  state,
  tabsEl, tabsEmpty, editorsContainer, welcome,
  btnSave, btnParse, btnProve,
  outputPane, outputStatus, outputTitle, outputPre,
  apiFetch, getCmTheme,
} from './state.js';
import { getModeForFile } from './cm-mode.js';
import { updateGameHopsPanel } from './game-hops.js';
import { updateWizardPanel } from './wizard.js';
import { highlightActiveFile } from './file-tree.js';

// ── Toolbar helpers ───────────────────────────────────────────────────────────

export function updateToolbar() {
  const hasTab = state.activeTab !== null;
  const isVirtual = hasTab && state.activeTab.startsWith(":inline:");
  btnSave.disabled = !hasTab || isVirtual;
  btnParse.disabled = !hasTab || isVirtual;
  const isProof = hasTab && state.activeTab.endsWith(".proof");
  btnProve.style.display = isProof ? "" : "none";
  btnProve.disabled = !isProof;
}

export function setRunning(running) {
  btnParse.disabled = running || !state.activeTab;
  btnProve.disabled = running || !(state.activeTab && state.activeTab.endsWith(".proof"));
  btnSave.disabled = running || !state.activeTab;
  if (running) {
    btnParse.classList.add("running");
    btnProve.classList.add("running");
  } else {
    btnParse.classList.remove("running");
    btnProve.classList.remove("running");
    updateToolbar();
  }
}

// ── Tab helpers ───────────────────────────────────────────────────────────────

export function getTabContent(path) {
  const tab = state.tabs.get(path);
  return tab ? tab.cm.getValue() : null;
}

export function isModified(path) {
  const tab = state.tabs.get(path);
  if (!tab) return false;
  return tab.cm.getValue() !== tab.savedContent;
}

export function updateTabEl(path) {
  const el = document.querySelector(`.tab[data-path="${CSS.escape(path)}"]`);
  if (!el) return;
  const dot = el.querySelector(".tab-dot");
  dot.style.visibility = isModified(path) ? "visible" : "hidden";
}

export function scrollTabIntoView(path) {
  const el = document.querySelector(`.tab[data-path="${CSS.escape(path)}"]`);
  if (el) el.scrollIntoView({ block: "nearest", inline: "nearest" });
}

export function activateTab(path) {
  if (state.activeTab === path) return;

  // Deactivate old
  if (state.activeTab) {
    const oldTabEl = document.querySelector(`.tab[data-path="${CSS.escape(state.activeTab)}"]`);
    if (oldTabEl) oldTabEl.classList.remove("active");
    const oldWrap = state.tabs.get(state.activeTab)?.wrap;
    if (oldWrap) oldWrap.classList.remove("active");
  }

  state.activeTab = path;
  welcome.classList.add("hidden");

  const tabEl = document.querySelector(`.tab[data-path="${CSS.escape(path)}"]`);
  if (tabEl) tabEl.classList.add("active");

  const { wrap, cm, cmRight } = state.tabs.get(path);
  wrap.classList.add("active");
  cm.refresh(); // CM5 needs refresh after being made visible
  if (cmRight) cmRight.refresh();
  if (!state.tabs.get(path)?.readonly) cm.focus();

  updateToolbar();
  scrollTabIntoView(path);
  updateGameHopsPanel();
  updateWizardPanel();

  // Show warning modal for proofs containing induction steps
  if (path.endsWith(".proof") && /\binduction\s*\(/.test(cm.getValue())) {
    document.getElementById("induction-modal").classList.add("visible");
  }
}

// ── Editor factory ────────────────────────────────────────────────────────────

export function createEditor(content, onChange, path) {
  const wrap = document.createElement("div");
  wrap.className = "editor-wrap";
  editorsContainer.appendChild(wrap);

  const cm = CodeMirror(wrap, {
    value: content,
    mode: getModeForFile(path),
    theme: getCmTheme(),
    lineNumbers: true,
    tabSize: 2,
    indentWithTabs: false,
    lineWrapping: false,
    extraKeys: {
      "Ctrl-S": () => saveFile(state.activeTab),
      "Cmd-S": () => saveFile(state.activeTab),
      Tab: (cm) => {
        if (cm.somethingSelected()) {
          cm.indentSelection("add");
        } else {
          cm.replaceSelection("  ");
        }
      },
      "Shift-Tab": (cm) => cm.indentSelection("subtract"),
    },
  });

  cm.on("change", onChange);

  return { cm, wrap };
}

// ── Open / close tabs ─────────────────────────────────────────────────────────

export async function openFile(path, name) {
  if (state.tabs.has(path)) {
    activateTab(path);
    return;
  }

  const data = await apiFetch(`/api/file?path=${encodeURIComponent(path)}`);
  if (data.error) { alert(data.error); return; }
  const content = data.content;

  const { cm, wrap } = createEditor(content, () => {
    updateTabEl(path);
    if (state.activeTab === path && path.endsWith(".proof")) updateGameHopsPanel();
    if (state.activeTab === path) updateWizardPanel();
  }, path);

  state.tabs.set(path, { name, savedContent: content, cm, wrap, readonly: false });

  const tabEl = document.createElement("div");
  tabEl.className = "tab";
  tabEl.dataset.path = path;
  const tabName = document.createElement("span");
  tabName.className = "tab-name";
  tabName.title = path;
  tabName.textContent = name;
  const tabDot = document.createElement("span");
  tabDot.className = "tab-dot";
  tabDot.style.visibility = "hidden";
  tabDot.textContent = "\u2022";
  const tabClose = document.createElement("span");
  tabClose.className = "tab-close";
  tabClose.title = "Close";
  tabClose.textContent = "\u2715";
  tabEl.append(tabName, tabDot, tabClose);
  tabEl.addEventListener("click", e => {
    if (e.target.classList.contains("tab-close")) { closeTab(path); return; }
    activateTab(path);
  });
  tabsEmpty.style.display = "none";
  tabsEl.appendChild(tabEl);

  activateTab(path);
  highlightActiveFile(path);
}

export function closeTab(path) {
  if (!path.startsWith(":inline:") && isModified(path)) {
    const name = state.tabs.get(path)?.name;
    if (!confirm(`'${name}' has unsaved changes. Close anyway?`)) return;
  }

  const tab = state.tabs.get(path);
  if (tab) {
    tab.wrap.remove();
    state.tabs.delete(path);
  }
  state.hopResultsByPath.delete(path);

  const tabEl = document.querySelector(`.tab[data-path="${CSS.escape(path)}"]`);
  if (tabEl) tabEl.remove();

  if (state.activeTab === path) {
    state.activeTab = null;
    welcome.classList.remove("hidden");
    const remaining = [...state.tabs.keys()];
    if (remaining.length > 0) activateTab(remaining[remaining.length - 1]);
  }

  if (state.tabs.size === 0) tabsEmpty.style.display = "";
  updateToolbar();
  highlightActiveFile(state.activeTab);
  updateGameHopsPanel();
  updateWizardPanel();
}

// ── Save ──────────────────────────────────────────────────────────────────────

export async function saveFile(path) {
  if (!path) return;
  const content = getTabContent(path);
  const res = await apiFetch(`/api/file?path=${encodeURIComponent(path)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (res.success) {
    const tab = state.tabs.get(path);
    if (tab) tab.savedContent = content;
    updateTabEl(path);
  }
}

// ── Parse / Prove ─────────────────────────────────────────────────────────────

export async function runCommand(endpoint, title) {
  if (!state.activeTab) return;
  const content = getTabContent(state.activeTab);
  setRunning(true);
  outputPane.classList.add("visible");
  outputTitle.textContent = `Running ${title} on ${state.tabs.get(state.activeTab)?.name}…`;
  outputStatus.textContent = "";
  outputStatus.className = "";
  outputPre.textContent = "";

  try {
    const data = await apiFetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: state.activeTab, content }),
    });

    // Update saved state (auto-save happened server-side)
    const tab = state.tabs.get(state.activeTab);
    if (tab) { tab.savedContent = content; updateTabEl(state.activeTab); }

    outputTitle.textContent = title;
    if (data.success) {
      outputStatus.textContent = "✓ Success";
      outputStatus.className = "success";
    } else {
      outputStatus.textContent = "✗ Failed";
      outputStatus.className = "error";
    }
    outputPre.textContent = data.output || "(no output)";
    if (endpoint === "/api/prove" && Array.isArray(data.hop_results)) {
      state.hopResultsByPath.set(state.activeTab, data.hop_results);
      updateGameHopsPanel();
    }
  } catch (e) {
    outputStatus.textContent = "✗ Error";
    outputStatus.className = "error";
    outputPre.textContent = String(e);
  } finally {
    setRunning(false);
  }
}
