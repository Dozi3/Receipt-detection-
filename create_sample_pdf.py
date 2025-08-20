#!/usr/bin/env python
"""
Create a sample PDF file with a summary page and a receipt-like page
for testing the receipt detection application.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def create_summary_page(c):
    """Create a summary page with text and a table."""
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, 10 * inch, "Expense Report Summary")
    
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, 9.5 * inch, "Employee: John Doe")
    c.drawString(1 * inch, 9.2 * inch, "Department: Engineering")
    c.drawString(1 * inch, 8.9 * inch, "Report Period: January 1-31, 2023")
    
    # Draw a summary table
    data = [
        ['Date', 'Vendor', 'Category', 'Amount'],
        ['01/05/2023', 'Office Supplies Inc', 'Office Supplies', '$24.99'],
        ['01/12/2023', 'City Parking', 'Transportation', '$15.00'],
        ['01/15/2023', 'Quick Lunch', 'Meals', '$12.50'],
        ['01/22/2023', 'Gas Station', 'Transportation', '$45.75'],
        ['01/28/2023', 'Hotel California', 'Accommodation', '$199.00'],
    ]
    
    table = Table(data, colWidths=[1.2*inch, 2*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    table.wrapOn(c, 6.5*inch, 5*inch)
    table.drawOn(c, 1*inch, 7*inch)
    
    # Add totals
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5.5 * inch, 6.5 * inch, "Total: $297.24")
    
    # Add footer
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, 1 * inch, "This is an automatically generated summary page.")
    c.drawString(1 * inch, 0.75 * inch, "Please see attached receipts for details.")

def create_receipt_page(c):
    """Create a page with a receipt-like image."""
    # Create a rectangle to represent a receipt
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(2*inch, 2*inch, 4*inch, 7*inch, fill=1)
    
    # Add receipt header
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.drawString(3 * inch, 8.5 * inch, "RECEIPT")
    
    # Add receipt content
    c.setFont("Helvetica", 12)
    c.drawString(2.5 * inch, 8 * inch, "Office Supplies Inc.")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, 7.7 * inch, "123 Main Street")
    c.drawString(2.5 * inch, 7.5 * inch, "Anytown, USA 12345")
    c.drawString(2.5 * inch, 7.3 * inch, "Tel: (555) 123-4567")
    
    # Date and receipt number
    c.setFont("Helvetica", 10)
    c.drawString(2.2 * inch, 6.8 * inch, "Date: 01/05/2023")
    c.drawString(2.2 * inch, 6.6 * inch, "Receipt #: R-12345")
    
    # Draw a line
    c.line(2.2*inch, 6.4*inch, 5.8*inch, 6.4*inch)
    
    # Add items
    c.setFont("Helvetica", 10)
    c.drawString(2.2 * inch, 6.1 * inch, "Paper, Letter Size, 500 sheets")
    c.drawString(5.3 * inch, 6.1 * inch, "$12.99")
    
    c.drawString(2.2 * inch, 5.8 * inch, "Pens, Black, 12 pack")
    c.drawString(5.3 * inch, 5.8 * inch, "$8.99")
    
    c.drawString(2.2 * inch, 5.5 * inch, "Stapler")
    c.drawString(5.3 * inch, 5.5 * inch, "$3.01")
    
    # Draw a line
    c.line(2.2*inch, 5.3*inch, 5.8*inch, 5.3*inch)
    
    # Add totals
    c.drawString(2.2 * inch, 5.0 * inch, "Subtotal:")
    c.drawString(5.3 * inch, 5.0 * inch, "$24.99")
    
    c.drawString(2.2 * inch, 4.7 * inch, "Tax:")
    c.drawString(5.3 * inch, 4.7 * inch, "$0.00")
    
    c.drawString(2.2 * inch, 4.4 * inch, "Total:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5.3 * inch, 4.4 * inch, "$24.99")
    
    # Payment information
    c.setFont("Helvetica", 10)
    c.drawString(2.2 * inch, 4.0 * inch, "Payment Method: Credit Card")
    c.drawString(2.2 * inch, 3.7 * inch, "Card Number: XXXX-XXXX-XXXX-1234")
    
    # Thank you message
    c.setFont("Helvetica-Bold", 10)
    c.drawString(3 * inch, 3.0 * inch, "Thank You!")
    c.setFont("Helvetica", 9)
    c.drawString(2.5 * inch, 2.7 * inch, "Please keep this receipt")
    c.drawString(2.7 * inch, 2.5 * inch, "for your records")

def create_sample_pdf(output_path="sample_receipt.pdf"):
    """Create a sample PDF with a summary page and a receipt page."""
    c = canvas.Canvas(output_path, pagesize=letter)
    
    # Create summary page
    create_summary_page(c)
    c.showPage()
    
    # Create receipt page
    create_receipt_page(c)
    c.showPage()
    
    # Save the PDF
    c.save()
    
    print(f"Sample PDF created at: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    create_sample_pdf()
