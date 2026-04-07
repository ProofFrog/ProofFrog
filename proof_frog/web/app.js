// ── Application entry point ───────────────────────────────────────────────────
// Wires up button handlers, keyboard shortcuts, and runs init.

import {
  state, applyTheme,
  btnSave, btnParse, btnProve, btnTheme,
  btnDescribe, btnCheck, btnInlinedGame, insertSelect,
  outputPane, outputStatus, outputTitle, outputPre,
  apiFetch,
} from './state.js';
import './cm-mode.js';
import {
  saveFile, saveAllDirtyTabs, runCommand, updateToolbar, setRunning,
  getTabContent,
} from './editor.js';
import { suppressFileChange } from './live-reload.js';
import { loadFileTree, collapseAll, expandAll } from './file-tree.js';
import {
  wireModal,
  closeWizardModal, createGameFromWizard,
  closePrimitiveWizardModal, createPrimitiveFromWizard,
  closeSchemeWizardModal, createSchemeFromWizard, addSchemeIngredientRow,
  closeProofWizardModal, createProofFromWizard,
  closeAddImportModal, createAddImportFromWizard,
  closeAddPrimitiveMethodModal, createAddPrimitiveMethodFromWizard,
  closeAddSchemeMethodModal, createAddSchemeMethodFromWizard,
  closeAddGameOracleModal, createAddGameOracleFromWizard,
  closeAddAssumptionModal, createAddAssumptionFromWizard,
  closeAddLemmaModal, createAddLemmaFromWizard,
  closeInsertReductionHopModal, createInsertReductionHopFromWizard,
  closeNewReductionModal, createNewReductionFromWizard,
  closeNewIntermediateGameModal, createNewIntermediateGameFromWizard,
  handleInsertSelect,
} from './wizard.js';
import { updateGameHopsPanel } from './game-hops.js';
import { openNewFileModal, closeNewFileModal, createNewFile } from './new-file.js';
import { connectSSE } from './live-reload.js';
import './resize.js';

// ── Button handlers ───────────────────────────────────────────────────────────

btnSave.addEventListener("click", () => saveFile(state.activeTab));
document.getElementById("btn-save-all").addEventListener("click", () => saveAllDirtyTabs());
btnParse.addEventListener("click", () => runCommand("/api/parse", "Parse"));
btnCheck.addEventListener("click", () => runCommand("/api/check", "Type Check"));
btnProve.addEventListener("click", () => runCommand("/api/prove", "Run Proof"));
insertSelect.addEventListener("change", handleInsertSelect);

// ── Describe ─────────────────────────────────────────────────────────────────
btnDescribe.addEventListener("click", async () => {
  if (!state.activeTab || state.activeTab.startsWith(":inline:")) return;
  const path = state.activeTab;
  const tab = state.tabs.get(path);
  if (!tab) return;
  const content = getTabContent(path);
  setRunning(true);
  outputPane.classList.add("visible");
  outputTitle.textContent = `Describing ${tab.name}…`;
  outputStatus.textContent = "";
  outputStatus.className = "";
  outputPre.textContent = "";
  try {
    suppressFileChange(path);
    const data = await apiFetch("/api/describe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    });
    outputTitle.textContent = `Describe: ${tab.name}`;
    if (data.success) {
      outputStatus.textContent = "✓ Success";
      outputStatus.className = "success";
    } else {
      outputStatus.textContent = "✗ Failed";
      outputStatus.className = "error";
    }
    outputPre.textContent = data.output || data.error || "(no output)";
  } catch (e) {
    outputStatus.textContent = "✗ Error";
    outputStatus.className = "error";
    outputPre.textContent = String(e);
  } finally {
    setRunning(false);
  }
});

// ── Inlined Game (modal) ─────────────────────────────────────────────────────
function openInlinedGameModal() {
  if (!state.activeTab || !state.activeTab.endsWith(".proof") || state.activeTab.startsWith(":inline:")) return;
  const modal = document.getElementById("inlined-game-modal");
  const input = document.getElementById("inlined-game-step");
  const err = document.getElementById("inlined-game-error");
  err.style.display = "none";
  err.textContent = "";
  input.value = "";
  modal.classList.add("visible");
  setTimeout(() => input.focus(), 0);
}

function closeInlinedGameModal() {
  document.getElementById("inlined-game-modal").classList.remove("visible");
}

async function runInlinedGameFromModal() {
  const input = document.getElementById("inlined-game-step");
  const err = document.getElementById("inlined-game-error");
  const stepText = input.value.trim();
  if (!stepText) {
    err.textContent = "Please enter a game expression.";
    err.style.display = "";
    return;
  }
  if (!state.activeTab || !state.activeTab.endsWith(".proof")) {
    err.textContent = "No active proof file.";
    err.style.display = "";
    return;
  }
  const path = state.activeTab;
  const tab = state.tabs.get(path);
  const content = tab ? tab.cm.getValue() : "";
  err.style.display = "none";
  err.textContent = "";
  try {
    suppressFileChange(path);
    const data = await apiFetch("/api/inlined-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content, step_text: stepText }),
    });
    if (!data.success) {
      err.textContent = data.error || data.output || "Failed to compute inlined game.";
      err.style.display = "";
      return;
    }
    closeInlinedGameModal();
    outputPane.classList.add("visible");
    outputTitle.textContent = `Inlined Game: ${stepText}`;
    outputStatus.textContent = "✓ Success";
    outputStatus.className = "success";
    outputPre.textContent = data.canonical || data.output || "(no output)";
  } catch (e) {
    err.textContent = String(e);
    err.style.display = "";
  }
}

btnInlinedGame.addEventListener("click", openInlinedGameModal);
wireModal("inlined-game-modal", closeInlinedGameModal, runInlinedGameFromModal);
document.getElementById("output-close").addEventListener("click", () => {
  document.getElementById("output-pane").classList.remove("visible");
});
btnTheme.addEventListener("click", () => applyTheme(!state.darkMode));
document.getElementById("btn-collapse-all").addEventListener("click", collapseAll);
document.getElementById("btn-expand-all").addEventListener("click", expandAll);

wireModal("wizard-modal", closeWizardModal, createGameFromWizard);
wireModal("primitive-wizard-modal", closePrimitiveWizardModal, createPrimitiveFromWizard);
wireModal("scheme-wizard-modal", closeSchemeWizardModal, createSchemeFromWizard);
document.getElementById("scheme-wizard-add-ingredient").addEventListener("click", addSchemeIngredientRow);
wireModal("proof-wizard-modal", closeProofWizardModal, createProofFromWizard);
wireModal("add-import-modal", closeAddImportModal, createAddImportFromWizard);
wireModal("add-prim-method-modal", closeAddPrimitiveMethodModal, createAddPrimitiveMethodFromWizard);
wireModal("add-scheme-method-modal", closeAddSchemeMethodModal, createAddSchemeMethodFromWizard);
document.getElementById("add-scheme-method-freeform-toggle").addEventListener("change", e => {
  document.getElementById("add-scheme-method-freeform-fields").style.display = e.target.checked ? "" : "none";
});
wireModal("add-game-oracle-modal", closeAddGameOracleModal, createAddGameOracleFromWizard);
wireModal("add-assumption-modal", closeAddAssumptionModal, createAddAssumptionFromWizard);
wireModal("add-lemma-modal", closeAddLemmaModal, createAddLemmaFromWizard);
wireModal("insert-reduction-hop-modal", closeInsertReductionHopModal, createInsertReductionHopFromWizard);
wireModal("new-reduction-modal", closeNewReductionModal, createNewReductionFromWizard);
wireModal("new-intermediate-game-modal", closeNewIntermediateGameModal, createNewIntermediateGameFromWizard);

// ── New-file modal ───────────────────────────────────────────────────────
document.getElementById("btn-new-file").addEventListener("click", openNewFileModal);
wireModal("newfile-modal", closeNewFileModal, createNewFile);

// ── Induction warning modal ──────────────────────────────────────────────
function closeInductionModal() {
  document.getElementById("induction-modal").classList.remove("visible");
}
document.getElementById("induction-modal-close").addEventListener("click", closeInductionModal);
document.getElementById("induction-modal-ok").addEventListener("click", closeInductionModal);
document.getElementById("induction-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("induction-modal")) closeInductionModal();
});

// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.addEventListener("keydown", e => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key === "s") { e.preventDefault(); saveFile(state.activeTab); }
});

const escapeModals = [
  ["newfile-modal", closeNewFileModal],
  ["wizard-modal", closeWizardModal],
  ["primitive-wizard-modal", closePrimitiveWizardModal],
  ["scheme-wizard-modal", closeSchemeWizardModal],
  ["proof-wizard-modal", closeProofWizardModal],
  ["induction-modal", closeInductionModal],
  ["add-import-modal", closeAddImportModal],
  ["add-prim-method-modal", closeAddPrimitiveMethodModal],
  ["add-scheme-method-modal", closeAddSchemeMethodModal],
  ["add-game-oracle-modal", closeAddGameOracleModal],
  ["add-assumption-modal", closeAddAssumptionModal],
  ["add-lemma-modal", closeAddLemmaModal],
  ["insert-reduction-hop-modal", closeInsertReductionHopModal],
  ["new-reduction-modal", closeNewReductionModal],
  ["new-intermediate-game-modal", closeNewIntermediateGameModal],
  ["inlined-game-modal", () => document.getElementById("inlined-game-modal").classList.remove("visible")],
];
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    for (const [id, closeFn] of escapeModals) {
      const el = document.getElementById(id);
      if (el.classList.contains("visible")) closeFn();
    }
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

// Platform-aware shortcut hint for the Save tooltip.
const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || "");
const saveShortcut = isMac ? "\u2318S" : "Ctrl+S";
btnSave.title = `Save (${saveShortcut})`;

applyTheme(state.darkMode);
updateToolbar();
loadFileTree();
updateGameHopsPanel();
connectSSE();
fetch('/api/version').then(r => r.json()).then(d => {
  document.getElementById('version-label').textContent = 'v' + d.version;
});
