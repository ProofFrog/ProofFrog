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
fetch('/api/version').then(r => r.json()).then(d => {
  document.getElementById('version-label').textContent = 'v' + d.version;
});
