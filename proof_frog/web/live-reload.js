// ── Live reload via Server-Sent Events ──────────────────────────────────────
// Listens for filesystem change events from the server and updates open tabs
// or the file tree accordingly.

import { state, apiFetch } from './state.js';
import { loadFileTree } from './file-tree.js';

// ── Suppress file-change events for UI-initiated saves ──────────────────────

const pendingSaves = new Set();

export function suppressFileChange(path) {
  pendingSaves.add(path);
  setTimeout(() => pendingSaves.delete(path), 5000);
}

// ── Notification bar for dirty-tab conflicts ─────────────────────────────────

function showReloadBar(path, name) {
  // Don't duplicate
  if (document.querySelector(`.reload-bar[data-path="${CSS.escape(path)}"]`)) return;

  const bar = document.createElement("div");
  bar.className = "reload-bar";
  bar.dataset.path = path;

  const msg = document.createElement("span");
  msg.textContent = `"${name}" changed on disk.`;
  const btn = document.createElement("button");
  btn.textContent = "Reload";
  btn.addEventListener("click", async () => {
    await reloadTab(path);
    bar.remove();
  });
  const dismiss = document.createElement("button");
  dismiss.textContent = "Dismiss";
  dismiss.addEventListener("click", () => bar.remove());

  bar.append(msg, btn, dismiss);

  // Insert at the top of the editor wrap for this tab
  const tab = state.tabs.get(path);
  if (tab?.wrap) {
    tab.wrap.prepend(bar);
  }
}

function removeReloadBar(path) {
  const bar = document.querySelector(`.reload-bar[data-path="${CSS.escape(path)}"]`);
  if (bar) bar.remove();
}

// ── Reload a tab's content from disk ─────────────────────────────────────────

async function reloadTab(path) {
  const tab = state.tabs.get(path);
  if (!tab) return;
  try {
    const data = await apiFetch(`/api/file?path=${encodeURIComponent(path)}`);
    if (data.error) return;
    const cursor = tab.cm.getCursor();
    const scroll = tab.cm.getScrollInfo();
    tab.cm.setValue(data.content);
    tab.savedContent = data.content;
    tab.cm.setCursor(cursor);
    tab.cm.scrollTo(scroll.left, scroll.top);
    removeReloadBar(path);
  } catch {
    // Silently ignore fetch errors (file may have been deleted)
  }
}

// ── SSE connection ───────────────────────────────────────────────────────────

let eventSource = null;

export function connectSSE() {
  if (eventSource) return;
  eventSource = new EventSource("/api/events");

  eventSource.onmessage = (e) => {
    let event;
    try {
      event = JSON.parse(e.data);
    } catch {
      return;
    }

    const { type, path } = event;

    if (type === "file_changed") {
      if (pendingSaves.delete(path)) return; // UI-initiated save, ignore
      const tab = state.tabs.get(path);
      if (!tab) return; // File not open, nothing to do
      const currentContent = tab.cm.getValue();
      if (currentContent !== tab.savedContent) {
        // Tab has unsaved edits — show notification
        showReloadBar(path, tab.name);
      } else {
        // No local edits — silently reload
        reloadTab(path);
      }
    } else if (type === "file_created" || type === "file_deleted") {
      loadFileTree();
    }
  };

  let errorCount = 0;
  eventSource.onerror = () => {
    errorCount++;
    // EventSource auto-reconnects; if it fails repeatedly the server is gone
    if (errorCount >= 3 && !document.getElementById("disconnected-banner")) {
      showDisconnectedBanner();
    }
  };

  eventSource.onopen = () => {
    errorCount = 0;
    const banner = document.getElementById("disconnected-banner");
    if (banner) banner.remove();
  };
}

// ── Disconnected banner ──────────────────────────────────────────────────────

function showDisconnectedBanner() {
  const banner = document.createElement("div");
  banner.id = "disconnected-banner";
  banner.textContent = "Server disconnected. Restart the web server and reload this page.";
  document.body.prepend(banner);
}
