// ── Wizard panel and modals ──────────────────────────────────────────────────

import { state, wizardPanel, wizardBody, apiFetch } from './state.js';
import { getTabContent } from './editor.js';

// ── Utility ──────────────────────────────────────────────────────────────────

function relativePath(fromFile, toFile) {
  const fromParts = fromFile.split("/");
  fromParts.pop(); // remove filename → directory segments
  const toParts = toFile.split("/");

  // find common prefix length
  let common = 0;
  while (common < fromParts.length && common < toParts.length
         && fromParts[common] === toParts[common]) {
    common++;
  }

  const ups = fromParts.length - common;
  const remainder = toParts.slice(common);
  const prefix = ups > 0 ? "../".repeat(ups) : "./";
  return prefix + remainder.join("/");
}

function filenameWithoutExt(tabPath) {
  const name = tabPath.split("/").pop();
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.substring(0, dot) : name;
}

function populateSelect(selectEl, items, emptyText) {
  selectEl.replaceChildren();
  if (items.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = emptyText;
    selectEl.appendChild(opt);
  } else {
    items.forEach(item => {
      const opt = document.createElement("option");
      opt.value = item.path;
      opt.textContent = item.name;
      selectEl.appendChild(opt);
    });
  }
}

function openModal(modalId) {
  document.getElementById(modalId).classList.add("visible");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("visible");
}

function applyTemplate(template) {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  tab.cm.setValue(template);
  updateWizardPanel();
}

/**
 * Wire up a modal's close/cancel/backdrop/Enter-key event listeners.
 * Call this once per modal from app.js instead of repeating the pattern.
 */
export function wireModal(modalId, closeFn, createFn) {
  document.getElementById(`${modalId}-close`).addEventListener("click", closeFn);
  document.getElementById(`${modalId}-cancel`).addEventListener("click", closeFn);
  document.getElementById(`${modalId}-create`).addEventListener("click", createFn);
  const modal = document.getElementById(modalId);
  modal.addEventListener("click", e => { if (e.target === modal) closeFn(); });
  modal.querySelectorAll("input.wizard-input, select.wizard-input").forEach(inp => {
    inp.addEventListener("keydown", e => { if (e.key === "Enter") createFn(); });
  });
}

// ── Wizard panel ─────────────────────────────────────────────────────────────

const wizardConfig = [
  { ext: "primitive", label: "Create new primitive", opener: openPrimitiveWizardModal },
  { ext: "scheme",    label: "Create new scheme",    opener: openSchemeWizardModal },
  { ext: "game",      label: "Create new game",      opener: openWizardModal },
  { ext: "proof",     label: "Create new proof",     opener: openProofWizardModal },
];

export function updateWizardPanel() {
  wizardPanel.style.display = "";
  wizardBody.replaceChildren();

  if (!state.activeTab || state.activeTab.startsWith(":inline:")) {
    const msg = document.createElement("span");
    msg.className = "wizard-empty";
    msg.textContent = "No suggestions";
    wizardBody.appendChild(msg);
    return;
  }

  const ext = state.activeTab.split(".").pop();
  const content = getTabContent(state.activeTab);
  const isEmpty = content !== null && content.trim() === "";

  if (isEmpty) {
    const config = wizardConfig.find(c => c.ext === ext);
    if (config) {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = config.label;
      btn.addEventListener("click", config.opener);
      wizardBody.appendChild(btn);
      return;
    }
  }

  const msg = document.createElement("span");
  msg.className = "wizard-empty";
  msg.textContent = "No suggestions";
  wizardBody.appendChild(msg);
}

// ── Game wizard ─────────────────────────────────────────────────────────────

export function openWizardModal() {
  populateSelect(
    document.getElementById("wizard-primitive"),
    state.primitiveFiles,
    "(no primitives found)"
  );
  document.getElementById("wizard-prop-name").value = "";
  document.getElementById("wizard-left-name").value = "Left";
  document.getElementById("wizard-right-name").value = "Right";
  openModal("wizard-modal");
  document.getElementById("wizard-prop-name").focus();
}

export function closeWizardModal() { closeModal("wizard-modal"); }

export function createGameFromWizard() {
  const propName  = document.getElementById("wizard-prop-name").value.trim();
  const primPath  = document.getElementById("wizard-primitive").value;
  const leftName  = document.getElementById("wizard-left-name").value.trim() || "Left";
  const rightName = document.getElementById("wizard-right-name").value.trim() || "Right";

  if (!propName) { document.getElementById("wizard-prop-name").focus(); return; }
  if (!primPath) return;

  const primName = primPath.split("/").pop().replace(/\.primitive$/, "");
  const template =
`import '${primPath}';

Game ${leftName}(${primName} E) {
    Void Initialize() {
    }
}

Game ${rightName}(${primName} E) {
    Void Initialize() {
    }
}

export as ${propName};
`;

  applyTemplate(template);
  closeWizardModal();
}

// ── Primitive wizard ─────────────────────────────────────────────────────────

export function openPrimitiveWizardModal() {
  document.getElementById("primitive-wizard-name").value = filenameWithoutExt(state.activeTab);
  openModal("primitive-wizard-modal");
  document.getElementById("primitive-wizard-name").focus();
}

export function closePrimitiveWizardModal() { closeModal("primitive-wizard-modal"); }

export function createPrimitiveFromWizard() {
  const name = document.getElementById("primitive-wizard-name").value.trim();
  if (!name) { document.getElementById("primitive-wizard-name").focus(); return; }

  applyTemplate(`Primitive ${name}() {\n}\n`);
  closePrimitiveWizardModal();
}

// ── Scheme wizard ────────────────────────────────────────────────────────────

export function openSchemeWizardModal() {
  document.getElementById("scheme-wizard-name").value = filenameWithoutExt(state.activeTab);
  populateSelect(
    document.getElementById("scheme-wizard-primitive"),
    state.primitiveFiles,
    "(no primitives found)"
  );
  openModal("scheme-wizard-modal");
  document.getElementById("scheme-wizard-name").focus();
}

export function closeSchemeWizardModal() { closeModal("scheme-wizard-modal"); }

export function createSchemeFromWizard() {
  const name = document.getElementById("scheme-wizard-name").value.trim();
  const primPath = document.getElementById("scheme-wizard-primitive").value;
  if (!name) { document.getElementById("scheme-wizard-name").focus(); return; }
  if (!primPath) return;

  const primName = primPath.split("/").pop().replace(/\.primitive$/, "");
  const importPath = relativePath(state.activeTab, primPath);
  applyTemplate(
`import '${importPath}';

Scheme ${name}(${primName} E) extends ${primName} {
}
`);
  closeSchemeWizardModal();
}

// ── Proof wizard ─────────────────────────────────────────────────────────────

export function openProofWizardModal() {
  populateSelect(
    document.getElementById("proof-wizard-scheme"),
    state.schemeFiles,
    "(no schemes found)"
  );
  populateSelect(
    document.getElementById("proof-wizard-game"),
    state.gameFiles,
    "(no games found)"
  );
  openModal("proof-wizard-modal");
  document.getElementById("proof-wizard-scheme").focus();
}

export function closeProofWizardModal() { closeModal("proof-wizard-modal"); }

export async function createProofFromWizard() {
  const schemePath = document.getElementById("proof-wizard-scheme").value;
  const gamePath = document.getElementById("proof-wizard-game").value;
  if (!schemePath || !gamePath) return;

  const createBtn = document.getElementById("proof-wizard-modal-create");
  createBtn.disabled = true;
  createBtn.textContent = "Loading...";
  let schemeMeta, gameMeta;
  try {
    [schemeMeta, gameMeta] = await Promise.all([
      apiFetch(`/api/file-metadata?path=${encodeURIComponent(schemePath)}`).catch(() => null),
      apiFetch(`/api/file-metadata?path=${encodeURIComponent(gamePath)}`).catch(() => null),
    ]);
  } catch (err) {
    console.error("Proof wizard: failed to fetch metadata", err);
  }
  createBtn.disabled = false;
  createBtn.textContent = "Create";

  const schemeFilename = schemePath.split("/").pop().replace(/\.scheme$/, "");
  const gameFilename = gamePath.split("/").pop().replace(/\.game$/, "");

  const schemeName = schemeMeta?.name || schemeFilename;
  const schemeParams = schemeMeta?.parameters || [];
  const gameExportName = gameMeta?.export_name || gameFilename;
  const sides = gameMeta?.sides || ["Left", "Right"];

  const schemeImport = relativePath(state.activeTab, schemePath);
  const gameImport = relativePath(state.activeTab, gamePath);

  const paramDecls = [];
  const paramArgs = [];
  for (const p of schemeParams) {
    paramArgs.push(p.name);
    if (p.type === "Int") {
      paramDecls.push(`    Int ${p.name};`);
    } else {
      paramDecls.push(`    // ${p.type} ${p.name} = ...;`);
    }
  }
  paramDecls.push(`    ${schemeName} S = ${schemeName}(${paramArgs.join(", ")});`);

  const template =
`import '${schemeImport}';
import '${gameImport}';

proof:

let:
${paramDecls.join("\n")}

assume:
    // List security assumptions here

theorem:
    ${gameExportName}(S);

games:
    ${gameExportName}(S).${sides[0]} against ${gameExportName}(S).Adversary;
    // Add intermediate games here
    ${gameExportName}(S).${sides[sides.length - 1]} against ${gameExportName}(S).Adversary;
`;

  applyTemplate(template);
  closeProofWizardModal();
}
