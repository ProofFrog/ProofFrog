// ── Wizard panel and modal ────────────────────────────────────────────────────

import { state, wizardPanel, wizardBody } from './state.js';
import { getTabContent } from './editor.js';

export function updateWizardPanel() {
  const isGame = state.activeTab !== null
    && state.activeTab.endsWith(".game")
    && !state.activeTab.startsWith(":inline:");

  wizardPanel.style.display = "";
  wizardBody.innerHTML = "";

  if (isGame) {
    const content = getTabContent(state.activeTab);
    const isEmpty = content !== null && content.trim() === "";
    if (isEmpty) {
      const btn = document.createElement("button");
      btn.className = "wizard-suggestion";
      btn.textContent = "Create new game";
      btn.addEventListener("click", openWizardModal);
      wizardBody.appendChild(btn);
      return;
    }
  }

  const msg = document.createElement("span");
  msg.className = "wizard-empty";
  msg.textContent = "No suggestions";
  wizardBody.appendChild(msg);
}

export function openWizardModal() {
  const sel = document.getElementById("wizard-primitive");
  sel.innerHTML = "";
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
  document.getElementById("wizard-modal").style.display = "";
  document.getElementById("wizard-prop-name").focus();
}

export function closeWizardModal() {
  document.getElementById("wizard-modal").style.display = "none";
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
