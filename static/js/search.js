/* TransitNotice – search.js · Search page interactions */
"use strict";

// ── Auto-submit on provider card click ────────────────────
document.querySelectorAll(".provider-filter-card").forEach(card => {
  card.addEventListener("click", function () {
    const prov = this.dataset.provider;
    const sel  = document.getElementById("provider-select");
    if (sel) {
      sel.value = prov;
      document.getElementById("search-form")?.submit();
    }
  });
});

// ── Swap origin / destination ──────────────────────────────
const swapBtn = document.getElementById("btn-swap");
if (swapBtn) {
  swapBtn.addEventListener("click", () => {
    const origin = document.getElementById("origin");
    const dest   = document.getElementById("destination");
    if (origin && dest) {
      [origin.value, dest.value] = [dest.value, origin.value];
    }
  });
}

// ── Highlight search terms in results ─────────────────────
(function () {
  const params  = new URLSearchParams(window.location.search);
  const origin  = (params.get("origin") || "").toLowerCase();
  const dest    = (params.get("destination") || "").toLowerCase();
  if (!origin && !dest) return;

  document.querySelectorAll(".route-origin-dest").forEach(el => {
    el.innerHTML = el.innerHTML.replace(
      new RegExp(`(${escRe(origin)}|${escRe(dest)})`, "gi"),
      m => `<mark style="background:#bfdbfe;color:#1d4ed8;padding:0 2px;border-radius:3px;">${m}</mark>`
    );
  });
})();

function escRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── Results count feedback ─────────────────────────────────
(function () {
  const count = document.querySelectorAll(".route-card").length;
  const el    = document.getElementById("result-count");
  if (el) {
    el.textContent = count === 0
      ? "No services found matching your criteria."
      : `${count} service${count > 1 ? "s" : ""} found.`;
  }
})();

// ── Date picker: set min to today ─────────────────────────
(function () {
  const dp = document.getElementById("travel-date");
  if (dp) dp.min = new Date().toISOString().split("T")[0];
})();

// ── Save route shortcut ────────────────────────────────────
document.querySelectorAll(".btn-save-route").forEach(btn => {
  btn.addEventListener("click", async function (e) {
    e.preventDefault();
    const form = this.closest("form");
    if (!form) return;
    const fd = new FormData(form);
    try {
      const r = await fetch("/saved-routes/add", { method: "POST", body: fd });
      if (r.redirected || r.ok) {
        this.innerHTML = '<i class="bi bi-bookmark-fill"></i>';
        this.classList.add("text-warning");
        this.disabled = true;
      }
    } catch (_) {}
  });
});
