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

// ── Wizard panel ─────────────────────────────────────────────────────────────

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
    if (ext === "primitive") {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = "Create new primitive";
      btn.addEventListener("click", openPrimitiveWizardModal);
      wizardBody.appendChild(btn);
      return;
    }
    if (ext === "scheme") {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = "Create new scheme";
      btn.addEventListener("click", openSchemeWizardModal);
      wizardBody.appendChild(btn);
      return;
    }
    if (ext === "game") {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = "Create new game";
      btn.addEventListener("click", openWizardModal);
      wizardBody.appendChild(btn);
      return;
    }
    if (ext === "proof") {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = "Create new proof";
      btn.addEventListener("click", openProofWizardModal);
      wizardBody.appendChild(btn);
      return;
    }
  }

  const msg = document.createElement("span");
  msg.className = "wizard-empty";
  msg.textContent = "No suggestions";
  wizardBody.appendChild(msg);
}

// ── Game wizard (existing) ───────────────────────────────────────────────────

export function openWizardModal() {
  const sel = document.getElementById("wizard-primitive");
  sel.replaceChildren();
  if (state.primitiveFiles.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no primitives found)";
    sel.appendChild(opt);
  } else {
    state.primitiveFiles.forEach(pf => {
      const opt = document.createElement("option");
      opt.value = pf.path;
      opt.textContent = pf.name;
      sel.appendChild(opt);
    });
  }
  document.getElementById("wizard-prop-name").value = "";
  document.getElementById("wizard-left-name").value = "Left";
  document.getElementById("wizard-right-name").value = "Right";
  document.getElementById("wizard-modal").classList.add("visible");
  document.getElementById("wizard-prop-name").focus();
}

export function closeWizardModal() {
  document.getElementById("wizard-modal").classList.remove("visible");
}

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

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  tab.cm.setValue(template);
  closeWizardModal();
  updateWizardPanel();
}

// ── Primitive wizard ─────────────────────────────────────────────────────────

export function openPrimitiveWizardModal() {
  document.getElementById("primitive-wizard-name").value = filenameWithoutExt(state.activeTab);
  document.getElementById("primitive-wizard-modal").classList.add("visible");
  document.getElementById("primitive-wizard-name").focus();
}

export function closePrimitiveWizardModal() {
  document.getElementById("primitive-wizard-modal").classList.remove("visible");
}

export function createPrimitiveFromWizard() {
  const name = document.getElementById("primitive-wizard-name").value.trim();
  if (!name) { document.getElementById("primitive-wizard-name").focus(); return; }

  const template =
`Primitive ${name}() {
}
`;

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  tab.cm.setValue(template);
  closePrimitiveWizardModal();
  updateWizardPanel();
}

// ── Scheme wizard ────────────────────────────────────────────────────────────

export function openSchemeWizardModal() {
  document.getElementById("scheme-wizard-name").value = filenameWithoutExt(state.activeTab);
  const sel = document.getElementById("scheme-wizard-primitive");
  sel.replaceChildren();
  if (state.primitiveFiles.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no primitives found)";
    sel.appendChild(opt);
  } else {
    state.primitiveFiles.forEach(pf => {
      const opt = document.createElement("option");
      opt.value = pf.path;
      opt.textContent = pf.name;
      sel.appendChild(opt);
    });
  }
  document.getElementById("scheme-wizard-modal").classList.add("visible");
  document.getElementById("scheme-wizard-name").focus();
}

export function closeSchemeWizardModal() {
  document.getElementById("scheme-wizard-modal").classList.remove("visible");
}

export function createSchemeFromWizard() {
  const name = document.getElementById("scheme-wizard-name").value.trim();
  const primPath = document.getElementById("scheme-wizard-primitive").value;
  if (!name) { document.getElementById("scheme-wizard-name").focus(); return; }
  if (!primPath) return;

  const primName = primPath.split("/").pop().replace(/\.primitive$/, "");
  const importPath = relativePath(state.activeTab, primPath);
  const template =
`import '${importPath}';

Scheme ${name}(${primName} E) extends ${primName} {
}
`;

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  tab.cm.setValue(template);
  closeSchemeWizardModal();
  updateWizardPanel();
}

// ── Proof wizard ─────────────────────────────────────────────────────────────

export function openProofWizardModal() {
  const schemeSel = document.getElementById("proof-wizard-scheme");
  schemeSel.replaceChildren();
  if (state.schemeFiles.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no schemes found)";
    schemeSel.appendChild(opt);
  } else {
    state.schemeFiles.forEach(sf => {
      const opt = document.createElement("option");
      opt.value = sf.path;
      opt.textContent = sf.name;
      schemeSel.appendChild(opt);
    });
  }

  const gameSel = document.getElementById("proof-wizard-game");
  gameSel.replaceChildren();
  if (state.gameFiles.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no games found)";
    gameSel.appendChild(opt);
  } else {
    state.gameFiles.forEach(gf => {
      const opt = document.createElement("option");
      opt.value = gf.path;
      opt.textContent = gf.name;
      gameSel.appendChild(opt);
    });
  }

  document.getElementById("proof-wizard-modal").classList.add("visible");
  schemeSel.focus();
}

export function closeProofWizardModal() {
  document.getElementById("proof-wizard-modal").classList.remove("visible");
}

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

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  tab.cm.setValue(template);
  closeProofWizardModal();
  updateWizardPanel();
}
