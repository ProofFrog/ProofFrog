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

function makeSplitPane(headerText) {
  const pane = document.createElement("div");
  pane.className = "split-pane";
  const header = document.createElement("div");
  header.className = "split-pane-header";
  header.textContent = headerText;
  pane.appendChild(header);
  return pane;
}

function setupHSplit(handle, topRow, bottomRow, wrap, cmsToRefresh) {
  let startY, startFlex;
  handle.addEventListener("mousedown", e => {
    startY = e.clientY;
    startFlex = topRow.getBoundingClientRect().height;
    handle.classList.add("dragging");
    function onMove(e) {
      const delta = e.clientY - startY;
      const totalH = wrap.getBoundingClientRect().height
        - Array.from(wrap.querySelectorAll(".h-split-handle"))
               .reduce((s, h) => s + h.offsetHeight, 0);
      const newTopH = Math.max(50, Math.min(totalH - 50, startFlex + delta));
      topRow.style.flex = `0 0 ${newTopH}px`;
      bottomRow.style.flex = "1 1 0";
      cmsToRefresh.forEach(cm => cm.refresh());
    }
    function onUp() {
      handle.classList.remove("dragging");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

function setupVSplit(handle, leftPane, rightPane, row, cmsToRefresh) {
  let startX, startFlex;
  handle.addEventListener("mousedown", e => {
    startX = e.clientX;
    startFlex = leftPane.getBoundingClientRect().width;
    handle.classList.add("dragging");
    function onMove(e) {
      const delta = e.clientX - startX;
      const totalW = row.getBoundingClientRect().width - handle.offsetWidth;
      const newLeftW = Math.max(100, Math.min(totalW - 100, startFlex + delta));
      leftPane.style.flex = `0 0 ${newLeftW}px`;
      rightPane.style.flex = "1 1 0";
      cmsToRefresh.forEach(cm => cm.refresh());
    }
    function onUp() {
      handle.classList.remove("dragging");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

export async function openInlineTab(stepIndex, label) {
  if (!state.activeTab) return;
  const sourceTab = state.activeTab;
  const content = getTabContent(sourceTab);
  const virtualPath = `:inline:${stepIndex}:${sourceTab}`;

  // Close existing inline tab for this step if already open
  if (state.tabs.has(virtualPath)) closeTab(virtualPath);

  // Build 3-row wrapper
  const wrap = document.createElement("div");
  wrap.className = "editor-wrap readonly split-view";
  editorsContainer.appendChild(wrap);

  function makeRow() {
    const row = document.createElement("div");
    row.className = "split-row";
    return row;
  }

  // Row 1: previous game hop
  const row1 = makeRow();
  const prevInlinedPane = makeSplitPane("Previous Game — Inlined");
  const vHandle1 = document.createElement("div");
  vHandle1.className = "v-split-handle";
  const prevCanonPane = makeSplitPane("Previous Game — Canonical Form");
  row1.appendChild(prevInlinedPane);
  row1.appendChild(vHandle1);
  row1.appendChild(prevCanonPane);

  // Row 2: current game hop
  const hHandle1 = document.createElement("div");
  hHandle1.className = "h-split-handle";
  const row2 = makeRow();
  const currInlinedPane = makeSplitPane("Current Game — Inlined");
  const vHandle2 = document.createElement("div");
  vHandle2.className = "v-split-handle";
  const currCanonPane = makeSplitPane("Current Game — Canonical Form");
  row2.appendChild(currInlinedPane);
  row2.appendChild(vHandle2);
  row2.appendChild(currCanonPane);

  // Row 3: reserved for future use
  const hHandle2 = document.createElement("div");
  hHandle2.className = "h-split-handle";
  const row3 = makeRow();

  wrap.appendChild(row1);
  wrap.appendChild(hHandle1);
  wrap.appendChild(row2);
  wrap.appendChild(hHandle2);
  wrap.appendChild(row3);

  const cmOpts = { value: "", mode: "prooffrog", theme: getCmTheme(), lineNumbers: true, readOnly: true, lineWrapping: false };
  const cmPrevInlined = CodeMirror(prevInlinedPane, { ...cmOpts });
  const cmPrevCanon   = CodeMirror(prevCanonPane,   { ...cmOpts });
  const cmCurrInlined = CodeMirror(currInlinedPane, { ...cmOpts, value: "Loading…" });
  const cmCurrCanon   = CodeMirror(currCanonPane,   { ...cmOpts, value: "Loading…" });

  setupVSplit(vHandle1, prevInlinedPane, prevCanonPane, row1, [cmPrevInlined, cmPrevCanon]);
  setupVSplit(vHandle2, currInlinedPane, currCanonPane, row2, [cmCurrInlined, cmCurrCanon]);
  setupHSplit(hHandle1, row1, row2, wrap, [cmPrevInlined, cmPrevCanon, cmCurrInlined, cmCurrCanon]);
  setupHSplit(hHandle2, row2, row3, wrap, [cmCurrInlined, cmCurrCanon]);

  const tabName = `[inline] ${label}`;
  const cms = [cmPrevInlined, cmPrevCanon, cmCurrInlined, cmCurrCanon];
  state.tabs.set(virtualPath, { name: tabName, savedContent: "Loading…", cm: cmCurrInlined, cms, wrap, readonly: true });

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
  // Defer an initial refresh so flex layout dimensions are resolved before CodeMirror measures
  requestAnimationFrame(() => cms.forEach(cm => cm.refresh()));

  // Fetch inlined game and canonical form for current step (and previous if applicable)
  setRunning(true);
  try {
    const fetchCurrent = apiFetch("/api/inline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: sourceTab, content, step_index: stepIndex }),
    });
    const fetchPrev = stepIndex > 0
      ? apiFetch("/api/inline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: sourceTab, content, step_index: stepIndex - 1 }),
        })
      : Promise.resolve(null);

    const [currData, prevData] = await Promise.all([fetchCurrent, fetchPrev]);

    cmCurrInlined.setValue(currData.output || "(no output)");
    cmCurrCanon.setValue(currData.canonical || "(no output)");
    if (prevData) {
      cmPrevInlined.setValue(prevData.output || "(no output)");
      cmPrevCanon.setValue(prevData.canonical || "(no output)");
    }

    // Refresh all editors after content is set to fix gutter alignment
    cms.forEach(cm => cm.refresh());

    const tab = state.tabs.get(virtualPath);
    if (tab) tab.savedContent = currData.output || "";
  } catch (e) {
    cmCurrInlined.setValue(`Error: ${e}`);
    cmCurrCanon.setValue("");
  } finally {
    setRunning(false);
  }
}
