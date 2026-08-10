"""Generate 3 sample text-layer PDFs for the ai-document-processing demo."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")
os.makedirs(OUT, exist_ok=True)

styles = getSampleStyleSheet()


def build(path: str, title: str, body_paras: list[str]):
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6*mm)]
    for p in body_paras:
        story.append(Paragraph(p, styles["BodyText"]))
        story.append(Spacer(1, 4*mm))
    doc.build(story)
    print("wrote", path)


# 1. Invoice
invoice_rows = [
    ["Description", "Qty", "Unit Price", "Amount"],
    ["Software development services", "40h", "$85.00", "$3,400.00"],
    ["Cloud infrastructure setup", "1", "$450.00", "$450.00"],
    ["Project management", "10h", "$95.00", "$950.00"],
    ["", "", "Subtotal", "$4,800.00"],
    ["", "", "Tax (10%)", "$480.00"],
    ["", "", "TOTAL DUE", "$5,280.00"],
]
t = Table(invoice_rows, colWidths=[70*mm, 30*mm, 35*mm, 35*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("PADDING", (0, 0), (-1, -1), 5),
]))
build(os.path.join(OUT, "invoice_2024_0142.pdf"), "INVOICE #2024-0142",
      ["Billed to: Northwind Traders LLC", "Invoice date: 12 June 2024",
       "Due date: 12 July 2024", "Payment terms: Net 30",
       "Issued by: Acme Software Consulting, invoice contact accounting@acme.example",
       "Reference number: REF-8821", ""])
doc = SimpleDocTemplate(os.path.join(OUT, "invoice_2024_0142.pdf"), pagesize=A4,
                        rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
story = [Paragraph("INVOICE #2024-0142", styles["Title"]), Spacer(1, 4*mm)]
for p in ["Billed to: Northwind Traders LLC",
          "Invoice date: 12 June 2024",
          "Due date: 12 July 2024",
          "Payment terms: Net 30",
          "Issued by: Acme Software Consulting",
          "Reference number: REF-8821"]:
    story.append(Paragraph(p, styles["BodyText"]))
story.append(Spacer(1, 4*mm))
story.append(t)
doc.build(story)
print("wrote", os.path.join(OUT, "invoice_2024_0142.pdf"))

# 2. Service agreement
build(os.path.join(OUT, "service_agreement_2024.pdf"), "SERVICE AGREEMENT",
      ["This Service Agreement is entered into on 3 March 2024 between Acme Software Consulting (the Provider) and Northwind Traders LLC (the Client).",
       "1. Scope of Services: The Provider will deliver cloud infrastructure design, implementation and ongoing maintenance for the Client's e-commerce platform.",
       "2. Term: This agreement is effective for 12 months from the start date, renewable by mutual written consent.",
       "3. Fees: The Client shall pay the Provider a monthly fee of $1,900, invoiced on the first business day of each month.",
       "4. Confidentiality: Both parties agree to keep all non-public information strictly confidential.",
       "5. Liability: Total aggregate liability under this agreement shall not exceed the fees paid in the preceding three months.",
       "Signed on behalf of the Provider: A. Rossi. Signed on behalf of the Client: J. Smith."])

# 3. Market analysis report
build(os.path.join(OUT, "q3_2024_market_report.pdf"), "Q3 2024 MARKET ANALYSIS REPORT",
      ["Prepared by the Acme Research Team, September 2024.",
       "Executive Summary: The European e-commerce sector grew 8.2% year-over-year in Q3 2024, driven by mobile commerce and cross-border sales.",
       "Revenue highlights: total addressable market reached $312 billion, with online grocery and electronics showing the strongest growth.",
       "Key findings: 61% of consumers now complete purchases on mobile devices; average order value rose 4.1% to $87.",
       "Recommendations: businesses should prioritize mobile checkout optimization and localized payment methods.",
       "This report is intended for internal distribution only."])
