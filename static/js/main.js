/* TransitNotice – main.js  · Global JS */
"use strict";

// ── Flash message auto-dismiss ─────────────────────────────
document.querySelectorAll(".alert.alert-dismissible").forEach(el => {
  setTimeout(() => {
    el.style.transition = "opacity .5s ease";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 500);
  }, 5000);
});

// ── Active nav link ────────────────────────────────────────
(function () {
  const path = window.location.pathname;
  document.querySelectorAll(".navbar-nav .nav-link").forEach(link => {
    if (link.getAttribute("href") && path.startsWith(link.getAttribute("href")) && link.getAttribute("href") !== "/") {
      link.classList.add("active");
    }
  });
})();

// ── Notification badge polling ─────────────────────────────
(function () {
  const badge = document.getElementById("notif-badge");
  if (!badge) return;

  async function pollCount() {
    try {
      const r = await fetch("/api/notifications/unread-count");
      if (!r.ok) return;
      const data = await r.json();
      const count = data.count || 0;
      badge.textContent = count > 0 ? count : "";
      badge.style.display = count > 0 ? "inline-block" : "none";
    } catch (_) {}
  }

  pollCount();
  setInterval(pollCount, 30000);
})();

// ── Mark notification read on click ───────────────────────
document.addEventListener("click", async function (e) {
  const btn = e.target.closest("[data-mark-read]");
  if (!btn) return;
  const id = btn.dataset.markRead;
  try {
    await fetch(`/notifications/${id}/read`, { method: "POST" });
    const item = btn.closest(".notif-item");
    if (item) item.classList.remove("unread");
  } catch (_) {}
});

// ── Source-status live ticker (SSE) ───────────────────────
(function () {
  const ticker = document.getElementById("live-ticker");
  if (!ticker || !window.EventSource) return;

  const es = new EventSource("/api/sse/updates");

  es.onmessage = function (e) {
    try {
      const changes = JSON.parse(e.data);
      if (!Array.isArray(changes) || changes.length === 0) return;
      changes.forEach(ch => {
        const item = document.createElement("div");
        item.className = "alert-transit alert-transit-info fade-in mb-2";
        item.innerHTML = `
          <i class="bi bi-info-circle-fill"></i>
          <strong>${ch.provider || ""} ${ch.route_number || ""}</strong>
          – ${formatChangeType(ch.change_type)}:
          <span style="text-decoration:line-through">${ch.old_value || ""}</span>
          → <strong>${ch.new_value || ""}</strong>`;
        ticker.prepend(item);
        setTimeout(() => { item.style.opacity = "0"; item.style.transition = "opacity 1s"; setTimeout(() => item.remove(), 1000); }, 8000);
      });
    } catch (_) {}
  };

  es.onerror = function () { es.close(); };
})();

function formatChangeType(ct) {
  const map = {
    departure_change: "Departure changed",
    arrival_change: "Arrival changed",
    cancellation: "Cancelled",
    diversion: "Diversion",
    new_schedule: "New schedule",
    service_resumption: "Service resumed",
  };
  return map[ct] || ct;
}

// ── Tooltip init ───────────────────────────────────────────
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
  new bootstrap.Tooltip(el);
});

// ── Confirm dialogs ────────────────────────────────────────
document.querySelectorAll("[data-confirm]").forEach(el => {
  el.addEventListener("click", function (e) {
    if (!confirm(this.dataset.confirm || "Are you sure?")) e.preventDefault();
  });
});

// ── Admin: trigger manual collection ──────────────────────
const runNowBtn = document.getElementById("btn-run-collection");
if (runNowBtn) {
  runNowBtn.addEventListener("click", async function () {
    this.disabled = true;
    this.innerHTML = '<span class="loading-spinner"></span> Running…';
    try {
      const r = await fetch("/admin/api/run-collection", { method: "POST" });
      const d = await r.json();
      alert(d.message || d.error || "Done.");
    } catch (_) {
      alert("Request failed.");
    } finally {
      this.disabled = false;
      this.innerHTML = '<i class="bi bi-play-fill"></i> Run Now';
    }
  });
}
