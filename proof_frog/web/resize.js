// ── Resize handle setup (side effects only) ───────────────────────────────────

import { outputPane } from './state.js';

(function initPanelHeights() {
  const sidebar = document.getElementById("sidebar");
  const gameHopsPanel = document.getElementById("game-hops-panel");
  function setHeights() {
    const h = sidebar.offsetHeight;
    if (h > 0) {
      gameHopsPanel.style.height = Math.round(h * 0.25) + "px";
    }
  }
  if (sidebar.offsetHeight > 0) {
    setHeights();
  } else {
    requestAnimationFrame(setHeights);
  }
})();

(function setupResize() {
  const handle = document.getElementById("resize-handle");
  let startY, startH;
  handle.addEventListener("mousedown", e => {
    startY = e.clientY;
    startH = outputPane.offsetHeight;
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", () => document.removeEventListener("mousemove", onMove), { once: true });
  });
  function onMove(e) {
    const delta = startY - e.clientY;
    const newH = Math.max(80, Math.min(600, startH + delta));
    outputPane.style.height = newH + "px";
  }
})();

(function setupSidebarResize() {
  const handle = document.getElementById("sidebar-resize-handle");
  const sidebar = document.getElementById("sidebar");
  let startX, startW;
  handle.addEventListener("mousedown", e => {
    startX = e.clientX;
    startW = sidebar.offsetWidth;
    handle.classList.add("dragging");
    function onMove(e) {
      const newW = Math.max(120, Math.min(500, startW + e.clientX - startX));
      sidebar.style.width = newW + "px";
    }
    function onUp() {
      handle.classList.remove("dragging");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
})();

(function setupInnerResize() {
  const handle = document.getElementById("inner-resize-handle");
  const gameHopsPanel = document.getElementById("game-hops-panel");
  let startY, startH;
  handle.addEventListener("mousedown", e => {
    startY = e.clientY;
    startH = gameHopsPanel.offsetHeight;
    handle.classList.add("dragging");
    function onMove(e) {
      const sidebar = document.getElementById("sidebar");
      const maxH = sidebar.offsetHeight - 100;
      const delta = startY - e.clientY;
      const newH = Math.max(80, Math.min(maxH, startH + delta));
      gameHopsPanel.style.height = newH + "px";
    }
    function onUp() {
      handle.classList.remove("dragging");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
})();

