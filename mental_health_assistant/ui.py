from __future__ import annotations

from pathlib import Path

import streamlit as st


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CSS_PATH = ASSETS_DIR / "app.css"
HERO_IMAGE_PATH = ASSETS_DIR / "wellness-hero.png"


def load_css() -> None:
    if CSS_PATH.exists():
        st.markdown(
            f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def wellness_badge(level: str) -> str:
    labels = {
        "high": "High Strain",
        "watch": "Watch Pattern",
        "steady": "Steady",
        "starting": "Getting Started",
    }
    return labels.get(level, level.title())

