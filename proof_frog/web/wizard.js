// ── Wizard panel and modals ──────────────────────────────────────────────────

import { state, apiFetch } from './state.js';
import { getTabContent } from './editor.js';
import { findImportInsertionPoint, findBlockClosingLine, insertAtLine, findSectionLine, findSectionLastMemberLine, findFirstReferenceInGames, findOrderedBlockInsertionLine } from './insertion.js';

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
      opt.textContent = item.displayName || item.name;
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
  updateInsertSelect();
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

// ── Wizard registry ──────────────────────────────────────────────────────────

// Each entry: { label, ext (file extension matcher or "any"), opener,
// emptyOnly (true = only show when buffer is empty) }
// Consumed by the toolbar Insert dropdown via applicableWizards().
const wizardConfig = [
  // Creation wizards — empty file only
  { label: "Create new primitive", ext: "primitive", opener: openPrimitiveWizardModal, emptyOnly: true },
  { label: "Create new scheme",    ext: "scheme",    opener: openSchemeWizardModal,    emptyOnly: true },
  { label: "Create new game",      ext: "game",      opener: openWizardModal,          emptyOnly: true },
  { label: "Create new proof",     ext: "proof",     opener: openProofWizardModal,     emptyOnly: true },
  // Always-available wizards
  { label: "Add import",                 ext: "any",       opener: openAddImportModal },
  { label: "Add primitive method",       ext: "primitive", opener: openAddPrimitiveMethodModal },
  { label: "Add scheme method",          ext: "scheme",    opener: openAddSchemeMethodModal },
  { label: "Add game oracle method",     ext: "game",      opener: openAddGameOracleModal },
  { label: "Insert reduction hop",       ext: "proof",     opener: openInsertReductionHopModal },
  { label: "New reduction stub",         ext: "proof",     opener: openNewReductionModal },
  { label: "New intermediate game stub", ext: "proof",     opener: openNewIntermediateGameModal },
  { label: "Add assumption",             ext: "proof",     opener: openAddAssumptionModal },
  { label: "Add lemma",                  ext: "proof",     opener: openAddLemmaModal },
];

// Compute the wizards applicable to the active tab. Returns an empty array if
// there is no active tab or it's a virtual (inline) tab.
function applicableWizards() {
  if (!state.activeTab || state.activeTab.startsWith(":inline:")) return [];
  const ext = state.activeTab.split(".").pop();
  const content = getTabContent(state.activeTab);
  const isEmpty = content !== null && content.trim() === "";
  return wizardConfig.filter(cfg => {
    if (cfg.ext !== "any" && cfg.ext !== ext) return false;
    if (cfg.emptyOnly && !isEmpty) return false;
    return true;
  });
}


// ── Insert dropdown (native select) ──────────────────────────────────────────

// Populate the toolbar's Insert select with the wizards applicable to the
// current file type. Called from updateToolbar (editor.js) on every tab
// switch / save / dirty change so the menu reflects the active file.
export function updateInsertSelect() {
  const sel = document.getElementById("insert-select");
  if (!sel) return;
  sel.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Insert...";
  sel.appendChild(placeholder);
  const applicable = applicableWizards();
  if (applicable.length === 0) {
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "(no wizards for this file type)";
    empty.disabled = true;
    sel.appendChild(empty);
    return;
  }
  applicable.forEach((cfg, idx) => {
    const opt = document.createElement("option");
    opt.value = String(idx);
    opt.textContent = cfg.label;
    sel.appendChild(opt);
  });
}

// Click handler wired in app.js. Reads the picked option, opens the
// corresponding wizard, then resets the select to the placeholder.
export function handleInsertSelect() {
  const sel = document.getElementById("insert-select");
  if (!sel) return;
  const idx = parseInt(sel.value, 10);
  sel.value = ""; // reset to placeholder before opening the wizard
  if (Number.isNaN(idx)) return;
  const applicable = applicableWizards();
  const cfg = applicable[idx];
  if (cfg) cfg.opener();
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
  document.getElementById("scheme-wizard-ingredients").replaceChildren();
  openModal("scheme-wizard-modal");
  document.getElementById("scheme-wizard-name").focus();
}

export function closeSchemeWizardModal() { closeModal("scheme-wizard-modal"); }

export function addSchemeIngredientRow() {
  const container = document.getElementById("scheme-wizard-ingredients");
  const row = document.createElement("div");
  row.className = "scheme-wizard-ingredient-row";
  row.style.display = "flex";
  row.style.gap = "0.5em";
  row.style.marginTop = "0.25em";

  const select = document.createElement("select");
  select.className = "wizard-input";
  populateSelect(select, state.primitiveFiles, "(no primitives found)");

  const name = document.createElement("input");
  name.type = "text";
  name.className = "wizard-input";
  name.placeholder = "param name";
  name.autocomplete = "off";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "×";
  remove.addEventListener("click", () => row.remove());

  row.appendChild(select);
  row.appendChild(name);
  row.appendChild(remove);
  container.appendChild(row);
  name.focus();
}

export function createSchemeFromWizard() {
  const name = document.getElementById("scheme-wizard-name").value.trim();
  const extPath = document.getElementById("scheme-wizard-primitive").value;
  if (!name) { document.getElementById("scheme-wizard-name").focus(); return; }
  if (!extPath) return;

  const extName = extPath.split("/").pop().replace(/\.primitive$/, "");
  const ingredientRows = document.getElementById("scheme-wizard-ingredients").children;
  const ingredients = []; // { path, primName, paramName }
  for (const row of ingredientRows) {
    const sel = row.querySelector("select");
    const inp = row.querySelector("input");
    if (!sel.value || !inp.value.trim()) continue;
    ingredients.push({
      path: sel.value,
      primName: sel.value.split("/").pop().replace(/\.primitive$/, ""),
      paramName: inp.value.trim(),
    });
  }

  const importPaths = new Set([relativePath(state.activeTab, extPath)]);
  for (const ing of ingredients) importPaths.add(relativePath(state.activeTab, ing.path));
  const imports = [...importPaths].map(p => `import '${p}';`).join("\n");

  const params = [`${extName} E`, ...ingredients.map(i => `${i.primName} ${i.paramName}`)].join(", ");

  applyTemplate(
`${imports}

Scheme ${name}(${params}) extends ${extName} {
}
`);
  closeSchemeWizardModal();
}

// ── Proof wizard ─────────────────────────────────────────────────────────────

export function openProofWizardModal() {
  const schemeSel = document.getElementById("proof-wizard-scheme");
  schemeSel.replaceChildren();
  // Always offer a scheme-less option for primitive-only proofs (e.g. DDH).
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "(none — primitives only)";
  schemeSel.appendChild(noneOpt);
  for (const item of state.schemeFiles) {
    const opt = document.createElement("option");
    opt.value = item.path;
    opt.textContent = item.displayName || item.name;
    schemeSel.appendChild(opt);
  }
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
  if (!gamePath) return;

  const createBtn = document.getElementById("proof-wizard-modal-create");
  createBtn.disabled = true;
  createBtn.textContent = "Loading...";
  let schemeMeta = null;
  let gameMeta = null;
  try {
    const fetches = [
      apiFetch(`/api/file-metadata?path=${encodeURIComponent(gamePath)}`).catch(() => null),
    ];
    if (schemePath) {
      fetches.push(
        apiFetch(`/api/file-metadata?path=${encodeURIComponent(schemePath)}`).catch(() => null)
      );
    }
    const results = await Promise.all(fetches);
    gameMeta = results[0];
    if (schemePath) schemeMeta = results[1];
  } catch (err) {
    console.error("Proof wizard: failed to fetch metadata", err);
  }
  createBtn.disabled = false;
  createBtn.textContent = "Create";

  const gameFilename = gamePath.split("/").pop().replace(/\.game$/, "");
  const gameExportName = gameMeta?.export_name || gameFilename;
  const sides = gameMeta?.sides || ["Left", "Right"];
  const gameImport = relativePath(state.activeTab, gamePath);

  let template;
  if (schemePath) {
    // Scheme-based proof: instantiate the scheme in let:, pass it to the game.
    const schemeFilename = schemePath.split("/").pop().replace(/\.scheme$/, "");
    const schemeName = schemeMeta?.name || schemeFilename;
    const schemeParams = schemeMeta?.parameters || [];
    const schemeImport = relativePath(state.activeTab, schemePath);

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

    template =
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
  } else {
    // Scheme-less proof (e.g. DDH-like): declare the game's own formal
    // parameters in let: and use them as the theorem's args.
    const gameFormalParams = gameMeta?.games?.[0]?.parameters || [];
    const paramDecls = gameFormalParams.length > 0
      ? gameFormalParams.map(p => `    ${p.type} ${p.name};`).join("\n")
      : "    // Declare your primitive instances and parameters here";
    const callArgs = gameFormalParams.map(p => p.name).join(", ");
    const callExpr = `${gameExportName}(${callArgs})`;

    template =
`import '${gameImport}';

proof:

let:
${paramDecls}

assume:
    // List security assumptions here

theorem:
    ${callExpr};

games:
    ${callExpr}.${sides[0]} against ${callExpr}.Adversary;
    // Add intermediate games here
    ${callExpr}.${sides[sides.length - 1]} against ${callExpr}.Adversary;
`;
  }

  applyTemplate(template);
  closeProofWizardModal();
}

// ── Add import wizard ────────────────────────────────────────────────────

export function openAddImportModal() {
  const allFiles = [
    ...state.primitiveFiles,
    ...state.schemeFiles,
    ...state.gameFiles,
    ...state.proofFiles,
  ].sort((a, b) => a.path.localeCompare(b.path));
  populateSelect(
    document.getElementById("add-import-file"),
    allFiles,
    "(no files found)"
  );
  openModal("add-import-modal");
  document.getElementById("add-import-file").focus();
}

export function closeAddImportModal() { closeModal("add-import-modal"); }

export function createAddImportFromWizard() {
  const targetPath = document.getElementById("add-import-file").value;
  if (!targetPath) return;
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const { line } = findImportInsertionPoint(source);
  const rel = relativePath(state.activeTab, targetPath);
  insertAtLine(tab.cm, line, `import '${rel}';`);
  closeAddImportModal();
}

// ── Add primitive method wizard ──────────────────────────────────────────

export function openAddPrimitiveMethodModal() {
  document.getElementById("add-prim-method-name").value = "";
  document.getElementById("add-prim-method-return").value = "";
  document.getElementById("add-prim-method-params").value = "";
  document.getElementById("add-prim-method-det").checked = false;
  document.getElementById("add-prim-method-inj").checked = false;
  openModal("add-prim-method-modal");
  document.getElementById("add-prim-method-name").focus();
}

export function closeAddPrimitiveMethodModal() { closeModal("add-prim-method-modal"); }

export function createAddPrimitiveMethodFromWizard() {
  const name   = document.getElementById("add-prim-method-name").value.trim();
  const ret    = document.getElementById("add-prim-method-return").value.trim();
  const params = document.getElementById("add-prim-method-params").value.trim();
  const det    = document.getElementById("add-prim-method-det").checked;
  const inj    = document.getElementById("add-prim-method-inj").checked;

  if (!name || !ret) {
    document.getElementById("add-prim-method-name").focus();
    return;
  }

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const closingLine = findBlockClosingLine(source, "Primitive", null);
  if (closingLine === null) {
    alert("Could not find a Primitive block in this file.");
    return;
  }

  const annots = [det && "deterministic", inj && "injective"].filter(Boolean).join(" ");
  const prefix = annots ? annots + " " : "";
  const line = `    ${prefix}${ret} ${name}(${params});`;
  insertAtLine(tab.cm, closingLine, line);
  closeAddPrimitiveMethodModal();
}

// ── Add game oracle method wizard ────────────────────────────────────────

export async function openAddGameOracleModal() {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const errEl = document.getElementById("add-game-oracle-error");
  errEl.style.display = "none";

  let meta;
  try {
    meta = await apiFetch("/api/file-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: state.activeTab, content: source }),
    });
  } catch (err) {
    errEl.textContent = "File has parse errors — fix them first.";
    errEl.style.display = "";
    openModal("add-game-oracle-modal");
    return;
  }

  const targetSelect = document.getElementById("add-game-oracle-target");
  targetSelect.replaceChildren();
  const sides = meta.sides || [];
  if (sides.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no Game blocks found)";
    targetSelect.appendChild(opt);
  } else {
    for (const s of sides) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      targetSelect.appendChild(opt);
    }
  }

  document.getElementById("add-game-oracle-name").value = "";
  document.getElementById("add-game-oracle-return").value = "";
  document.getElementById("add-game-oracle-params").value = "";
  openModal("add-game-oracle-modal");
  document.getElementById("add-game-oracle-name").focus();
}

export function closeAddGameOracleModal() { closeModal("add-game-oracle-modal"); }

export function createAddGameOracleFromWizard() {
  const targetGame = document.getElementById("add-game-oracle-target").value;
  const name       = document.getElementById("add-game-oracle-name").value.trim();
  const ret        = document.getElementById("add-game-oracle-return").value.trim();
  const params     = document.getElementById("add-game-oracle-params").value.trim();
  if (!targetGame || !name || !ret) {
    document.getElementById("add-game-oracle-name").focus();
    return;
  }
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const closingLine = findBlockClosingLine(source, "Game", targetGame);
  if (closingLine === null) {
    alert(`Could not find Game ${targetGame}.`);
    return;
  }
  const block = `    ${ret} ${name}(${params}) {\n    }`;
  insertAtLine(tab.cm, closingLine, block);
  closeAddGameOracleModal();
}

// ── Add scheme method wizard ─────────────────────────────────────────────

// Holds the unimplemented-method signatures fetched in openAddSchemeMethodModal.
let addSchemeMethodInherited = [];

export async function openAddSchemeMethodModal() {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const errEl = document.getElementById("add-scheme-method-error");
  errEl.style.display = "none";
  addSchemeMethodInherited = [];

  let schemeMeta;
  try {
    schemeMeta = await apiFetch("/api/file-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: state.activeTab, content: source }),
    });
  } catch (err) {
    errEl.textContent = "Scheme file has parse errors — fix them first.";
    errEl.style.display = "";
    openModal("add-scheme-method-modal");
    return;
  }

  // Find the extended primitive's file in state.primitiveFiles.
  const primName = schemeMeta.primitive_name;
  const primFile = state.primitiveFiles.find(p => p.name === primName);
  const inheritedSelect = document.getElementById("add-scheme-method-inherited");
  inheritedSelect.replaceChildren();

  if (primFile) {
    try {
      const primMeta = await apiFetch(`/api/file-metadata?path=${encodeURIComponent(primFile.path)}`);
      const implementedNames = new Set(
        (schemeMeta.methods || []).map(m => extractMethodName(m)).filter(Boolean)
      );
      addSchemeMethodInherited = (primMeta.methods || []).filter(
        sig => {
          const n = extractMethodName(sig);
          return n && !implementedNames.has(n);
        }
      );
      if (addSchemeMethodInherited.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "(all inherited methods already implemented)";
        inheritedSelect.appendChild(opt);
      } else {
        addSchemeMethodInherited.forEach((sig, idx) => {
          const opt = document.createElement("option");
          opt.value = String(idx);
          opt.textContent = sig;
          inheritedSelect.appendChild(opt);
        });
      }
    } catch (err) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(could not load primitive)";
      inheritedSelect.appendChild(opt);
    }
  } else {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(primitive not found in project)";
    inheritedSelect.appendChild(opt);
  }

  document.getElementById("add-scheme-method-freeform-toggle").checked = false;
  document.getElementById("add-scheme-method-freeform-fields").style.display = "none";
  document.getElementById("add-scheme-method-name").value = "";
  document.getElementById("add-scheme-method-return").value = "";
  document.getElementById("add-scheme-method-params").value = "";
  openModal("add-scheme-method-modal");
}

// Extract the method name from a signature string like
// "deterministic BitString<n> F(BitString<n> x)" — the token just before the
// first "(".
function extractMethodName(sig) {
  const idx = sig.indexOf("(");
  if (idx === -1) return null;
  const head = sig.slice(0, idx).trim().split(/\s+/);
  return head[head.length - 1] || null;
}

export function closeAddSchemeMethodModal() { closeModal("add-scheme-method-modal"); }

export function createAddSchemeMethodFromWizard() {
  const freeform = document.getElementById("add-scheme-method-freeform-toggle").checked;
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const closingLine = findBlockClosingLine(source, "Scheme", null);
  if (closingLine === null) {
    alert("Could not find a Scheme block in this file.");
    return;
  }

  let block;
  if (freeform) {
    const name   = document.getElementById("add-scheme-method-name").value.trim();
    const ret    = document.getElementById("add-scheme-method-return").value.trim();
    const params = document.getElementById("add-scheme-method-params").value.trim();
    if (!name || !ret) {
      document.getElementById("add-scheme-method-name").focus();
      return;
    }
    block = `    ${ret} ${name}(${params}) {\n    }`;
  } else {
    const idxStr = document.getElementById("add-scheme-method-inherited").value;
    if (idxStr === "") return;
    const sig = addSchemeMethodInherited[parseInt(idxStr, 10)];
    if (!sig) return;
    block = `    ${sig} {\n    }`;
  }
  insertAtLine(tab.cm, closingLine, block);
  closeAddSchemeMethodModal();
}

// ── Insert reduction hop wizard ──────────────────────────────────────────

// Parsed assume: entries from metadata, used to derive Side options.
let insertHopAssumptions = [];
// Per-assumption resolved details (name, args, sides) from server metadata,
// keyed by assumption index. Populated alongside insertHopAssumptions.
let insertHopAssumptionDetails = [];
// Top-level Reduction declarations from server metadata: [{name, parameters}].
// Used to pre-fill the reduction-arguments input when an existing reduction
// is picked.
let insertHopReductions = [];

export async function openInsertReductionHopModal() {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();
  const errEl = document.getElementById("insert-reduction-hop-error");
  errEl.style.display = "none";

  // Capture cursor-adjacent lines.
  const cursor = tab.cm.getCursor();
  const prevLine = cursor.line > 0 ? tab.cm.getLine(cursor.line - 1).trim() : "";
  const nextLine = cursor.line + 1 < tab.cm.lineCount() ? tab.cm.getLine(cursor.line + 1).trim() : "";
  document.getElementById("insert-reduction-hop-prev").value = prevLine;
  document.getElementById("insert-reduction-hop-next").value = nextLine;

  let meta;
  try {
    meta = await apiFetch("/api/file-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: state.activeTab, content: source }),
    });
  } catch {
    errEl.textContent = "Proof has parse errors — fix them first.";
    errEl.style.display = "";
    openModal("insert-reduction-hop-modal");
    return;
  }

  insertHopAssumptions = meta.assumptions || [];
  insertHopAssumptionDetails = meta.assumption_details || [];
  insertHopReductions = meta.reductions || [];
  const assumptionSel = document.getElementById("insert-reduction-hop-assumption");
  assumptionSel.replaceChildren();
  if (insertHopAssumptions.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no assume: entries found)";
    assumptionSel.appendChild(opt);
  } else {
    insertHopAssumptions.forEach((a, idx) => {
      const opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = a;
      assumptionSel.appendChild(opt);
    });
  }

  // Direction dropdown — populated when assumption changes. Sides come
  // from the server-resolved assumption_details, which honors the proof's
  // import aliases and export-name remapping.
  const dirSel = document.getElementById("insert-reduction-hop-direction");
  const populateDirection = () => {
    dirSel.replaceChildren();
    const idx = parseInt(assumptionSel.value, 10);
    const details = insertHopAssumptionDetails[idx];
    if (!details) return;
    const sides = details.sides || [];
    if (sides.length < 2) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = sides.length === 0
        ? "(could not resolve assumption game)"
        : "(assumption game has fewer than 2 sides)";
      dirSel.appendChild(opt);
      return;
    }
    const forward = `${sides[0]} → ${sides[1]}`;
    const backward = `${sides[1]} → ${sides[0]}`;
    for (const [val, label] of [[`${sides[0]}|${sides[1]}`, forward], [`${sides[1]}|${sides[0]}`, backward]]) {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = label;
      dirSel.appendChild(opt);
    }
  };
  assumptionSel.onchange = populateDirection;
  populateDirection();

  // Reduction dropdown: populated from server-resolved top-level Reduction
  // declarations (insertHopReductions). The arguments input is auto-filled
  // with the picked reduction's formal parameter names; the user can edit.
  const reductionSel = document.getElementById("insert-reduction-hop-reduction");
  const argsInput = document.getElementById("insert-reduction-hop-args");
  reductionSel.replaceChildren();
  for (const r of insertHopReductions) {
    const opt = document.createElement("option");
    opt.value = r.name;
    opt.textContent = r.name;
    reductionSel.appendChild(opt);
  }
  const manualOpt = document.createElement("option");
  manualOpt.value = "__manual__";
  manualOpt.textContent = "— enter name manually —";
  reductionSel.appendChild(manualOpt);

  const manualRow = document.getElementById("insert-reduction-hop-manual-row");
  const manualInput = document.getElementById("insert-reduction-hop-manual");
  manualInput.value = "";
  argsInput.value = "";
  // Track whether the user has manually edited the args input. Auto-fill
  // only when they haven't (so picking a different reduction refreshes the
  // suggestion, but typing into the field locks it).
  let lastSuggestedArgs = "";
  argsInput.addEventListener("input", () => {
    // If the user types something different from our last suggestion, lock.
    if (argsInput.value !== lastSuggestedArgs) lastSuggestedArgs = "__locked__";
  });
  const updateArgsFromReduction = () => {
    if (lastSuggestedArgs === "__locked__") return;
    if (reductionSel.value === "__manual__") {
      argsInput.value = "";
      lastSuggestedArgs = "";
      return;
    }
    const picked = insertHopReductions.find(r => r.name === reductionSel.value);
    if (picked) {
      const suggested = (picked.parameters || []).map(p => p.name).join(", ");
      argsInput.value = suggested;
      lastSuggestedArgs = suggested;
    }
  };
  reductionSel.onchange = () => {
    manualRow.style.display = reductionSel.value === "__manual__" ? "" : "none";
    updateArgsFromReduction();
  };
  manualRow.style.display = "none";
  updateArgsFromReduction();

  openModal("insert-reduction-hop-modal");
}

export function closeInsertReductionHopModal() { closeModal("insert-reduction-hop-modal"); }

export async function createInsertReductionHopFromWizard() {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const assumptionIdxStr = document.getElementById("insert-reduction-hop-assumption").value;
  const assumptionIdx = parseInt(assumptionIdxStr, 10);
  if (Number.isNaN(assumptionIdx) || !insertHopAssumptions[assumptionIdx]) return;

  const direction = document.getElementById("insert-reduction-hop-direction").value;
  if (!direction) return;
  const [side1, side2] = direction.split("|");

  let reductionName = document.getElementById("insert-reduction-hop-reduction").value;
  if (reductionName === "__manual__") {
    reductionName = document.getElementById("insert-reduction-hop-manual").value.trim();
  }
  if (!reductionName) return;

  // Combine the reduction name with its arguments. Empty args stays bare.
  const argsText = document.getElementById("insert-reduction-hop-args").value.trim();
  const reduction = argsText ? `${reductionName}(${argsText})` : reductionName;

  const errEl = document.getElementById("insert-reduction-hop-error");
  errEl.style.display = "none";

  const source = tab.cm.getValue();
  let result;
  try {
    result = await apiFetch("/api/scaffold/reduction-hop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: state.activeTab,
        content: source,
        assumption_index: assumptionIdx,
        side1,
        side2,
        reduction_name: reduction,
      }),
    });
  } catch (e) {
    errEl.textContent = e?.message || "Failed to scaffold reduction hop.";
    errEl.style.display = "";
    return;
  }

  const [line1, line2] = result.lines;
  const cursor = tab.cm.getCursor();
  tab.cm.replaceRange(`${line1}\n${line2}\n`, { line: cursor.line, ch: 0 }, { line: cursor.line, ch: 0 });
  closeInsertReductionHopModal();
}

// ── New intermediate game stub wizard ────────────────────────────────────

// Tracks the most recently server-suggested params value, so the name-input
// auto-fill can detect manual edits and stop overriding them.
let intermediateGameLastSuggestedParams = "";
let intermediateGameNameDebounceTimer = null;

export async function openNewIntermediateGameModal() {
  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  document.getElementById("new-intermediate-game-name").value = "";
  document.getElementById("new-intermediate-game-params").value = "";
  document.getElementById("new-intermediate-game-warning").style.display = "none";
  intermediateGameLastSuggestedParams = "";

  const nameEl = document.getElementById("new-intermediate-game-name");
  const paramsEl = document.getElementById("new-intermediate-game-params");

  // Debounced: when the user types a name, ask the server for a default
  // params list. The server uses the proof's let-bindings to type the
  // theorem args. Only auto-fill if the user hasn't manually edited.
  nameEl.oninput = () => {
    if (intermediateGameNameDebounceTimer) {
      clearTimeout(intermediateGameNameDebounceTimer);
    }
    intermediateGameNameDebounceTimer = setTimeout(async () => {
      const name = nameEl.value.trim();
      if (!name) return;
      if (paramsEl.value !== intermediateGameLastSuggestedParams) return;
      try {
        const result = await apiFetch("/api/scaffold/intermediate-game", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            path: state.activeTab,
            content: tab.cm.getValue(),
            name,
            params: "",
          }),
        });
        if (result && typeof result.params_used === "string") {
          if (paramsEl.value === intermediateGameLastSuggestedParams) {
            paramsEl.value = result.params_used;
            intermediateGameLastSuggestedParams = result.params_used;
          }
        }
      } catch {
        // Silent: leave params field as-is. The user can fill it in.
      }
    }, 200);
  };

  openModal("new-intermediate-game-modal");
  nameEl.focus();
}

export function closeNewIntermediateGameModal() { closeModal("new-intermediate-game-modal"); }

export async function createNewIntermediateGameFromWizard() {
  const name   = document.getElementById("new-intermediate-game-name").value.trim();
  const params = document.getElementById("new-intermediate-game-params").value.trim();
  if (!name) return;

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();

  let block;
  try {
    const result = await apiFetch("/api/scaffold/intermediate-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: state.activeTab,
        content: source,
        name,
        params,
      }),
    });
    block = result.block;
  } catch (err) {
    document.getElementById("new-intermediate-game-warning").textContent =
      `Failed to scaffold intermediate game: ${err.message || err}`;
    document.getElementById("new-intermediate-game-warning").style.display = "";
    return;
  }
  if (!block) return;

  const ordinal = findFirstReferenceInGames(source, name);
  let insertLine;
  if (ordinal === -1) {
    document.getElementById("new-intermediate-game-warning").textContent =
      "Not yet referenced in games: — placing after existing intermediate games.";
    document.getElementById("new-intermediate-game-warning").style.display = "";
    insertLine = findOrderedBlockInsertionLine(source, "Game", Number.MAX_SAFE_INTEGER);
  } else {
    insertLine = findOrderedBlockInsertionLine(source, "Game", ordinal);
  }
  insertAtLine(tab.cm, insertLine, "\n" + block);
  closeNewIntermediateGameModal();
}

// ── New reduction stub wizard ────────────────────────────────────────────

export function openNewReductionModal() {
  document.getElementById("new-reduction-name").value = "";
  document.getElementById("new-reduction-params").value = "";
  document.getElementById("new-reduction-compose-args").value = "";
  document.getElementById("new-reduction-warning").style.display = "none";

  populateSelect(document.getElementById("new-reduction-game"),   state.gameFiles,   "(no games found)");
  populateSelect(document.getElementById("new-reduction-scheme"), state.schemeFiles, "(no schemes found)");

  const gameSel = document.getElementById("new-reduction-game");
  const sideSel = document.getElementById("new-reduction-side");
  const populateSides = async () => {
    sideSel.replaceChildren();
    if (!gameSel.value) return;
    try {
      const meta = await apiFetch(`/api/file-metadata?path=${encodeURIComponent(gameSel.value)}`);
      (meta.sides || []).forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        sideSel.appendChild(opt);
      });
    } catch { /* ignore */ }
  };
  gameSel.onchange = populateSides;
  populateSides();

  openModal("new-reduction-modal");
  document.getElementById("new-reduction-name").focus();
}

export function closeNewReductionModal() { closeModal("new-reduction-modal"); }

export async function createNewReductionFromWizard() {
  const name        = document.getElementById("new-reduction-name").value.trim();
  const gamePath    = document.getElementById("new-reduction-game").value;
  const side        = document.getElementById("new-reduction-side").value;
  const schemePath  = document.getElementById("new-reduction-scheme").value;
  const params      = document.getElementById("new-reduction-params").value.trim();
  const composeArgs = document.getElementById("new-reduction-compose-args").value.trim();
  if (!name || !gamePath || !side || !schemePath) return;

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();

  // Resolve the security game's export name from the dropdown's selected
  // file entry. The server endpoint looks this up in the engine namespace.
  const gameItem = state.gameFiles.find(g => g.path === gamePath);
  const securityGameName = gameItem ? gameItem.name : "";
  if (!securityGameName) {
    document.getElementById("new-reduction-warning").textContent =
      "Could not resolve security game name.";
    document.getElementById("new-reduction-warning").style.display = "";
    return;
  }

  let block;
  try {
    const result = await apiFetch("/api/scaffold/reduction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: state.activeTab,
        content: source,
        name,
        security_game_name: securityGameName,
        side,
        params,
        compose_args: composeArgs,
      }),
    });
    block = result.block;
  } catch (err) {
    document.getElementById("new-reduction-warning").textContent =
      `Failed to scaffold reduction: ${err.message || err}`;
    document.getElementById("new-reduction-warning").style.display = "";
    return;
  }
  if (!block) return;

  // Determine insertion position by first reference in games:
  const ordinal = findFirstReferenceInGames(source, name);
  let insertLine;
  if (ordinal === -1) {
    document.getElementById("new-reduction-warning").textContent =
      "Not yet referenced in games: — placing after existing reductions.";
    document.getElementById("new-reduction-warning").style.display = "";
    insertLine = findOrderedBlockInsertionLine(source, "Reduction", Number.MAX_SAFE_INTEGER);
  } else {
    insertLine = findOrderedBlockInsertionLine(source, "Reduction", ordinal);
  }

  insertAtLine(tab.cm, insertLine, "\n" + block);
  closeNewReductionModal();
}

// ── Add lemma wizard ─────────────────────────────────────────────────────

export function openAddLemmaModal() {
  const fileSelect = document.getElementById("add-lemma-file");
  fileSelect.replaceChildren();
  const otherProofs = state.proofFiles.filter(p => p.path !== state.activeTab);
  if (otherProofs.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no other proof files found)";
    fileSelect.appendChild(opt);
  } else {
    for (const p of otherProofs) {
      const opt = document.createElement("option");
      opt.value = p.path;
      opt.textContent = p.displayName || p.name;
      fileSelect.appendChild(opt);
    }
  }
  document.getElementById("add-lemma-theorem").value = "";
  document.getElementById("add-lemma-params").value = "";
  fileSelect.onchange = async () => {
    if (!fileSelect.value) return;
    try {
      const meta = await apiFetch(`/api/file-metadata?path=${encodeURIComponent(fileSelect.value)}`);
      document.getElementById("add-lemma-theorem").value = meta.theorem || "";
    } catch {
      document.getElementById("add-lemma-theorem").value = "(failed to load)";
    }
  };
  if (otherProofs.length > 0) fileSelect.dispatchEvent(new Event("change"));
  openModal("add-lemma-modal");
}

export function closeAddLemmaModal() { closeModal("add-lemma-modal"); }

export function createAddLemmaFromWizard() {
  const proofPath = document.getElementById("add-lemma-file").value;
  const theorem   = document.getElementById("add-lemma-theorem").value.trim();
  const paramsOverride = document.getElementById("add-lemma-params").value.trim();
  if (!proofPath || !theorem) return;

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;

  // Ensure `lemma:` section exists; create between `assume:` and `theorem:` if missing.
  if (findSectionLine(tab.cm.getValue(), "lemma:") === -1) {
    const assumeLast = findSectionLastMemberLine(tab.cm.getValue(), "assume:");
    const theoremLine = findSectionLine(tab.cm.getValue(), "theorem:");
    if (theoremLine === -1) {
      alert("Proof file has no `theorem:` section.");
      return;
    }
    const insertAt = assumeLast === -1 ? theoremLine : assumeLast + 1;
    tab.cm.replaceRange("\nlemma:\n", { line: insertAt, ch: 0 }, { line: insertAt, ch: 0 });
  }

  const lastLemma = findSectionLastMemberLine(tab.cm.getValue(), "lemma:");
  const rel = relativePath(state.activeTab, proofPath);
  // If user overrode parameters, substitute inside the theorem string's parentheses.
  let effective = theorem;
  if (paramsOverride) {
    effective = theorem.replace(/\([^)]*\)/, `(${paramsOverride})`);
  }
  // Strip trailing `;` if present.
  effective = effective.replace(/;\s*$/, "");
  const line = `    ${effective} by '${rel}';`;
  insertAtLine(tab.cm, lastLemma + 1, line);
  closeAddLemmaModal();
}

// ── Add assumption wizard ────────────────────────────────────────────────

export async function openAddAssumptionModal() {
  const gameSelect = document.getElementById("add-assumption-game");
  gameSelect.replaceChildren();
  if (state.gameFiles.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(no games found)";
    gameSelect.appendChild(opt);
  } else {
    for (const g of state.gameFiles) {
      const opt = document.createElement("option");
      opt.value = g.path;
      opt.textContent = g.displayName || g.name;
      gameSelect.appendChild(opt);
    }
  }
  document.getElementById("add-assumption-params").value = "";
  openModal("add-assumption-modal");
  document.getElementById("add-assumption-game").focus();
}

export function closeAddAssumptionModal() { closeModal("add-assumption-modal"); }

export async function createAddAssumptionFromWizard() {
  const gamePath = document.getElementById("add-assumption-game").value;
  const params   = document.getElementById("add-assumption-params").value.trim();
  if (!gamePath) return;

  let meta;
  try {
    meta = await apiFetch(`/api/file-metadata?path=${encodeURIComponent(gamePath)}`);
  } catch (err) {
    alert(`Failed to read game metadata: ${err.message}`);
    return;
  }
  const exportName = meta.export_name || gamePath.split("/").pop().replace(/\.game$/, "");

  const tab = state.tabs.get(state.activeTab);
  if (!tab) return;
  const source = tab.cm.getValue();

  // Ensure `assume:` section exists; create before `theorem:` if missing.
  let sourceAfter = source;
  let lineToInsert;
  if (findSectionLine(sourceAfter, "assume:") === -1) {
    const theoremLine = findSectionLine(sourceAfter, "theorem:");
    if (theoremLine === -1) {
      alert("Proof file has no `theorem:` section; cannot insert `assume:`.");
      return;
    }
    tab.cm.replaceRange("\nassume:\n", { line: theoremLine, ch: 0 }, { line: theoremLine, ch: 0 });
    sourceAfter = tab.cm.getValue();
  }

  const last = findSectionLastMemberLine(sourceAfter, "assume:");
  lineToInsert = last + 1;
  const gameImport = relativePath(state.activeTab, gamePath);
  const newLine = `    ${exportName}(${params});`;
  insertAtLine(tab.cm, lineToInsert, newLine);

  // Insert import if not already present.
  if (!new RegExp(`import\\s+['"]${gameImport.replace(/[.\\]/g, "\\$&")}['"]`).test(tab.cm.getValue())) {
    const { line } = findImportInsertionPoint(tab.cm.getValue());
    insertAtLine(tab.cm, line, `import '${gameImport}';`);
  }

  closeAddAssumptionModal();
}
