import os
import sys

def install_and_generate():
    try:
        import reportlab
    except ImportError:
        print("Installing reportlab to generate sample PDFs...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    # Create Invoice PDF
    invoice_path = "sample_invoice.pdf"
    print(f"Generating {invoice_path}...")
    doc = SimpleDocTemplate(invoice_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=20
    )
    
    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=10
    )

    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 10))
    
    # Vendor & Invoice Info
    info_data = [
        [Paragraph("<b>Vendor:</b> ACME Corporation<br/>123 Innovation Way<br/>Tech City, TC 10101", body_style),
         Paragraph("<b>Invoice #:</b> INV-2026-9901<br/><b>Date:</b> 2026-06-12<br/><b>Due Date:</b> 2026-07-12", body_style)]
    ]
    info_table = Table(info_data, colWidths=[300, 200])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Bill To
    story.append(Paragraph("<b>BILL TO:</b><br/>Enterprise Solutions Inc.<br/>456 Corporate Blvd<br/>Suite 800", body_style))
    story.append(Spacer(1, 20))
    
    # Items Table
    items_data = [
        ["Description", "Quantity", "Unit Price", "Total"],
        ["Enterprise AI Document Intelligent System Integration", "1", "$20,000.00", "$20,000.00"],
        ["Cloud Storage & Compute Fee (Q2)", "1", "$4,500.00", "$4,500.00"],
        ["Subtotal", "", "", "$24,500.00"],
        ["Tax (10%)", "", "", "$2,450.00"],
        ["Total", "", "", "$26,950.00"]
    ]
    items_table = Table(items_data, colWidths=[280, 70, 70, 80])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,2), 1, colors.HexColor("#CBD5E1")),
        ('LINEBELOW', (0,3), (-1,-1), 1, colors.HexColor("#94A3B8")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,3), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(items_table)
    
    doc.build(story)
    print(f"Generated {invoice_path} successfully.")

    # Create Contract PDF
    contract_path = "sample_contract.pdf"
    print(f"Generating {contract_path}...")
    doc_contract = SimpleDocTemplate(contract_path, pagesize=letter)
    story_contract = []
    
    contract_title_style = ParagraphStyle(
        'ContractTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=20,
        alignment=1 # Centered
    )
    
    story_contract.append(Paragraph("MUTUAL NON-DISCLOSURE AGREEMENT", contract_title_style))
    story_contract.append(Spacer(1, 15))
    
    p1 = ("This Mutual Non-Disclosure Agreement (\"Agreement\") is entered into on <b>June 12, 2026</b> (\"Effective Date\"), "
          "by and between <b>TechCorp Solutions LLC</b>, having its principal place of business at 100 Silicon Valley Rd, "
          "and <b>Innovate Software Inc.</b>, having its principal place of business at 200 Startup Alley.")
    story_contract.append(Paragraph(p1, body_style))
    story_contract.append(Spacer(1, 10))
    
    h1 = "1. Confidential Information"
    story_contract.append(Paragraph(f"<b>{h1}</b>", styles['Heading3']))
    p2 = ("Receiving Party shall hold the Confidential Information in strict confidence and shall not disclose it to any third party. "
          "Receiving Party shall use the Confidential Information solely for the Purpose of evaluating a potential business relationship. "
          "This obligation shall continue for a period of five (5) years from the date of disclosure.")
    story_contract.append(Paragraph(p2, body_style))
    story_contract.append(Spacer(1, 10))
    
    h2 = "2. Limitation of Liability"
    story_contract.append(Paragraph(f"<b>{h2}</b>", styles['Heading3']))
    p3 = ("NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. "
          "THE MAXIMUM AGGREGATE LIABILITY OF THE DISCLOSING PARTY UNDER THIS AGREEMENT SHALL NOT EXCEED $1,000, BUT THE "
          "RECEIVING PARTY'S LIABILITY FOR BREACH OF CONFIDENTIALITY SHALL BE UNLIMITED.")
    story_contract.append(Paragraph(p3, body_style))
    story_contract.append(Spacer(1, 10))
    
    h3 = "3. Expiration and Term"
    story_contract.append(Paragraph(f"<b>{h3}</b>", styles['Heading3']))
    p4 = "This agreement shall be effective as of the Effective Date and shall expire on <b>July 01, 2026</b>."
    story_contract.append(Paragraph(p4, body_style))
    story_contract.append(Spacer(1, 20))
    
    story_contract.append(Paragraph("IN WITNESS WHEREOF, the parties have executed this Agreement.", body_style))
    
    doc_contract.build(story_contract)
    print(f"Generated {contract_path} successfully.")

if __name__ == "__main__":
    install_and_generate()
