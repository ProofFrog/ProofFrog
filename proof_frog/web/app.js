// ── Application entry point ───────────────────────────────────────────────────
// Wires up button handlers, keyboard shortcuts, and runs init.

import { state, applyTheme, btnSave, btnParse, btnProve, btnTheme } from './state.js';
import './cm-mode.js';
import { saveFile, runCommand, updateToolbar } from './editor.js';
import { loadFileTree } from './file-tree.js';
import { updateWizardPanel, closeWizardModal, createGameFromWizard } from './wizard.js';
import { updateGameHopsPanel } from './game-hops.js';
import './resize.js';

// ── Button handlers ───────────────────────────────────────────────────────────

btnSave.addEventListener("click", () => saveFile(state.activeTab));
btnParse.addEventListener("click", () => runCommand("/api/parse", "Parse"));
btnProve.addEventListener("click", () => runCommand("/api/prove", "Run Proof"));
document.getElementById("output-close").addEventListener("click", () => {
  document.getElementById("output-pane").classList.remove("visible");
});
btnTheme.addEventListener("click", () => applyTheme(!state.darkMode));

document.getElementById("wizard-modal-close").addEventListener("click", closeWizardModal);
document.getElementById("wizard-modal-cancel").addEventListener("click", closeWizardModal);
document.getElementById("wizard-modal-create").addEventListener("click", createGameFromWizard);
document.getElementById("wizard-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("wizard-modal")) closeWizardModal();
});
document.querySelectorAll("#wizard-modal-body input.wizard-input").forEach(inp => {
  inp.addEventListener("keydown", e => { if (e.key === "Enter") createGameFromWizard(); });
});

// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.addEventListener("keydown", e => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key === "s") { e.preventDefault(); saveFile(state.activeTab); }
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    const modal = document.getElementById("wizard-modal");
    if (modal.style.display !== "none") closeWizardModal();
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

applyTheme(state.darkMode);
updateToolbar();
loadFileTree();
updateWizardPanel();
updateGameHopsPanel();
