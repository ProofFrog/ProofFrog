// ── Application entry point ───────────────────────────────────────────────────
// Wires up button handlers, keyboard shortcuts, and runs init.

import { state, applyTheme, btnSave, btnParse, btnProve, btnTheme } from './state.js';
import './cm-mode.js';
import { saveFile, runCommand, updateToolbar } from './editor.js';
import { loadFileTree, collapseAll, expandAll } from './file-tree.js';
import { updateWizardPanel, closeWizardModal, createGameFromWizard } from './wizard.js';
import { updateGameHopsPanel } from './game-hops.js';
import { openNewFileModal, closeNewFileModal, createNewFile } from './new-file.js';
import './resize.js';

// ── Button handlers ───────────────────────────────────────────────────────────

btnSave.addEventListener("click", () => saveFile(state.activeTab));
btnParse.addEventListener("click", () => runCommand("/api/parse", "Parse"));
btnProve.addEventListener("click", () => runCommand("/api/prove", "Run Proof"));
document.getElementById("output-close").addEventListener("click", () => {
  document.getElementById("output-pane").classList.remove("visible");
});
btnTheme.addEventListener("click", () => applyTheme(!state.darkMode));
document.getElementById("btn-collapse-all").addEventListener("click", collapseAll);
document.getElementById("btn-expand-all").addEventListener("click", expandAll);

document.getElementById("wizard-modal-close").addEventListener("click", closeWizardModal);
document.getElementById("wizard-modal-cancel").addEventListener("click", closeWizardModal);
document.getElementById("wizard-modal-create").addEventListener("click", createGameFromWizard);
document.getElementById("wizard-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("wizard-modal")) closeWizardModal();
});
document.querySelectorAll("#wizard-modal-body input.wizard-input").forEach(inp => {
  inp.addEventListener("keydown", e => { if (e.key === "Enter") createGameFromWizard(); });
});

// ── New-file modal ───────────────────────────────────────────────────────
document.getElementById("btn-new-file").addEventListener("click", openNewFileModal);
document.getElementById("newfile-modal-close").addEventListener("click", closeNewFileModal);
document.getElementById("newfile-modal-cancel").addEventListener("click", closeNewFileModal);
document.getElementById("newfile-modal-create").addEventListener("click", createNewFile);
document.getElementById("newfile-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("newfile-modal")) closeNewFileModal();
});
document.querySelectorAll("#newfile-modal-body input.wizard-input, #newfile-modal-body select.wizard-input").forEach(inp => {
  inp.addEventListener("keydown", e => { if (e.key === "Enter") createNewFile(); });
});

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

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    const newfile = document.getElementById("newfile-modal");
    if (newfile.classList.contains("visible")) closeNewFileModal();
    const wizard = document.getElementById("wizard-modal");
    if (wizard.classList.contains("visible")) closeWizardModal();
    const induction = document.getElementById("induction-modal");
    if (induction.classList.contains("visible")) closeInductionModal();
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

applyTheme(state.darkMode);
updateToolbar();
loadFileTree();
updateWizardPanel();
updateGameHopsPanel();
