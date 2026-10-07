"""Animated UI pieces, built as Streamlit Components v2 (inline HTML/CSS/JS, no iframes).

The markup, styles and scripts live in frontend/. GSAP and Motion load from jsDelivr
inside the components; if the CDN is unreachable, everything still renders, just static.
"""
from pathlib import Path

import streamlit as st

FRONTEND = Path(__file__).parent / "frontend"


def _read(name):
    return (FRONTEND / name).read_text(encoding="utf-8")


_hero = st.components.v2.component(
    "macrosnap_hero", html=_read("hero.html"), css=_read("hero.css"), js=_read("hero.js")
)
_dashboard = st.components.v2.component(
    "macrosnap_dashboard", css=_read("dashboard.css"), js=_read("dashboard.js")
)


def inject_theme():
    st.html(FRONTEND / "theme.css")


def hero():
    _hero(key="hero")


def macro_dashboard(totals, goals, meals):
    _dashboard(
        key="dashboard",
        data={
            "totals": totals,
            "goals": goals,
            "meals": [{"name": m["name"], "calories": m["calories"]} for m in meals],
        },
    )
