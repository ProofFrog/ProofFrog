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

// ── Line-level diff (LCS-based) ─────────────────────────────────────────────

function computeLineDiff(prevLines, currLines) {
  const m = prevLines.length;
  const n = currLines.length;

  // Build LCS table
  const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = prevLines[i - 1] === currLines[j - 1]
        ? dp[i - 1][j - 1] + 1
        : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  // Backtrack to produce per-line tags
  const prevTags = new Array(m);
  const currTags = new Array(n);
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && prevLines[i - 1] === currLines[j - 1]) {
      prevTags[--i] = "same";
      currTags[--j] = "same";
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      currTags[--j] = "added";
    } else {
      prevTags[--i] = "removed";
    }
  }
  return { prevTags, currTags };
}

function applyDiffHighlight(cmPrev, cmCurr) {
  const prevText = cmPrev.getValue();
  const currText = cmCurr.getValue();
  if (!prevText || !currText) return;

  const prevLines = prevText.split("\n");
  const currLines = currText.split("\n");
  const { prevTags, currTags } = computeLineDiff(prevLines, currLines);

  for (let i = 0; i < prevTags.length; i++) {
    if (prevTags[i] === "removed") {
      cmPrev.addLineClass(i, "background", "diff-removed");
    }
  }
  for (let i = 0; i < currTags.length; i++) {
    if (currTags[i] === "added") {
      cmCurr.addLineClass(i, "background", "diff-added");
    }
  }
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

  // Row 3: scheme-inline analysis panes
  const hHandle2 = document.createElement("div");
  hHandle2.className = "h-split-handle";
  const row3 = makeRow();
  const row3PaneA = makeSplitPane("Reduction");
  const vHandleR3a = document.createElement("div");
  vHandleR3a.className = "v-split-handle";
  const row3PaneB = makeSplitPane("Challenger");
  row3.appendChild(row3PaneA);
  row3.appendChild(vHandleR3a);
  row3.appendChild(row3PaneB);

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
  const cmRow3A       = CodeMirror(row3PaneA,        { ...cmOpts });
  const cmRow3B       = CodeMirror(row3PaneB,        { ...cmOpts });

  setupVSplit(vHandle1,   prevInlinedPane, prevCanonPane, row1, [cmPrevInlined, cmPrevCanon]);
  setupVSplit(vHandle2,   currInlinedPane, currCanonPane, row2, [cmCurrInlined, cmCurrCanon]);
  setupVSplit(vHandleR3a, row3PaneA,       row3PaneB,     row3, [cmRow3A, cmRow3B]);
  setupHSplit(hHandle1, row1, row2, wrap, [cmPrevInlined, cmPrevCanon, cmCurrInlined, cmCurrCanon]);
  setupHSplit(hHandle2, row2, row3, wrap, [cmCurrInlined, cmCurrCanon, cmRow3A, cmRow3B]);

  const tabName = `[inline] ${label}`;
  const cms = [cmPrevInlined, cmPrevCanon, cmCurrInlined, cmCurrCanon, cmRow3A, cmRow3B];
  state.tabs.set(virtualPath, { name: tabName, savedContent: "Loading…", cm: cmCurrInlined, cms, wrap, readonly: true });

  const tabEl = document.createElement("div");
  tabEl.className = "tab";
  tabEl.dataset.path = virtualPath;
  const tabNameSpan = document.createElement("span");
  tabNameSpan.className = "tab-name";
  tabNameSpan.title = label;
  tabNameSpan.textContent = tabName;
  const tabDot = document.createElement("span");
  tabDot.className = "tab-dot";
  tabDot.style.visibility = "hidden";
  tabDot.textContent = "\u2022";
  const tabClose = document.createElement("span");
  tabClose.className = "tab-close";
  tabClose.title = "Close";
  tabClose.textContent = "\u2715";
  tabEl.append(tabNameSpan, tabDot, tabClose);
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
    if (currData.has_reduction) {
      cmRow3A.setValue(currData.reduction || "(no output)");
      cmRow3B.setValue(currData.challenger || "(no output)");
    }

    // Highlight lines that differ between the two canonical forms
    if (prevData) {
      applyDiffHighlight(cmPrevCanon, cmCurrCanon);
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
