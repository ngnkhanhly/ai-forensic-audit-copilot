import os
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica", 12)
    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()

# 1. Contract ABC 2026
contract_path = "demo_data/contracts/contract_ABC_2026.pdf"
contract_text = [
    "MASTER SERVICES AGREEMENT",
    "Vendor: ABC Trading Co.",
    "Effective Date: 2026-01-01",
    "Expiration Date: 2026-12-31",
    "Payment Terms: Net 30",
    "Authorized Bank Account: 1234567890 (Bank of Global)",
    "Maximum Monthly Limit: 50,000,000 VND"
]
create_pdf(contract_path, contract_text)

# 2. Invoice INV-001 (Valid)
inv1_path = "demo_data/invoices/invoice_INV-001.pdf"
inv1_text = [
    "INVOICE",
    "Vendor: ABC Trading Co.",
    "Invoice Number: INV-001",
    "Issue Date: 2026-05-12",
    "PO Reference: PO-889",
    "Payment Terms: Net 7", # Flag: Mismatch with contract Net 30
    "Bank Account: 1234567890",
    "Subtotal: 22,727,273 VND",
    "Tax: 2,272,727 VND",
    "Total: 25,000,000 VND"
]
create_pdf(inv1_path, inv1_text)

# 3. Invoice INV001_copy (Fraudulent Near-duplicate)
inv2_path = "demo_data/invoices/invoice_INV001_copy.pdf"
inv2_text = [
    "INVOICE",
    "Vendor: A.B.C Trading Company", # Flag: Fuzzy match
    "Invoice Number: INV001", # Flag: Near duplicate ID
    "Issue Date: 2026-05-13", # Flag: Date +1 day
    "PO Reference: NONE", # Flag: Missing PO
    "Payment Terms: Net 7",
    "Bank Account: 9988221100", # Flag: Account Takeover
    "Subtotal: 22,727,273 VND",
    "Tax: 2,272,727 VND",
    "Total: 25,000,000 VND" # Flag: Exact Amount match
]
create_pdf(inv2_path, inv2_text)

# 4. Purchase Order PO-889
po_path = "demo_data/purchase_orders/purchase_order_PO-889.pdf"
po_text = [
    "PURCHASE ORDER",
    "PO Number: PO-889",
    "Vendor: ABC Trading Co.",
    "Approved Amount: 25,000,000 VND",
    "Date: 2026-05-10"
]
create_pdf(po_path, po_text)

# 5. Payment History
csv_path = "demo_data/payment_history/payment_history.csv"
os.makedirs(os.path.dirname(csv_path), exist_ok=True)
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["payment_id", "vendor_name", "invoice_id", "payment_date", "amount_vnd", "bank_account"])
    writer.writerow(["PAY-1001", "ABC Trading Co.", "INV-000", "2026-04-15", "15000000", "1234567890"])

print("Successfully generated all demo data files!")
