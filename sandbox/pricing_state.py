from __future__ import annotations

import streamlit as st


def service_price_state_key(label: str) -> str:
    return f"price_{label}"


def refresh_service_price_defaults(defaults: dict[str, float]) -> None:
    for label, default_value in defaults.items():
        st.session_state[service_price_state_key(label)] = float(default_value)
