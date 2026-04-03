// ── Game hops panel ───────────────────────────────────────────────────────────

import { state } from './state.js';
import { getTabContent, activateTab } from './editor.js';
import { openInlineTab } from './inline-game.js';

export function getAllGameHops(content) {
  const lines = content.split("\n");
  let gamesLine = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*games\s*:/.test(lines[i])) { gamesLine = i; break; }
  }
  if (gamesLine === -1) return [];

  const hops = [];
  let braceDepth = 0, stepIndex = 0, currentStepStart = gamesLine + 1;
  for (let i = gamesLine + 1; i < lines.length; i++) {
    const stripped = lines[i].replace(/\/\/.*$/, "");
    for (const ch of stripped) {
      if (ch === "{") braceDepth++;
      else if (ch === "}") braceDepth--;
    }
    if (braceDepth === 0 && stripped.includes(";")) {
      const stepText = lines.slice(currentStepStart, i + 1)
        .map(l => l.replace(/\/\/.*$/, "").trim()).join(" ")
        .replace(/\s+/g, " ").replace(/\s*;\s*$/, "").trim();
      if (stepText.includes(" against ")) {
        const label = stepText.replace(/\s+against\s+\S+\s*$/, "").trim();
        hops.push({ stepIndex, label });
      }
      stepIndex++;
      currentStepStart = i + 1;
    }
  }
  return hops;
}

export function updateGameHopsPanel() {
  const panel = document.getElementById("game-hops-panel");
  const list = document.getElementById("game-hops-list");

  // Resolve the source .proof path (handles both proof tabs and inline tabs)
  let proofPath = null;
  if (state.activeTab) {
    if (state.activeTab.startsWith(":inline:")) {
      // Format: ":inline:STEPINDEX:FILEPATH"
      const withoutPrefix = state.activeTab.slice(":inline:".length);
      const colonPos = withoutPrefix.indexOf(":");
      if (colonPos !== -1) {
        const candidate = withoutPrefix.slice(colonPos + 1);
        if (candidate.endsWith(".proof")) proofPath = candidate;
      }
    } else if (state.activeTab.endsWith(".proof")) {
      proofPath = state.activeTab;
    }
  }

  if (!proofPath) {
    panel.style.display = "";
    list.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "hop-item-empty";
    empty.textContent = "No proof file open";
    list.appendChild(empty);
    return;
  }

  const content = getTabContent(proofPath);
  if (content === null) {
    panel.style.display = "";
    list.replaceChildren();
    return;
  }

  // Determine highlighted step when an inline tab is active
  let activeStepIndex = null;
  if (state.activeTab && state.activeTab.startsWith(":inline:")) {
    const withoutPrefix = state.activeTab.slice(":inline:".length);
    const colonPos = withoutPrefix.indexOf(":");
    if (colonPos !== -1) {
      const parsed = parseInt(withoutPrefix.slice(0, colonPos), 10);
      if (!isNaN(parsed)) activeStepIndex = parsed;
    }
  }

  const hops = getAllGameHops(content);
  panel.style.display = "";
  list.innerHTML = "";

  if (hops.length === 0) {
    const empty = document.createElement("div");
    empty.className = "hop-item-empty";
    empty.textContent = "No game hops";
    list.appendChild(empty);
    return;
  }

  const hopResults = proofPath ? (state.hopResultsByPath.get(proofPath) ?? []) : [];
  hops.forEach(({ stepIndex, label }, i) => {
    const result = hopResults[i - 1];
    const validityClass = result ? (result.valid ? " hop-valid" : " hop-invalid") : "";
    const item = document.createElement("div");
    item.className = "hop-item" + (stepIndex === activeStepIndex ? " active" : "") + validityClass;
    item.title = label;

    const labelSpan = document.createElement("span");
    labelSpan.className = "hop-label";
    labelSpan.textContent = label;

    const statusSpan = document.createElement("span");
    statusSpan.className = "hop-status";
    statusSpan.textContent = result ? (result.valid ? "✓" : "✗") : "";

    item.append(labelSpan, statusSpan);
    item.addEventListener("click", () => {
      if (state.activeTab !== proofPath) activateTab(proofPath);
      openInlineTab(stepIndex, label);
    });
    list.appendChild(item);
  });
}
