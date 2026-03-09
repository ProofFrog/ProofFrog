// ── Sidebar file tree ─────────────────────────────────────────────────────────

import { state, fileTreeEl, dirLabel, apiFetch } from './state.js';
import { openFile } from './editor.js';

export function collapseAll() {
  fileTreeEl.querySelectorAll(".tree-dir").forEach(dir => {
    dir.classList.add("collapsed");
    dir.querySelector(":scope > .tree-item > .icon").textContent = "\u25B6";
  });
}

export function expandAll() {
  fileTreeEl.querySelectorAll(".tree-dir").forEach(dir => {
    dir.classList.remove("collapsed");
    dir.querySelector(":scope > .tree-item > .icon").textContent = "\u25BC";
  });
}

function makeIconNamePair(iconText, nameText) {
  const icon = document.createElement("span");
  icon.className = "icon";
  icon.textContent = iconText;
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = nameText;
  return { icon, name };
}

export function buildTree(node, depth) {
  const el = document.createElement("div");

  if (node.type === "directory") {
    el.className = "tree-dir collapsed";
    const header = document.createElement("div");
    header.className = "tree-item";
    header.style.paddingLeft = `${8 + depth * 14}px`;
    const { icon, name } = makeIconNamePair("\u25B6", node.name);
    header.appendChild(icon);
    header.appendChild(name);
    header.addEventListener("click", () => {
      el.classList.toggle("collapsed");
      icon.textContent = el.classList.contains("collapsed") ? "\u25B6" : "\u25BC";
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
    const { icon, name } = makeIconNamePair("\uD83D\uDCC4", node.name);
    el.appendChild(icon);
    el.appendChild(name);
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

export function collectSchemes(node, result) {
  if (node.type === "file" && node.name.endsWith(".scheme")) {
    result.push({ path: node.path, name: node.name.replace(/\.scheme$/, "") });
  }
  if (node.type === "directory") {
    (node.children || []).forEach(child => collectSchemes(child, result));
  }
}

export function collectGames(node, result) {
  if (node.type === "file" && node.name.endsWith(".game")) {
    result.push({ path: node.path, name: node.name.replace(/\.game$/, "") });
  }
  if (node.type === "directory") {
    (node.children || []).forEach(child => collectGames(child, result));
  }
}

export async function loadFileTree() {
  const data = await apiFetch("/api/files");
  fileTreeEl.replaceChildren();
  dirLabel.textContent = data.name || "";
  (data.children || []).forEach(child => fileTreeEl.appendChild(buildTree(child, 0)));
  state.primitiveFiles = [];
  collectPrimitives(data, state.primitiveFiles);
  state.primitiveFiles.sort((a, b) => a.name.localeCompare(b.name));
  state.schemeFiles = [];
  collectSchemes(data, state.schemeFiles);
  state.schemeFiles.sort((a, b) => a.name.localeCompare(b.name));
  state.gameFiles = [];
  collectGames(data, state.gameFiles);
  state.gameFiles.sort((a, b) => a.name.localeCompare(b.name));
}
