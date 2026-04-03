// ── Application entry point ───────────────────────────────────────────────────
// Wires up button handlers, keyboard shortcuts, and runs init.

import { state, applyTheme, btnSave, btnParse, btnProve, btnTheme } from './state.js';
import './cm-mode.js';
import { saveFile, runCommand, updateToolbar } from './editor.js';
import { loadFileTree, collapseAll, expandAll } from './file-tree.js';
import {
  updateWizardPanel, wireModal,
  closeWizardModal, createGameFromWizard,
  closePrimitiveWizardModal, createPrimitiveFromWizard,
  closeSchemeWizardModal, createSchemeFromWizard,
  closeProofWizardModal, createProofFromWizard,
} from './wizard.js';
import { updateGameHopsPanel } from './game-hops.js';
import { openNewFileModal, closeNewFileModal, createNewFile } from './new-file.js';
import { connectSSE } from './live-reload.js';
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

wireModal("wizard-modal", closeWizardModal, createGameFromWizard);
wireModal("primitive-wizard-modal", closePrimitiveWizardModal, createPrimitiveFromWizard);
wireModal("scheme-wizard-modal", closeSchemeWizardModal, createSchemeFromWizard);
wireModal("proof-wizard-modal", closeProofWizardModal, createProofFromWizard);

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

applyTheme(state.darkMode);
updateToolbar();
loadFileTree();
updateWizardPanel();
updateGameHopsPanel();
connectSSE();
