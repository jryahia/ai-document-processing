"""Generate 2 additional demo test documents (lease agreement + utility bill)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")
os.makedirs(OUT, exist_ok=True)
styles = getSampleStyleSheet()


def build(path: str, title: str, paras: list[str], table_rows: list[list[str]] | None = None):
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6*mm)]
    for p in paras:
        story.append(Paragraph(p, styles["BodyText"]))
        story.append(Spacer(1, 4*mm))
    if table_rows:
        t = Table(table_rows, colWidths=[70*mm, 30*mm, 35*mm, 35*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    doc.build(story)
    print("wrote", path)


# 1. Residential lease agreement
build(
    os.path.join(OUT, "lease_agreement_2024.pdf"),
    "RESIDENTIAL LEASE AGREEMENT",
    [
        "This Residential Lease Agreement is made on 15 January 2024 between Luca Bianchi (the Landlord) and Giulia Romano (the Tenant).",
        "Property: Apartment 4B, Via Garibaldi 28, 20121 Milan, Italy.",
        "1. Term: The lease begins on 1 February 2024 and ends on 31 January 2026 (24 months).",
        "2. Rent: The monthly rent is EUR 1,150, payable by the 5th of each month to account IT60X0542811101000000123456.",
        "3. Deposit: A security deposit of EUR 2,300 was paid by the Tenant on 28 January 2024.",
        "4. Utilities: Water, electricity and gas are the responsibility of the Tenant; condo fees of EUR 180 per month are included in the rent.",
        "5. Notice: Either party may terminate with 3 months written notice.",
        "Signed: Luca Bianchi (Landlord), Giulia Romano (Tenant). Contract reference: LEASE-MI-2024-0117.",
    ],
)

# 2. Utility bill (electricity)
build(
    os.path.join(OUT, "electricity_bill_august.pdf"),
    "ELECTRICITY BILL - AUGUST 2024",
    [
        "Customer: Giulia Romano, Apartment 4B, Via Garibaldi 28, 20121 Milan.",
        "Supplier: Enel Energia S.p.A., customer number 3002456789.",
        "Bill date: 2 September 2024. Due date: 22 September 2024. Billing period: 1 August - 31 August 2024.",
        "Invoice number: INV-2024-884521. Contract: C/2045/88912.",
        "Consumption: 214 kWh at EUR 0.31/kWh.",
        "Fixed charges: EUR 12.50. Network charges: EUR 28.40. Taxes (10%): EUR 9.31.",
        "TOTAL AMOUNT DUE: EUR 116.57. Payment methods: direct debit, credit card, or bank transfer to IT60X0542811101000000123456.",
        "Late payment penalty: 1.5% per month after the due date.",
    ],
)
