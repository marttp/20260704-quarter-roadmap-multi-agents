// Quarter Roadmap Co-Pilot — dashboard interactivity.
// Pure client-side: moves cards between columns when the human decides, and
// recomputes the running capacity delta. No backend persistence (the demo
// shows the decision flow; persistence is a v2 concern).

(function () {
  "use strict";

  // Read the initial capacity envelope from the API once on load.
  let capacity = null;
  let committedHours = 0;

  async function init() {
    try {
      const res = await fetch("/api/state");
      const data = await res.json();
      capacity = data.capacity;
    } catch (e) {
      console.warn("Could not load /api/state; capacity tracker disabled.", e);
    }
  }

  function cardEl(itemId) {
    return document.querySelector(`.card[data-item-id="${itemId}"]`);
  }

  function hoursFor(card) {
    // Prefer remaining effort; fall back to 0.
    const badge = card.querySelector(".badge.team");
    if (badge && /h left/.test(badge.textContent)) {
      const n = parseInt(badge.textContent, 10);
      if (!Number.isNaN(n)) return n;
    }
    return 0;
  }

  function recomputeDelta() {
    if (!capacity) return;
    const remaining = capacity.total_demand_hours - committedHours;
    const banner = document.querySelector(".banner .delta");
    if (banner) {
      const sign = remaining > capacity.initiative_capacity_hours_q3 ? "+" : "";
      banner.textContent = `${sign}${remaining - capacity.initiative_capacity_hours_q3}h (after decisions)`;
    }
  }

  // Global — called from the card buttons' onclick handlers.
  window.moveItem = function (itemId, action) {
    const card = cardEl(itemId);
    if (!card) return;
    const committed = document.getElementById("committed");
    const backlog = document.getElementById("backlog");
    const proposals = document.getElementById("proposals");
    const origin = card.closest(".column");

    if (action === "committed") {
      // Move to Q3 Committed and add its hours to the running tally.
      committed.appendChild(card);
      committedHours += hoursFor(card);
    } else if (action === "deprioritize") {
      // Send back to the original column (Backlog or Proposed).
      // Heuristic: backlog ids start with BACKLOG-, proposals start with Q3-.
      const target = /^BACKLOG-/.test(itemId) ? backlog : proposals;
      target.appendChild(card);
      committedHours = Math.max(0, committedHours - hoursFor(card));
    }
    // Visual feedback so the demo flow is obvious.
    card.style.transition = "box-shadow 0.2s";
    card.style.boxShadow = "0 0 0 2px rgba(74, 222, 128, 0.5)";
    setTimeout(() => (card.style.boxShadow = ""), 600);
    recomputeDelta();
  };

  document.addEventListener("DOMContentLoaded", init);
})();
