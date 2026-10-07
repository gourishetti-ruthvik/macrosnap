// Onboarding hero: GSAP intro timeline + Motion spring cards.
const GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3/+esm";
const MOTION_URL = "https://cdn.jsdelivr.net/npm/motion@12/+esm";

export default async function ({ parentElement }) {
  const hero = parentElement.querySelector(".hero");
  if (!hero || hero.dataset.ready) return; // reruns re-call us; play the intro once
  hero.dataset.ready = "1";

  splitTitle(hero.querySelector(".title"));
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  hero.style.visibility = "hidden";
  let gsap, motion;
  try {
    [{ gsap }, motion] = await Promise.all([import(GSAP_URL), import(MOTION_URL)]);
  } catch {
    return; // CDN unreachable: the hero just stays static
  } finally {
    hero.style.visibility = "";
  }

  const orbs = hero.querySelectorAll(".orb");
  gsap
    .timeline({ defaults: { ease: "power3.out" } })
    .from(hero.querySelector(".badge"), { y: -14, opacity: 0, duration: 0.5 })
    .from(hero.querySelectorAll(".char"), {
      yPercent: 120, rotate: 10, opacity: 0, duration: 0.8, stagger: 0.05, ease: "back.out(1.8)",
    }, "-=0.2")
    .from(hero.querySelector(".tagline"), { y: 16, opacity: 0, duration: 0.6 }, "-=0.4")
    .from(orbs, { scale: 0, opacity: 0, duration: 0.7, stagger: 0.08, ease: "back.out(2.2)" }, 0.3);

  orbs.forEach((orb, i) =>
    gsap.to(orb, {
      y: "random(-16, 16)", x: "random(-10, 10)", rotate: "random(-14, 14)",
      duration: "random(2.4, 3.8)", repeat: -1, yoyo: true, ease: "sine.inOut", delay: 0.8 + i * 0.15,
    })
  );

  const { animate, hover, stagger } = motion;
  const cards = hero.querySelectorAll(".card");
  animate(cards, { opacity: [0, 1], y: [28, 0] }, {
    type: "spring", stiffness: 220, damping: 18, delay: stagger(0.12, { startDelay: 0.6 }),
  });
  hover(cards, (card) => {
    animate(card, { y: -6, scale: 1.03 }, { type: "spring", stiffness: 420, damping: 16 });
    return () => animate(card, { y: 0, scale: 1 }, { type: "spring", stiffness: 420, damping: 22 });
  });
}

// Wrap each letter in a span; each span carries its offset so one gradient spans the word.
function splitTitle(title) {
  const chars = [...title.textContent].map((c) =>
    Object.assign(document.createElement("span"), { className: "char", textContent: c })
  );
  title.setAttribute("aria-label", title.textContent);
  title.replaceChildren(...chars);
  const first = chars[0], last = chars.at(-1);
  title.style.setProperty("--word-w", `${last.offsetLeft + last.offsetWidth - first.offsetLeft}px`);
  chars.forEach((c) => c.style.setProperty("--char-x", `${c.offsetLeft - first.offsetLeft}px`));
}
