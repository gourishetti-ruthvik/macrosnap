// Macro dashboard: Motion spring rings + GSAP count-up + staggered meal chips.
// Called again on every data change; the shadow root (parentElement) persists, so
// the last-shown values live on it and each update animates from there.
const GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3/+esm";
const MOTION_URL = "https://cdn.jsdelivr.net/npm/motion@12/+esm";

const RINGS = [
  { key: "calories", label: "Calories", unit: "kcal", color: "#10b981" },
  { key: "protein_g", label: "Protein", unit: "g", color: "#6366f1" },
  { key: "carbs_g", label: "Carbs", unit: "g", color: "#f59e0b" },
  { key: "fat_g", label: "Fat", unit: "g", color: "#ec4899" },
];

let libs; // shared across calls: { gsap, motion } or null if the CDN failed
const loadLibs = () =>
  (libs ??= Promise.all([import(GSAP_URL), import(MOTION_URL)])
    .then(([{ gsap }, motion]) => ({ gsap, motion }))
    .catch(() => null));

export default async function ({ parentElement, data }) {
  const { totals, goals, meals } = data;
  const root = parentElement.querySelector(".dash") ?? build(parentElement);
  const shown = (parentElement.shown ??= { totals: Object.fromEntries(RINGS.map((r) => [r.key, 0])), meals: 0 });
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const lib = reduced ? null : await loadLibs();

  root.querySelector(".count").textContent = `${meals.length} meal${meals.length === 1 ? "" : "s"} logged`;

  for (const { key } of RINGS) {
    const ring = root.querySelector(`[data-k="${key}"]`);
    const bar = ring.querySelector(".bar");
    const val = ring.querySelector(".val");
    const pct = Math.min(totals[key] / goals[key], 1) * 100;
    ring.classList.toggle("over", totals[key] > goals[key]);
    ring.querySelector(".goal").textContent = `/ ${goals[key].toLocaleString()}`;

    if (!lib) {
      bar.setAttribute("stroke-dashoffset", 100 - pct);
      val.textContent = totals[key].toLocaleString();
      continue;
    }
    lib.motion.animate(bar, { strokeDashoffset: 100 - pct }, { type: "spring", stiffness: 90, damping: 14 });
    const counter = { v: shown.totals[key] };
    lib.gsap.to(counter, {
      v: totals[key], duration: 1.2, ease: "power2.out", snap: { v: 1 },
      onUpdate: () => (val.textContent = counter.v.toLocaleString()),
    });
  }

  // Meal names come from the LLM: textContent only, never innerHTML.
  const list = root.querySelector(".meals");
  list.replaceChildren(...meals.map((m) =>
    Object.assign(document.createElement("li"), { textContent: `${m.name} · ${m.calories} kcal` })
  ));
  const fresh = [...list.children].slice(shown.meals);
  if (lib && fresh.length) {
    const { animate, stagger } = lib.motion;
    animate(fresh, { opacity: [0, 1], scale: [0.6, 1], y: [8, 0] }, {
      type: "spring", stiffness: 380, damping: 18, delay: stagger(0.08),
    });
  }

  shown.totals = { ...totals };
  shown.meals = meals.length;
}

function build(parentElement) {
  const root = document.createElement("section");
  root.className = "dash";
  root.innerHTML = `
    <div class="head"><h3>Today's macros</h3><span class="count"></span></div>
    <div class="rings">${RINGS.map((r) => `
      <figure class="ring" data-k="${r.key}" style="--c: ${r.color}">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle class="track" cx="60" cy="60" r="50" pathLength="100"></circle>
          <circle class="bar" cx="60" cy="60" r="50" pathLength="100" stroke-dashoffset="100"></circle>
        </svg>
        <div class="center"><span class="val">0</span><span class="goal"></span></div>
        <figcaption>${r.label} (${r.unit})</figcaption>
      </figure>`).join("")}
    </div>
    <ul class="meals"></ul>`;
  parentElement.appendChild(root);
  return root;
}
