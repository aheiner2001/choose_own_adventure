from __future__ import annotations

from datetime import date
from io import BytesIO

import streamlit as st
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pdf_share import build_download_url, build_qr_image_url, get_pdf, register_pdf
from pricing_state import refresh_service_price_defaults


COMPANY_NAME = "FreshPane Solutions LLC"
SERVICE_NAME = "Window Cleaning Bid Generator"
BUSINESS_PHONE_PLACEHOLDER = "(208) 960-9883"
BUSINESS_EMAIL_PLACEHOLDER = "freshpanesolutionsllc@gmail.com"


def money(value: float) -> str:
    return f"${value:,.2f}"


def compute_defaults(exterior_price: float) -> dict[str, float]:
    interior_default = exterior_price * 0.70
    kitchen_main_default = interior_default * 0.50
    front_only_default = max(exterior_price * 0.60, 100.0)
    return {
        "Exterior Cleaning": exterior_price,
        "Interior Cleaning": interior_default,
        "Interior Kitchen/Main Windows": kitchen_main_default,
        "Front-Only Exterior": front_only_default,
    }


def build_pdf(
    quote_date: date,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    customer_address: str,
    quote_items: list[tuple[str, float]],
    notes: str,
    total: float,
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    y = height - 0.75 * inch

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(0.75 * inch, y, COMPANY_NAME)
    y -= 0.3 * inch

    pdf.setFont("Helvetica", 11)
    pdf.drawString(0.75 * inch, y, "Window Cleaning Bid")
    y -= 0.2 * inch
    pdf.drawString(0.75 * inch, y, f"Date: {quote_date.isoformat()}")
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.75 * inch, y, "Customer")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(0.75 * inch, y, f"Name: {customer_name or 'TBD'}")
    y -= 0.18 * inch
    pdf.drawString(0.75 * inch, y, f"Phone: {customer_phone or 'TBD'}")
    y -= 0.18 * inch
    pdf.drawString(0.75 * inch, y, f"Email: {customer_email or 'TBD'}")
    y -= 0.18 * inch
    pdf.drawString(0.75 * inch, y, f"Address: {customer_address or 'TBD'}")
    y -= 0.35 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.75 * inch, y, "Quoted Services")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 11)

    customization_note = (
        "This bid includes recommended pricing and is fully customizable."
    
    )
    pdf.drawString(0.75 * inch, y, customization_note)
    y -= 0.25 * inch

    for service_name, service_price in quote_items:
        pdf.drawString(0.85 * inch, y, f"- {service_name}")
        pdf.drawRightString(width - 0.75 * inch, y, money(service_price))
        y -= 0.2 * inch
        if y < 1.2 * inch:
            pdf.showPage()
            y = height - 0.75 * inch
            pdf.setFont("Helvetica", 11)

    y -= 0.1 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.75 * inch, y, "Total")
    pdf.drawRightString(width - 0.75 * inch, y, money(total))
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.75 * inch, y, "Notes")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 11)
    for line in (notes or "No additional notes.").splitlines():
        pdf.drawString(0.85 * inch, y, line)
        y -= 0.18 * inch
        if y < 1.0 * inch:
            pdf.showPage()
            y = height - 0.75 * inch
            pdf.setFont("Helvetica", 11)

    y -= 0.1 * inch
    if y < 1.2 * inch:
        pdf.showPage()
        y = height - 0.75 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(0.75 * inch, y, "Schedule First Appointment")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(0.85 * inch, y, f"Business Phone: {BUSINESS_PHONE_PLACEHOLDER}")
    y -= 0.18 * inch
    pdf.drawString(0.85 * inch, y, f"Business Email: {BUSINESS_EMAIL_PLACEHOLDER}")

    pdf.save()
    buffer.seek(0)
    return buffer.read()


st.set_page_config(page_title="FreshPane Bid PDF Generator", page_icon="🧼", layout="centered")
st.title(f"{COMPANY_NAME} - {SERVICE_NAME}")
st.caption(
    "Create a quote with recommended pricing, customize any service selection, and "
    "download a customer-ready PDF."
)

download_token = st.query_params.get("download_token")
if download_token:
    stored_pdf = get_pdf(download_token)
    if stored_pdf:
        file_name, pdf_bytes = stored_pdf
        st.subheader("Download Your Bid")
        st.download_button(
            label="Download Bid PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True,
        )
        st.stop()
    st.warning("This bid link is unavailable. Ask your provider to share a fresh QR code.")
    st.stop()

st.subheader("Customer Details")
customer_name = st.text_input("Customer Name", placeholder="e.g., Jamie Smith")
customer_phone = st.text_input("Phone", placeholder="(555) 555-5555")
customer_email = st.text_input("Email", placeholder="customer@email.com")
customer_address = st.text_input("Service Address", placeholder="123 Main St, City, ST")
quote_date = st.date_input("Quote Date", value=date.today())

st.subheader("Pricing Inputs")
step_amount = st.number_input("Increment step", min_value=1.0, value=5.0, step=1.0)
if "exterior_base_quote" not in st.session_state:
    st.session_state["exterior_base_quote"] = 200.0
exterior_price = st.number_input(
    "Exterior base quote",
    min_value=0.0,
    step=step_amount,
    key="exterior_base_quote",
    help="Primary quote used to calculate defaults.",
)

defaults = compute_defaults(exterior_price)
if st.button("Refresh default prices"):
    refresh_service_price_defaults(defaults)
    st.success("Service prices refreshed from the current exterior quote.")

selected_items: list[tuple[str, float]] = []

st.subheader("Service Options")
for label, default_value in defaults.items():
    with st.container(border=True):
        include_service = st.checkbox(f"Include {label}", value=True, key=f"include_{label}")
        st.caption(f"Default: {money(default_value)}")
        price_key = f"price_{label}"
        if price_key not in st.session_state:
            st.session_state[price_key] = float(default_value)
        edited_price = st.number_input(
            f"{label} price",
            min_value=0.0,
            step=step_amount,
            key=price_key,
        )
        if include_service:
            selected_items.append((label, edited_price))

total_price = sum(price for _, price in selected_items)
st.markdown(f"### Total Quote: `{money(total_price)}`")

notes = st.text_area("Notes for customer", placeholder="Optional details about scope, schedule, etc.")

if selected_items:
    pdf_bytes = build_pdf(
        quote_date=quote_date,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        customer_address=customer_address,
        quote_items=selected_items,
        notes=notes,
        total=total_price,
    )

    file_stub = (customer_name.strip().replace(" ", "_") or "customer").lower()
    st.download_button(
        label="Download Bid PDF",
        data=pdf_bytes,
        file_name=f"freshpane_bid_{file_stub}.pdf",
        mime="application/pdf",
    )

    st.subheader("Customer QR Download")
    default_base_url = st.session_state.get("public_base_url", "http://localhost:8501")
    public_base_url = st.text_input(
        "Public app URL for customer QR",
        value=default_base_url,
        help="Set this to the shareable app URL customers can reach (not localhost).",
    ).strip()
    st.session_state["public_base_url"] = public_base_url

    shared_file_name = f"freshpane_bid_{file_stub}.pdf"
    pdf_token = register_pdf(shared_file_name, pdf_bytes)
    qr_download_url = build_download_url(public_base_url, pdf_token)
    qr_image_url = build_qr_image_url(qr_download_url)
    st.image(qr_image_url, caption="Scan to open bid download page", width=220)
    st.caption("This QR updates automatically whenever quote inputs change.")
    st.code(qr_download_url, language="text")
else:
    st.info("Select at least one service option to generate a PDF.")
