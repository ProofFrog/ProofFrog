// ── New-file modal logic ──────────────────────────────────────────────────────

import { apiFetch } from './state.js';
import { loadFileTree } from './file-tree.js';
import { openFile } from './editor.js';

const modal       = document.getElementById("newfile-modal");
const folderSel   = document.getElementById("newfile-folder");
const nameInput   = document.getElementById("newfile-name");
const typeSel     = document.getElementById("newfile-type");
const errorDiv    = document.getElementById("newfile-error");

function showError(msg) {
  errorDiv.textContent = msg;
  errorDiv.style.display = "block";
}

function hideError() {
  errorDiv.style.display = "none";
  errorDiv.textContent = "";
}

export async function openNewFileModal() {
  hideError();
  nameInput.value = "";
  try {
    const dirs = await apiFetch("/api/directories");
    folderSel.replaceChildren();
    for (const d of dirs) {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d === "" ? "(root)" : d;
      folderSel.appendChild(opt);
    }
  } catch (e) {
    folderSel.replaceChildren();
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(root)";
    folderSel.appendChild(opt);
  }
  modal.classList.add("visible");
  nameInput.focus();
}

export function closeNewFileModal() {
  modal.classList.remove("visible");
}

export async function createNewFile() {
  hideError();
  const name = nameInput.value.trim();
  if (!name) { showError("File name is required."); return; }
  if (/[\/\\:*?"<>|]/.test(name)) { showError("File name contains invalid characters."); return; }

  const folder = folderSel.value;
  const ext = typeSel.value;
  const filename = name + ext;
  const relPath = folder ? folder + "/" + filename : filename;

  try {
    await apiFetch("/api/file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: relPath }),
    });
    closeNewFileModal();
    await loadFileTree();
    openFile(relPath, filename);
  } catch (e) {
    showError(e.message || "Failed to create file.");
  }
}
