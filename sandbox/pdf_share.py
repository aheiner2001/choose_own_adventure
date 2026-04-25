from __future__ import annotations

import hashlib
from urllib.parse import quote

import streamlit as st


@st.cache_resource
def _pdf_store() -> dict[str, tuple[str, bytes]]:
    return {}


def register_pdf(file_name: str, pdf_bytes: bytes) -> str:
    token = hashlib.sha256(pdf_bytes).hexdigest()[:16]
    _pdf_store()[token] = (file_name, pdf_bytes)
    return token


def get_pdf(token: str) -> tuple[str, bytes] | None:
    return _pdf_store().get(token)


def build_download_url(base_url: str, token: str) -> str:
    clean_base = base_url.rstrip("/")
    return f"{clean_base}/?download_token={token}"


def build_qr_image_url(value: str, size: int = 240) -> str:
    encoded = quote(value, safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}"
