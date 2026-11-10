/* TransitNotice – notifications.js */
"use strict";

// ── Mark all read ──────────────────────────────────────────
const markAllBtn = document.getElementById("btn-mark-all-read");
if (markAllBtn) {
  markAllBtn.addEventListener("click", async function () {
    try {
      await fetch("/notifications/read-all", { method: "POST" });
      document.querySelectorAll(".notif-item.unread").forEach(el => {
        el.classList.remove("unread");
      });
      const badge = document.getElementById("notif-badge");
      if (badge) { badge.textContent = ""; badge.style.display = "none"; }
      this.style.display = "none";
    } catch (_) {}
  });
}

// ── Click to mark individual read ─────────────────────────
document.querySelectorAll(".notif-item[data-notif-id]").forEach(item => {
  item.addEventListener("click", async function () {
    const id = this.dataset.notifId;
    if (!this.classList.contains("unread")) return;
    try {
      await fetch(`/notifications/${id}/read`, { method: "POST" });
      this.classList.remove("unread");
    } catch (_) {}
  });
});
