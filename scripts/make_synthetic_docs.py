"""Generate the synthetic PDF documents used by this project.

Everything here is invented: the firm, the clients, the people, the numbers.
No real client data is used anywhere in this repo.

Run:  python scripts/make_synthetic_docs.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "data" / "docs"
STYLES = getSampleStyleSheet()
FIRM = "Harbourline Advisory Pty Ltd (fictional)"

TABLE_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6f0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]
)


def p(text, style="BodyText"):
    return Paragraph(text, STYLES[style])


def table(rows, widths=None):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TABLE_STYLE)
    return t


def build(name, story):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    doc.build(story)
    print("wrote", name)


def money(x):
    return f"${x:,.2f}"


def invoice(number, date, due, client, client_abn, items):
    subtotal = sum(q * price for _, q, price in items)
    gst = round(subtotal * 0.10, 2)
    rows = [["Description", "Qty", "Unit price", "Amount"]]
    rows += [[d, str(q), money(price), money(q * price)] for d, q, price in items]
    story = [
        p(f"TAX INVOICE {number}", "Title"),
        p(f"<b>From:</b> {FIRM}, ABN 00 111 222 333 (synthetic)"),
        p(f"<b>Bill to:</b> {client}, ABN {client_abn} (synthetic)"),
        p(f"<b>Invoice date:</b> {date} &nbsp;&nbsp; <b>Due date:</b> {due}"),
        Spacer(1, 8),
        table(rows, [90 * mm, 15 * mm, 30 * mm, 30 * mm]),
        Spacer(1, 8),
        p(f"<b>Subtotal (excl. GST):</b> {money(subtotal)}"),
        p(f"<b>GST (10%):</b> {money(gst)}"),
        p(f"<b>Total payable (incl. GST):</b> {money(subtotal + gst)}"),
        Spacer(1, 8),
        p("Payment by bank transfer to BSB 000-000, account 12345678 (synthetic). "
          "Please quote the invoice number as the payment reference."),
    ]
    build(f"invoice_{number}.pdf", story)


def payslip():
    rows = [
        ["Item", "This period", "Year to date"],
        ["Gross salary", money(7500.00), money(7500.00)],
        ["PAYG tax withheld", money(1688.00), money(1688.00)],
        ["Salary sacrifice (super)", money(250.00), money(250.00)],
        ["Net pay", money(5562.00), money(5562.00)],
        ["Employer super contribution (12%)", money(900.00), money(900.00)],
    ]
    story = [
        p("PAYSLIP", "Title"),
        p(f"<b>Employer:</b> {FIRM}"),
        p("<b>Employee:</b> Priya Raman (synthetic) &nbsp;&nbsp; <b>Employee ID:</b> HL-0217"),
        p("<b>Pay period:</b> 1 July 2026 to 31 July 2026 &nbsp;&nbsp; <b>Payment date:</b> 31 July 2026"),
        p("<b>Position:</b> Senior Accountant &nbsp;&nbsp; <b>Employment type:</b> Full-time"),
        Spacer(1, 8),
        table(rows, [80 * mm, 40 * mm, 40 * mm]),
        Spacer(1, 8),
        p("Annual leave balance: 11.5 days. Personal leave balance: 6 days."),
        p("Superannuation is paid to: Southern Cross Super Fund (synthetic), member no. 99887766."),
    ]
    build("payslip_2026-07_priya_raman.pdf", story)


def bank_statement():
    # Long enough to spill onto a second page, which is a realistic extraction challenge.
    rows = [["Date", "Description", "Debit", "Credit", "Balance"]]
    balance = 18250.00
    txns = [
        ("01/07/2026", "Opening balance", None, None),
        ("02/07/2026", "Rent - Unit 4, 22 Wharf St", 3200.00, None),
        ("03/07/2026", "Square deposits", None, 4120.50),
        ("04/07/2026", "Coffee bean supplier - Ridge Roasters", 1185.00, None),
        ("05/07/2026", "Electricity - GridCo", 642.18, None),
        ("07/07/2026", "Square deposits", None, 5310.75),
        ("08/07/2026", "Wages run", 6480.00, None),
        ("09/07/2026", "Milk supplier - Valley Dairy", 520.40, None),
        ("10/07/2026", "Square deposits", None, 4987.20),
        ("11/07/2026", "Equipment lease - EspressoCo", 389.00, None),
        ("12/07/2026", "Insurance premium - ShieldCover", 1240.00, None),
        ("14/07/2026", "Square deposits", None, 5102.35),
        ("15/07/2026", "Wages run", 6480.00, None),
        ("16/07/2026", "Harbourline Advisory - INV-1042", 3135.00, None),
        ("17/07/2026", "Square deposits", None, 4630.00),
        ("18/07/2026", "Council rates", 870.55, None),
        ("19/07/2026", "Packaging - EcoCup Supplies", 615.90, None),
        ("21/07/2026", "Square deposits", None, 5560.10),
        ("22/07/2026", "Wages run", 6480.00, None),
        ("23/07/2026", "Water - CityWater", 214.70, None),
        ("24/07/2026", "Square deposits", None, 4890.45),
        ("25/07/2026", "Coffee bean supplier - Ridge Roasters", 1185.00, None),
        ("26/07/2026", "Internet - FibreNet", 109.00, None),
        ("28/07/2026", "Square deposits", None, 5245.80),
        ("29/07/2026", "Wages run", 6480.00, None),
        ("30/07/2026", "Bank fee", 15.00, None),
        ("31/07/2026", "Square deposits", None, 3998.60),
    ]
    for date, desc, debit, credit in txns:
        if debit:
            balance -= debit
        if credit:
            balance += credit
        rows.append([date, desc, money(debit) if debit else "", money(credit) if credit else "", money(balance)])
    story = [
        p("BUSINESS TRANSACTION ACCOUNT STATEMENT", "Title"),
        p("<b>Account name:</b> Bluegum Cafe Pty Ltd (synthetic) &nbsp;&nbsp; <b>BSB:</b> 000-111 &nbsp;&nbsp; "
          "<b>Account:</b> 55667788"),
        p("<b>Statement period:</b> 1 July 2026 to 31 July 2026"),
        Spacer(1, 8),
        p("Important information: this statement was prepared for testing purposes only and contains no real account data. " * 14),
        Spacer(1, 8),
        table(rows, [24 * mm, 70 * mm, 24 * mm, 24 * mm, 26 * mm]),
        Spacer(1, 8),
        p(f"<b>Closing balance at 31 July 2026:</b> {money(balance)}"),
    ]
    build("bank_statement_bluegum_2026-07.pdf", story)


def engagement_policy():
    story = [
        p(f"{FIRM}: Client Engagement and Document Policy", "Title"),
        p("Version 3.2, effective 1 July 2026. Internal document. All rules below are fictional."),
        p("1. Onboarding", "Heading2"),
        p("Every new client must sign an engagement letter before any work begins. The engagement letter "
          "must be countersigned by a director of the firm. Identity verification must be completed for "
          "every individual client and for every director of a company client."),
        p("2. Document deadlines", "Heading2"),
        p("Clients must upload all source documents for an annual return within 10 business days of the "
          "document request being sent. If documents are not received by the deadline, the assigned "
          "accountant sends one reminder, and the job is placed on hold after a further 5 business days."),
        p("3. Review and sign-off", "Heading2"),
        p("All returns are prepared by an accountant and reviewed by a second person before lodgement. "
          "Returns for businesses with annual turnover above $2,000,000 must also be reviewed by a director. "
          "Any return that claims a deduction above $50,000 for a single item requires a written file note "
          "explaining the basis of the claim."),
        p("4. Fees", "Heading2"),
        p("The standard fee for an individual tax return is $330 including GST. A sole trader return is "
          "$770 including GST. Company returns are quoted individually. Invoices are payable within "
          "14 days of the invoice date."),
        p("5. Record retention", "Heading2"),
        p("Client working papers are retained for 7 years from the date of lodgement. After 7 years they "
          "are securely destroyed unless the client has an open dispute or audit."),
        p("6. Use of AI tools", "Heading2"),
        p("AI tools may only be used on synthetic or de-identified data unless the client has given written "
          "consent. Any figure produced by an AI tool must be checked against the source document by the "
          "preparing accountant before it is used in a return."),
    ]
    build("policy_client_engagement_v3.2.pdf", story)


def expense_guide():
    rows = [
        ["Expense type", "Limit", "Receipt required", "Approver"],
        ["Meals while travelling", "$95 per day", "Above $30", "Team lead"],
        ["Taxi / rideshare", "No fixed limit", "Always", "Team lead"],
        ["Accommodation", "$260 per night", "Always", "Director"],
        ["Client entertainment", "$150 per event", "Always", "Director"],
        ["Training courses", "$1,500 per year", "Always", "Director"],
        ["Home office equipment", "$600 per year", "Always", "Practice manager"],
    ]
    story = [
        p(f"{FIRM}: Staff Expense Reimbursement Guide", "Title"),
        p("Effective 1 July 2026. Internal document. All limits below are fictional."),
        p("Staff can claim reimbursement for reasonable work-related expenses within the limits below. "
          "Claims must be submitted within 30 days of the expense, using the expense form in the staff portal."),
        Spacer(1, 8),
        table(rows, [55 * mm, 35 * mm, 35 * mm, 35 * mm]),
        Spacer(1, 8),
        p("Claims above the limit need written approval from a director before the expense is incurred. "
          "Reimbursements are paid with the next payroll run after approval. Alcohol is not reimbursed "
          "except as part of approved client entertainment."),
    ]
    build("guide_staff_expenses_2026.pdf", story)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    invoice(
        "INV-1042", "1 July 2026", "15 July 2026", "Bluegum Cafe Pty Ltd", "44 555 666 777",
        [("Annual company tax return FY2026", 1, 2200.00),
         ("BAS preparation - April to June quarter", 1, 550.00),
         ("Bookkeeping clean-up (hours)", 1, 100.00)],
    )
    invoice(
        "INV-1057", "8 July 2026", "22 July 2026", "Koala Freight Logistics Pty Ltd", "88 999 000 111",
        [("Payroll setup and STP onboarding", 1, 1400.00),
         ("Fringe benefits tax review", 1, 980.00),
         ("Advisory meeting (hours)", 3, 220.00)],
    )
    payslip()
    bank_statement()
    engagement_policy()
    expense_guide()
