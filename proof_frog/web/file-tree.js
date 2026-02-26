// ── Sidebar file tree ─────────────────────────────────────────────────────────

import { state, fileTreeEl, dirLabel, apiFetch } from './state.js';
import { openFile } from './editor.js';

export function buildTree(node, depth) {
  const el = document.createElement("div");

  if (node.type === "directory") {
    el.className = "tree-dir";
    const header = document.createElement("div");
    header.className = "tree-item";
    header.style.paddingLeft = `${8 + depth * 14}px`;
    header.innerHTML = `<span class="icon">&#x25BC;</span><span class="name">${node.name}</span>`;
    header.addEventListener("click", () => {
      el.classList.toggle("collapsed");
      header.querySelector(".icon").innerHTML = el.classList.contains("collapsed") ? "&#x25B6;" : "&#x25BC;";
    });
    const children = document.createElement("div");
    children.className = "tree-children";
    (node.children || []).forEach(child => children.appendChild(buildTree(child, depth + 1)));
    el.appendChild(header);
    el.appendChild(children);
  } else {
    el.className = "tree-item";
    el.dataset.path = node.path;
    el.style.paddingLeft = `${8 + depth * 14}px`;
    el.innerHTML = `<span class="icon">&#x1F4C4;</span><span class="name">${node.name}</span>`;
    el.addEventListener("click", () => openFile(node.path, node.name));
  }
  return el;
}

export function highlightActiveFile(path) {
  document.querySelectorAll(".tree-item[data-path]").forEach(el => {
    el.classList.toggle("active", el.dataset.path === path);
  });
}

export function collectPrimitives(node, result) {
  if (node.type === "file" && node.name.endsWith(".primitive")) {
    result.push({ path: node.path, name: node.name.replace(/\.primitive$/, "") });
  }
  if (node.type === "directory") {
    (node.children || []).forEach(child => collectPrimitives(child, result));
  }
}

export async function loadFileTree() {
  const data = await apiFetch("/api/files");
  fileTreeEl.innerHTML = "";
  dirLabel.textContent = data.name || "";
  (data.children || []).forEach(child => fileTreeEl.appendChild(buildTree(child, 0)));
  state.primitiveFiles = [];
  collectPrimitives(data, state.primitiveFiles);
  state.primitiveFiles.sort((a, b) => a.name.localeCompare(b.name));
}
