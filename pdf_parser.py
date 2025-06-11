import fitz  # PyMuPDF
import re
import io
from datetime import datetime

def extract_text_from_pdf(file_stream):
    """Extract text from a PDF file stream"""
    if not hasattr(file_stream, 'read'):
        raise ValueError("Invalid file stream: must have a 'read' method")

    file_stream.seek(0)
    file_stream.seek(0, 2)
    file_size = file_stream.tell()
    if file_size == 0:
        raise ValueError("Uploaded PDF file is empty")
    file_stream.seek(0)

    pdf_bytes = file_stream.read()
    if not pdf_bytes:
        raise ValueError("Failed to read PDF content")

    doc = fitz.open("pdf", pdf_bytes)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def clean_amount(amount):
    """Clean currency symbols and commas from amount"""
    if amount:
        return amount.replace('₹', '').replace('$', '').replace(',', '').strip()
    return '0'

def parse_date(date_str):
    """Convert various date formats to DD-MM-YYYY"""
    if not date_str:
        return ''
    try:
        for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%d-%b-%Y', '%Y-%m-%d', '%d %B %Y'):
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                print(f"Parsed date '{date_str}' as {parsed_date.strftime('%d-%m-%Y')} using format {fmt}")
                return parsed_date.strftime('%d-%m-%Y')
            except ValueError:
                continue
        print(f"Failed to parse date '{date_str}': no matching format")
        return ''
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return ''

def parse_invoice_data(text, company_key):
    """Parse invoice data based on supplier key"""
    if company_key == 'SUPPLIER1':
        return parse_supplier1_invoice(text)
    elif company_key == 'SUPPLIER2':
        return parse_supplier2_invoice(text)
    elif company_key == 'SUPPLIER3':
        return parse_supplier3_invoice(text)
    else:
        raise ValueError(f"Unknown company_key: {company_key}")

def parse_supplier1_invoice(text):
    """Parse invoice data for SUPPLIER1"""
    gst_match = re.search(r'GSTIN\s*[:\-]?\s*([0-9A-Z]{15})', text, re.IGNORECASE)
    gstin = gst_match.group(1).strip() if gst_match else ''

    from_block_match = re.search(r'From\s*:?\s*(.*?)GSTIN', text, re.IGNORECASE | re.DOTALL)
    from_block = from_block_match.group(1).strip() if from_block_match else ''
    lines = [line.strip() for line in from_block.split('\n') if line.strip()]
    company = lines[0] if lines else ''
    address = ', '.join(lines[1:]) if len(lines) > 1 else ''

    invoice_no_match = re.search(r'Invoice No\s*[:\-]?\s*(\w+\-?\d+)', text, re.IGNORECASE)
    invoice_no = invoice_no_match.group(1).strip() if invoice_no_match else ''

    date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{2}-[A-Za-z]{3}-\d{4}|\d{4}-\d{2}-\d{2})'
    invoice_date_match = re.search(r'Invoice Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    due_date_match = re.search(r'Due Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    po_number_match = re.search(r'PO Number\s*[:\-]?\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    terms_match = re.search(r'Terms\s*[:\-]?\s*(Net\s*\d+)', text, re.IGNORECASE)
    shipping_method_match = re.search(r'Shipping\s*Method\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
    subtotal_match = re.search(r'Subtotal\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    discount_match = re.search(r'Discount\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    tax_match = re.search(r'Tax.*?\(\d+% GST\)?\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    total_match = re.search(r'Total\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)

    invoice_date = parse_date(invoice_date_match.group(1).strip()) if invoice_date_match else ''
    due_date = parse_date(due_date_match.group(1).strip()) if due_date_match else ''
    po_number = po_number_match.group(1).strip() if po_number_match else ''
    terms = terms_match.group(1).strip() if terms_match else 'Net 30'
    shipping_method = shipping_method_match.group(1).strip() if shipping_method_match else 'Courier'
    subtotal = float(clean_amount(subtotal_match.group(1))) if subtotal_match else 0.0
    discount = float(clean_amount(discount_match.group(1))) if discount_match else 0.0
    tax = float(clean_amount(tax_match.group(1))) if tax_match else 0.0
    total = float(clean_amount(total_match.group(1))) if total_match else 0.0

    return company, gstin, address, invoice_no, terms, shipping_method, subtotal, discount, tax, total, invoice_date, due_date, po_number

def parse_supplier2_invoice(text):
    """Parse invoice data for SUPPLIER2"""
    gst_match = re.search(r'GST\s*ID\s*[:\-]?\s*([0-9A-Z]{15})', text, re.IGNORECASE)
    gstin = gst_match.group(1).strip() if gst_match else ''

    company_match = re.search(r'Global Imports Inc\.', text, re.IGNORECASE)
    company = 'Global Imports Inc.' if company_match else ''
    address_match = re.search(r'456 Global Avenue.*?(?=GST\s*ID|$)', text, re.IGNORECASE | re.DOTALL)
    address = address_match.group(0).strip() if address_match else '456 Global Avenue, New York, NY, 10001, USA'

    invoice_no_match = re.search(r'Invoice\s*#?\s*[:\-]?\s*(\S+)', text, re.IGNORECASE)
    invoice_no = invoice_no_match.group(1).strip() if invoice_no_match else ''

    date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{2}-[A-Za-z]{3}-\d{4}|\d{4}-\d{2}-\d{2})'
    invoice_date_match = re.search(r'Invoice Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    due_date_match = re.search(r'Due Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    po_number_match = re.search(r'PO Number\s*[:\-]?\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    terms_match = re.search(r'Terms\s*[:\-]?\s*(Net\s*\d+)', text, re.IGNORECASE)
    shipping_method_match = re.search(r'Shipping\s*Method\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
    subtotal_match = re.search(r'Subtotal\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    discount_match = re.search(r'Discount\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    tax_match = re.search(r'Tax.*?\(\d+% GST\)?\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    total_match = re.search(r'Total\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)

    invoice_date = parse_date(invoice_date_match.group(1).strip()) if invoice_date_match else ''
    due_date = parse_date(due_date_match.group(1).strip()) if due_date_match else ''
    po_number = po_number_match.group(1).strip() if po_number_match else ''
    terms = terms_match.group(1).strip() if terms_match else 'Net 30'
    shipping_method = shipping_method_match.group(1).strip() if shipping_method_match else 'Freight'
    subtotal = float(clean_amount(subtotal_match.group(1))) if subtotal_match else 0.0
    discount = float(clean_amount(discount_match.group(1))) if discount_match else 0.0
    tax = float(clean_amount(tax_match.group(1))) if tax_match else 0.0
    total = float(clean_amount(total_match.group(1))) if total_match else 0.0

    return company, gstin, address, invoice_no, terms, shipping_method, subtotal, discount, tax, total, invoice_date, due_date, po_number

def parse_supplier3_invoice(text):
    """Parse invoice data for SUPPLIER3"""
    gst_match = re.search(r'GSTIN\s*[:\-]?\s*([0-9A-Z]{15})', text, re.IGNORECASE)
    gstin = gst_match.group(1).strip() if gst_match else ''

    company_match = re.search(r'NexGen Enterprises', text, re.IGNORECASE)
    company = 'NexGen Enterprises' if company_match else ''
    address_match = re.search(r'789 NexGen Road.*?(?=GSTIN|$)', text, re.IGNORECASE | re.DOTALL)
    address = address_match.group(0).strip() if address_match else '789 NexGen Road, Toronto, ON, M5V2T6, Canada'

    invoice_no_match = re.search(r'Invoice\s*Number\s*[:\-]?\s*(\S+)', text, re.IGNORECASE)
    invoice_no = invoice_no_match.group(1).strip() if invoice_no_match else ''

    date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{2}-[A-Za-z]{3}-\d{4}|\d{4}-\d{2}-\d{2})'
    invoice_date_match = re.search(r'Invoice Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    due_date_match = re.search(r'Due Date\s*[:\-]?\s*' + date_pattern, text, re.IGNORECASE)
    po_number_match = re.search(r'PO Number\s*[:\-]?\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    terms_match = re.search(r'Terms\s*[:\-]?\s*(Net\s*\d+)', text, re.IGNORECASE)
    shipping_method_match = re.search(r'Shipping\s*Method\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
    subtotal_match = re.search(r'Subtotal\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    discount_match = re.search(r'Discount\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    tax_match = re.search(r'Tax.*?\(\d+% GST\)?\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)
    total_match = re.search(r'Total\s*[:\-]?\s*INR\s*([\-\d,]+\.?\d*)', text, re.IGNORECASE)

    invoice_date = parse_date(invoice_date_match.group(1).strip()) if invoice_date_match else ''
    due_date = parse_date(due_date_match.group(1).strip()) if due_date_match else ''
    po_number = po_number_match.group(1).strip() if po_number_match else ''
    terms = terms_match.group(1).strip() if terms_match else 'Net 30'
    shipping_method = shipping_method_match.group(1).strip() if shipping_method_match else 'Air'
    subtotal = float(clean_amount(subtotal_match.group(1))) if subtotal_match else 0.0
    discount = float(clean_amount(discount_match.group(1))) if discount_match else 0.0
    tax = float(clean_amount(tax_match.group(1))) if tax_match else 0.0
    total = float(clean_amount(total_match.group(1))) if total_match else 0.0

    return company, gstin, address, invoice_no, terms, shipping_method, subtotal, discount, tax, total, invoice_date, due_date, po_number

def parse_address(full_address):
    """Parse address into components"""
    try:
        parts = full_address.split(',')
        street = parts[0].strip() if len(parts) > 0 else ""
        city = parts[1].strip() if len(parts) > 1 else ""
        state_zip_match = re.search(r'(\w+)\s*-\s*(\d+)', parts[2]) if len(parts) > 2 else None
        state = state_zip_match.group(1).strip() if state_zip_match else ""
        zipcode = state_zip_match.group(2).strip() if state_zip_match else ""
        country = parts[3].strip() if len(parts) > 3 else ""
        return street, city, state, zipcode, country
    except Exception as e:
        print(f"Error parsing address: {e}")
        return "", "", "", "", ""

def parse_line_items(text, invoice_no="", company_key=""):
    """Parse line items based on supplier key"""
    print(f"\n=== DEBUG: Parsing line items for invoice {invoice_no}, company_key {company_key} ===")
    print(f"Text length: {len(text)} characters")
    print("Raw PDF text:")
    print(text[:500] + "..." if len(text) > 500 else text)
    
    items = []

    if company_key == 'SUPPLIER1':
        pattern = re.compile(
            r'(ITEM-\d{4})'                                 # Group 1: Item No
            r'\s+'                                          # Required whitespace
            r'(?:(Premium)\s+)?'                            # Group 2: Optional "Premium"
            r'(Server\s+Rack)\s+'                           # Group 3: "Server Rack"
            r'(with\s+Cooling)'                             # Group 4: "with Cooling"
            r'(?:\s+(and\s+Cable\s+Management))?'           # Group 5: Optional "and Cable Management"
            r'\s+'                                          # Required whitespace
            r'Piece\s+'                                     # Unit
            r'(\d+)\s+'                                     # Group 6: Quantity
            r'([\d.,]+)\s+'                                 # Group 7: Unit Price
            r'([\d.,]+)',                                   # Group 8: Total Price
            re.IGNORECASE
        )
        
        matches = list(pattern.finditer(text))
        print(f"Pattern for SUPPLIER1 found {len(matches)} matches")
        print("Matches:", [(match.group(0), match.groups()) for match in matches])
        
        for match in matches:
            try:
                item_no = match.group(1)
                premium = match.group(2)
                server_rack = match.group(3)
                with_cooling = match.group(4)
                and_cable = match.group(5)
                description = ' '.join(filter(None, [premium, server_rack, with_cooling, and_cable])).strip()
                unit = "Piece"
                quantity = int(match.group(6))
                unit_price = float(clean_amount(match.group(7)))
                total_price = float(clean_amount(match.group(8)))

                items.append({
                    "item_no": item_no,
                    "description": description,
                    "unit": unit,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })
                print(f"  Added: {item_no}, Qty: {quantity}, Price: {unit_price}")
            except (ValueError, IndexError) as e:
                print(f"  Error parsing match: {e}")
    
    elif company_key == 'SUPPLIER2':
        pattern = re.compile(
            r'(ITEM-\d{4})'                                 # Group 1: Item No
            r'\s+'                                          # Required whitespace
            r'([^\n]+?)\s+'                                 # Group 2: Description
            r'(Piece|Unit|Box)\s+'                          # Group 3: Unit
            r'(\d+)\s+'                                     # Group 4: Quantity
            r'([\d.,]+)\s+'                                 # Group 5: Unit Price
            r'([\d.,]+)',                                   # Group 6: Total Price
            re.IGNORECASE
        )
        
        matches = list(pattern.finditer(text))
        print(f"Pattern for SUPPLIER2 found {len(matches)} matches")
        print("Matches:", [(match.group(0), match.groups()) for match in matches])
        
        for match in matches:
            try:
                item_no = match.group(1)
                description = match.group(2).strip()
                unit = match.group(3)
                quantity = int(match.group(4))
                unit_price = float(clean_amount(match.group(5)))
                total_price = float(clean_amount(match.group(6)))

                items.append({
                    "item_no": item_no,
                    "description": description,
                    "unit": unit,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })
                print(f"  Added: {item_no}, Qty: {quantity}, Price: {unit_price}")
            except (ValueError, IndexError) as e:
                print(f"  Error parsing match: {e}")
    
    elif company_key == 'SUPPLIER3':
        pattern = re.compile(
            r'(ITEM-\d{4})'                                 # Group 1: Item No
            r'\s+'                                          # Required whitespace
            r'([^\n]+?)\s+'                                 # Group 2: Description
            r'(Piece|Unit|Set)\s+'                          # Group 3: Unit
            r'(\d+)\s+'                                     # Group 4: Quantity
            r'([\d.,]+)\s+'                                 # Group 5: Unit Price
            r'([\d.,]+)',                                   # Group 6: Total Price
            re.IGNORECASE
        )
        
        matches = list(pattern.finditer(text))
        print(f"Pattern for SUPPLIER3 found {len(matches)} matches")
        print("Matches:", [(match.group(0), match.groups()) for match in matches])
        
        for match in matches:
            try:
                item_no = match.group(1)
                description = match.group(2).strip()
                unit = match.group(3)
                quantity = int(match.group(4))
                unit_price = float(clean_amount(match.group(5)))
                total_price = float(clean_amount(match.group(6)))

                items.append({
                    "item_no": item_no,
                    "description": description,
                    "unit": unit,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })
                print(f"  Added: {item_no}, Qty: {quantity}, Price: {unit_price}")
            except (ValueError, IndexError) as e:
                print(f"  Error parsing match: {e}")
    
    else:
        print(f"Unknown company_key: {company_key}")
    
    print(f"=== Final result: Found {len(items)} line items ===")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['item_no']} - Qty: {item['quantity']} - Price: {item['unit_price']}")
    
    return items

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <invoice_pdf_file>")
        sys.exit(1)

    pdf_file = sys.argv[1]

    with open(pdf_file, "rb") as f:
        text = extract_text_from_pdf(f)

    with open(f"debug_text_{pdf_file.replace('.pdf', '.txt')}", 'w', encoding='utf-8') as debug_file:
        debug_file.write(text)
    print(f"Saved extracted text to debug_text_{pdf_file.replace('.pdf', '.txt')}")

    company, gstin, address, invoice_no, terms, shipping_method, subtotal, discount, tax, total, invoice_date, due_date, po_number = parse_invoice_data(text, "SUPPLIER1")
    line_items = parse_line_items(text, invoice_no, "SUPPLIER1")

    print("Company:", company)
    print("GSTIN:", gstin)
    print("Address:", address)
    print("Invoice No:", invoice_no)
    print("Terms:", terms)
    print("Shipping Method:", shipping_method)
    print("Subtotal:", subtotal)
    print("Discount:", discount)
    print("Tax:", tax)
    print("Total:", total)
    print("Invoice Date:", invoice_date)
    print("Due Date:", due_date)
    print("PO Number:", po_number)
    print(f"\nTotal Line Items Found: {len(line_items)}")
    for item in line_items:
        print(item)