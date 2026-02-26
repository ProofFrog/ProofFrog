// ── Inline game split-pane tab ────────────────────────────────────────────────
// CodeMirror is a CDN global.

/* global CodeMirror */

import { state, editorsContainer, tabsEl, tabsEmpty, apiFetch, getCmTheme } from './state.js';
import { activateTab, closeTab, getTabContent, setRunning } from './editor.js';

// ── Cursor / games-section detection ─────────────────────────────────────────

export function getStepAtCursor(content, cursorLine) {
  const lines = content.split("\n");

  // Find the "games:" line
  let gamesLine = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*games\s*:/.test(lines[i])) { gamesLine = i; break; }
  }
  if (gamesLine === -1 || cursorLine <= gamesLine) return null;

  // Walk through the games section line-by-line, tracking:
  //   braceDepth — to skip induction { ... } blocks
  //   stepIndex  — 0-based count of all ; -terminated top-level statements
  //   currentStepStart — first line of the current in-progress statement
  let braceDepth = 0;
  let stepIndex = 0;
  let currentStepStart = gamesLine + 1;

  for (let i = gamesLine + 1; i < lines.length; i++) {
    const raw = lines[i];
    // Strip line comments
    const stripped = raw.replace(/\/\/.*$/, "");

    for (const ch of stripped) {
      if (ch === "{") braceDepth++;
      else if (ch === "}") braceDepth--;
    }

    // Only track steps at depth 0 (not inside induction blocks)
    if (braceDepth === 0 && stripped.includes(";")) {
      // This line ends a top-level step
      if (cursorLine >= currentStepStart && cursorLine <= i) {
        // Cursor is within this step's line range
        const stepText = lines
          .slice(currentStepStart, i + 1)
          .map(l => l.replace(/\/\/.*$/, "").trim())
          .join(" ")
          .replace(/\s+/g, " ")
          .trim();

        if (!stepText.includes(" against ")) return null; // assume step or other

        const label = stepText.length > 50 ? stepText.slice(0, 47) + "…" : stepText;
        return { stepIndex, label };
      }
      stepIndex++;
      currentStepStart = i + 1;
    }
  }
  return null;
}

// ── Open inline split-pane tab ────────────────────────────────────────────────

export async function openInlineTab(stepIndex, label) {
  if (!state.activeTab) return;
  const sourceTab = state.activeTab;
  const content = getTabContent(sourceTab);
  const virtualPath = `:inline:${stepIndex}:${sourceTab}`;

  // Close existing inline tab for this step if already open
  if (state.tabs.has(virtualPath)) closeTab(virtualPath);

  // Build split-view wrapper: left pane (inlined) + drag handle + right pane (canonical)
  const wrap = document.createElement("div");
  wrap.className = "editor-wrap readonly split-view";
  editorsContainer.appendChild(wrap);

  function makeSplitPane(headerText) {
    const pane = document.createElement("div");
    pane.className = "split-pane";
    const header = document.createElement("div");
    header.className = "split-pane-header";
    header.textContent = headerText;
    pane.appendChild(header);
    return pane;
  }

  const leftPane = makeSplitPane("Inlined Game");
  const handle = document.createElement("div");
  handle.className = "v-split-handle";
  const rightPane = makeSplitPane("Canonical Form");

  wrap.appendChild(leftPane);
  wrap.appendChild(handle);
  wrap.appendChild(rightPane);

  const cmOpts = { value: "Loading…", mode: "prooffrog", theme: getCmTheme(), lineNumbers: true, readOnly: true, lineWrapping: false };
  const cmLeft = CodeMirror(leftPane, cmOpts);
  const cmRight = CodeMirror(rightPane, { ...cmOpts });

  // Vertical drag-to-resize
  (function setupVSplit() {
    let startX, startFlex;
    handle.addEventListener("mousedown", e => {
      startX = e.clientX;
      startFlex = leftPane.getBoundingClientRect().width;
      handle.classList.add("dragging");
      function onMove(e) {
        const delta = e.clientX - startX;
        const totalW = wrap.getBoundingClientRect().width - handle.offsetWidth;
        const newLeftW = Math.max(100, Math.min(totalW - 100, startFlex + delta));
        leftPane.style.flex = `0 0 ${newLeftW}px`;
        rightPane.style.flex = "1 1 0";
        cmLeft.refresh();
        cmRight.refresh();
      }
      function onUp() {
        handle.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      }
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  })();

  const tabName = `[inline] ${label}`;
  state.tabs.set(virtualPath, { name: tabName, savedContent: "Loading…", cm: cmLeft, cmRight, wrap, readonly: true });

  const tabEl = document.createElement("div");
  tabEl.className = "tab";
  tabEl.dataset.path = virtualPath;
  tabEl.innerHTML = `<span class="tab-name" title="${label}">${tabName}</span><span class="tab-dot" style="visibility:hidden">&#x2022;</span><span class="tab-close" title="Close">&#x2715;</span>`;
  tabEl.addEventListener("click", e => {
    if (e.target.classList.contains("tab-close")) { closeTab(virtualPath); return; }
    activateTab(virtualPath);
  });
  tabsEmpty.style.display = "none";
  tabsEl.appendChild(tabEl);

  activateTab(virtualPath);

  // Fetch both the inlined game and canonical form
  setRunning(true);
  try {
    const data = await apiFetch("/api/inline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: sourceTab, content, step_index: stepIndex }),
    });
    const raw = data.output || "(no output)";
    const canonical = data.canonical || "(no output)";
    cmLeft.setValue(raw);
    cmRight.setValue(canonical);
    const tab = state.tabs.get(virtualPath);
    if (tab) tab.savedContent = raw;
  } catch (e) {
    cmLeft.setValue(`Error: ${e}`);
    cmRight.setValue("");
  } finally {
    setRunning(false);
  }
}
