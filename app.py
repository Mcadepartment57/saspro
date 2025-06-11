from flask import Flask, request, render_template, redirect, flash, jsonify, session, url_for
from pdf_parser import extract_text_from_pdf, parse_invoice_data, parse_address, parse_line_items
from db import (
    insert_invoice_with_line_items, check_invoice_exists, get_invoice_by_number,
    get_all_invoices, create_indexes, get_all_suppliers, get_all_items
)
from config import SECRET_KEY, DB_CONNECTION_STRING
import pyodbc
import uuid
import time
import traceback
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Enable pyodbc connection pooling
pyodbc.pooling = True

def get_connection():
    """Get a SQL Server connection"""
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        print("Database connection established successfully")
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {str(e)}")
        raise

@app.route('/', methods=['GET', 'POST'])
def upload_invoice():
    if request.method == 'POST':
        if 'invoice_pdf' not in request.files or 'company_key' not in request.form:
            return jsonify({'success': False, 'error': 'Missing file or supplier selection'}), 400

        file = request.files['invoice_pdf']
        company_key = request.form['company_key']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400

        if file:
            try:
                # Validate company_key and get key_code
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT key_code FROM suppliers WHERE key_name = ?', (company_key,))
                supplier = cursor.fetchone()
                if not supplier:
                    conn.close()
                    return jsonify({'success': False, 'error': 'Invalid supplier selected'}), 400
                key_code = supplier[0]
                conn.close()

                # Validate file size before processing
                file.seek(0, 2)
                file_size = file.tell()
                if file_size == 0:
                    return jsonify({'success': False, 'error': 'Uploaded file is empty'}), 400
                file.seek(0)

                text = extract_text_from_pdf(file)
                company, gstin, address, invoice_no, terms, shipping_method, subtotal, discount, tax, total, invoice_date, due_date, po_number = parse_invoice_data(text, company_key)

                if not company or not gstin or not invoice_no:
                    return jsonify({'success': False, 'error': 'Missing required fields. Please verify the PDF format.'}), 400

                street, city, state, zipcode, country = parse_address(address)
                line_items = parse_line_items(text, invoice_no, company_key)

                # Set key_code for line items
                for item in line_items:
                    item['key_code'] = key_code

                suppliers = get_all_suppliers()
                supplier_name = next((supplier[1] for supplier in suppliers if supplier[0] == company_key), company)

                if 'temp_invoices' not in session:
                    session['temp_invoices'] = {}

                session['temp_invoices'][invoice_no] = {
                    'company_name': company,
                    'gst_number': gstin,
                    'street': street,
                    'city': city,
                    'state': state,
                    'zipcode': zipcode,
                    'country': country,
                    'invoice_no': invoice_no,
                    'terms': terms,
                    'shipping_method': shipping_method,
                    'subtotal': float(subtotal) if isinstance(subtotal, (Decimal, float)) else 0.0,
                    'discount': float(discount) if isinstance(discount, (Decimal, float)) else 0.0,
                    'tax': float(tax) if isinstance(tax, (Decimal, float)) else 0.0,
                    'total': float(total) if isinstance(total, (Decimal, float)) else 0.0,
                    'invoice_date': invoice_date,
                    'due_date': due_date,
                    'po_number': po_number,
                    'line_items': line_items,
                    'key_name': company_key,
                    'supplier_name': supplier_name,
                    'key_code': key_code
                }
                session.modified = True

                return jsonify({'success': True, 'message': f'Invoice {invoice_no} extracted successfully. Redirecting...', 'redirect_url': '/invoices'})

            except Exception as e:
                return jsonify({'success': False, 'error': f'Error processing file: {str(e)}'}), 500

    return render_template('upload_form.html')

@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    try:
        suppliers = get_all_suppliers()
        return jsonify({
            'success': True,
            'suppliers': [{'company_key': key, 'supplier_name': name} for key, name in suppliers]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        items = get_all_items()
        return jsonify({
            'success': True,
            'items': [{
                'item_code': item[0],
                'item_no': item[1],
                'description': item[2],
                'unit': item[3],
                'default_unit_price': float(item[4]) if item[4] is not None else 0.0,
                'category': item[5] or ''
            } for item in items]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/invoices')
def list_invoices():
    try:
        saved_invoices = get_all_invoices()
        temp_invoices = session.get('temp_invoices', {})

        invoices = []
        for invoice in saved_invoices:
            print(f"Invoice {invoice[0]}: invoice_date={invoice[4]}, type={type(invoice[4])}, due_date={invoice[5]}, type={type(invoice[5])}")
            
            invoice_date = invoice[4]
            if isinstance(invoice_date, str) and invoice_date:
                try:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d-%b-%Y'):
                        try:
                            invoice_date = datetime.strptime(invoice_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        invoice_date = None
                except Exception as e:
                    print(f"Error parsing invoice_date '{invoice_date}': {e}")
                    invoice_date = None
            invoice_date_str = invoice_date.strftime('%d-%m-%Y') if invoice_date else 'N/A'

            due_date = invoice[5]
            if isinstance(due_date, str) and due_date:
                try:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d-%b-%Y'):
                        try:
                            due_date = datetime.strptime(due_date, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        due_date = None
                except Exception as e:
                    print(f"Error parsing due_date '{due_date}': {e}")
                    due_date = None
            due_date_str = due_date.strftime('%d-%m-%Y') if due_date else 'N/A'

            invoices.append({
                'invoice_no': invoice[0],
                'company_name': invoice[1],
                'invoice_date': invoice_date_str,
                'due_date': due_date_str,
                'total': float(invoice[2]) if invoice[2] is not None else 0.0,
                'is_temp': False
            })

        for invoice_no, data in temp_invoices.items():
            invoices.append({
                'invoice_no': invoice_no,
                'company_name': data['company_name'],
                'invoice_date': data.get('invoice_date', 'N/A'),
                'due_date': data.get('due_date', 'N/A'),
                'total': float(data.get('total', 0.0)),
                'is_temp': True
            })

        return render_template('invoice_list.html', invoices=invoices)
    except Exception as e:
        print(f"Error retrieving invoices: {str(e)}")
        flash(f"Error retrieving invoices: {str(e)}")
        return redirect('/')

@app.route('/invoice/<invoice_no>')
def view_invoice(invoice_no):
    temp_invoices = session.get('temp_invoices', {})
    if invoice_no in temp_invoices:
        inv = temp_invoices[invoice_no]
        invoice = {
            'invoice_no': inv['invoice_no'],
            'key_code': inv.get('key_code'),
            'invoice_date': inv.get('invoice_date', 'N/A'),
            'due_date': inv.get('due_date', 'N/A'),
            'po_number': inv.get('po_number', 'N/A'),
            'subtotal': float(inv.get('subtotal', 0.0)),
            'discount': float(inv.get('discount', 0.0)),
            'tax': float(inv.get('tax', 0.0)),
            'total': float(inv.get('total', 0.0)),
            'supplier_name': inv.get('supplier_name', inv.get('company_name', 'Unknown')),
            'gst_number': inv.get('gst_number', ''),
            'street': inv.get('street', ''),
            'city': inv.get('city', ''),
            'state': inv.get('state', ''),
            'zipcode': inv.get('zipcode', ''),
            'country': inv.get('country', ''),
            'terms': inv.get('terms', 'N/A'),
            'shipping_method': inv.get('shipping_method', 'N/A')
        }
        line_items = [{
            'key_code': item.get('key_code'),
            'item_no': item.get('item_no'),
            'description': item.get('description', ''),
            'unit': item.get('unit', ''),
            'quantity': item.get('quantity', 0),
            'unit_price': float(item.get('unit_price', 0.0)),
            'total_price': float(item.get('total_price', 0.0)),
            'line_number': item.get('line_number')
        } for item in inv.get('line_items', [])]
        is_temp = True
    else:
        invoice_data, line_items = get_invoice_by_number(invoice_no)
        if not invoice_data:
            flash(f"Invoice {invoice_no} not found.", "error")
            return redirect(url_for('list_invoices'))

        invoice_date = invoice_data[2]
        due_date = invoice_data[3]
        invoice_date_str = invoice_date.strftime('%d-%m-%Y') if invoice_date else 'N/A'
        due_date_str = due_date.strftime('%d-%m-%Y') if due_date else 'N/A'

        invoice = {
            'invoice_no': invoice_data[0],
            'key_code': invoice_data[1],
            'invoice_date': invoice_date_str,
            'due_date': due_date_str,
            'po_number': invoice_data[4] if invoice_data[4] else 'N/A',
            'subtotal': float(invoice_data[5]) if invoice_data[5] is not None else 0.0,
            'discount': float(invoice_data[6]) if invoice_data[6] is not None else 0.0,
            'tax': float(invoice_data[7]) if invoice_data[7] is not None else 0.0,
            'total': float(invoice_data[8]) if invoice_data[8] is not None else 0.0,
            'supplier_name': invoice_data[9],
            'gst_number': invoice_data[10],
            'street': invoice_data[11],
            'city': invoice_data[12],
            'state': invoice_data[13],
            'zipcode': invoice_data[14],
            'country': invoice_data[15],
            'terms': invoice_data[16] if invoice_data[16] else 'N/A',
            'shipping_method': invoice_data[17] if invoice_data[17] else 'N/A'
        }
        line_items = [{
            'key_code': item[0],
            'item_code': item[2],
            'item_no': item[3],
            'description': item[4],
            'unit': item[5],
            'quantity': item[6],
            'unit_price': float(item[7]) if item[7] is not None else 0.0,
            'total_price': float(item[8]) if item[8] is not None else 0.0,
            'line_number': item[9]
        } for item in line_items]
        is_temp = False

    return render_template('invoice_detail.html', invoice=invoice, line_items=line_items, is_temp=is_temp)

@app.route('/api/invoice-details/<invoice_no>')
def get_invoice_details(invoice_no):
    try:
        temp_invoices = session.get('temp_invoices', {})
        if invoice_no in temp_invoices:
            inv = temp_invoices[invoice_no]
            invoice = {
                'invoice_no': inv['invoice_no'],
                'company_name': inv.get('company_name', inv.get('supplier_name', 'Unknown')),
                'gst_number': inv.get('gst_number', ''),
                'street': inv.get('street', ''),
                'city': inv.get('city', ''),
                'state': inv.get('state', ''),
                'zipcode': inv.get('zipcode', ''),
                'country': inv.get('country', ''),
                'invoice_date': inv.get('invoice_date', 'N/A'),
                'due_date': inv.get('due_date', 'N/A'),
                'terms': inv.get('terms', 'N/A'),
                'po_number': inv.get('po_number', 'N/A'),
                'shipping_method': inv.get('shipping_method', 'N/A'),
                'subtotal': float(inv.get('subtotal', 0.0)),
                'discount': float(inv.get('discount', 0.0)),
                'tax': float(inv.get('tax', 0.0)),
                'total': float(inv.get('total', 0.0))
            }
            return jsonify({'success': True, 'invoice': invoice})

        invoice_data, _ = get_invoice_by_number(invoice_no)
        if not invoice_data:
            return jsonify({'success': False, 'error': f'Invoice {invoice_no} not found'}), 404

        invoice_date = invoice_data[2]
        due_date = invoice_data[3]
        invoice_date_str = invoice_date.strftime('%d-%m-%Y') if invoice_date else 'N/A'
        due_date_str = due_date.strftime('%d-%m-%Y') if due_date else 'N/A'

        invoice = {
            'invoice_no': invoice_data[0],
            'company_name': invoice_data[9],
            'gst_number': invoice_data[10] or '',
            'street': invoice_data[11] or '',
            'city': invoice_data[12] or '',
            'state': invoice_data[13] or '',
            'zipcode': invoice_data[14] or '',
            'country': invoice_data[15] or '',
            'invoice_date': invoice_date_str,
            'due_date': due_date_str,
            'terms': invoice_data[16] if invoice_data[16] else 'N/A',
            'po_number': invoice_data[4] if invoice_data[4] else 'N/A',
            'shipping_method': invoice_data[17] if invoice_data[17] else 'N/A',
            'subtotal': float(invoice_data[5]) if invoice_data[5] is not None else 0.0,
            'discount': float(invoice_data[6]) if invoice_data[6] is not None else 0.0,
            'tax': float(invoice_data[7]) if invoice_data[7] is not None else 0.0,
            'total': float(invoice_data[8]) if invoice_data[8] is not None else 0.0
        }
        return jsonify({'success': True, 'invoice': invoice})
    except Exception as e:
        print(f"Error in get_invoice_details for invoice {invoice_no}: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/invoice/<invoice_no>')
def api_get_invoice(invoice_no):
    try:
        temp_invoices = session.get('temp_invoices', {})
        if invoice_no in temp_invoices:
            invoice = temp_invoices[invoice_no]
            return jsonify({
                'invoice': invoice,
                'line_items': invoice['line_items']
            })

        invoice, line_items = get_invoice_by_number(invoice_no)
        if invoice:
            invoice_dict = dict(zip([col[0] for col in invoice.cursor_description], invoice))
            line_items_list = [dict(zip([col[0] for col in line_items[0].cursor_description], item))
                              for item in line_items] if line_items else []
            return jsonify({
                'invoice': invoice_dict,
                'line_items': line_items_list
            })
        else:
            return jsonify({'error': 'Invoice not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-invoice', methods=['POST'])
def update_invoice():
    try:
        data = request.get_json()
        invoice_no = data.get('invoice_no')
        line_items = data.get('line_items', [])
        invoice_data = data.get('invoice_data', {})

        if not invoice_no:
            return jsonify({'success': False, 'error': 'Missing invoice_no'}), 400

        temp_invoices = session.get('temp_invoices', {})
        if invoice_no in temp_invoices:
            temp_invoices[invoice_no].update({
                'company_name': invoice_data.get('company_name', temp_invoices[invoice_no]['company_name']),
                'gst_number': invoice_data.get('gst_number', temp_invoices[invoice_no]['gst_number']),
                'street': invoice_data.get('street', temp_invoices[invoice_no]['street']),
                'city': invoice_data.get('city', temp_invoices[invoice_no]['city']),
                'state': invoice_data.get('state', temp_invoices[invoice_no]['state']),
                'zipcode': invoice_data.get('zipcode', temp_invoices[invoice_no]['zipcode']),
                'country': invoice_data.get('country', temp_invoices[invoice_no]['country']),
                'terms': invoice_data.get('terms', temp_invoices[invoice_no]['terms']),
                'shipping_method': invoice_data.get('shipping_method', temp_invoices[invoice_no]['shipping_method']),
                'subtotal': float(invoice_data.get('subtotal', temp_invoices[invoice_no]['subtotal'])),
                'discount': float(invoice_data.get('discount', temp_invoices[invoice_no]['discount'])),
                'tax': float(invoice_data.get('tax', temp_invoices[invoice_no]['tax'])),
                'total': float(invoice_data.get('total', temp_invoices[invoice_no]['total'])),
                'line_items': line_items,
                'key_code': invoice_data.get('key_code', temp_invoices[invoice_no].get('key_code', ''))
            })
            session['temp_invoices'] = temp_invoices
            session.modified = True
            return jsonify({'success': True, 'message': 'Temporary invoice updated'})

        if not check_invoice_exists(invoice_no):
            return jsonify({'success': False, 'error': 'Invoice does not exist in database'}), 404

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT key_code FROM invoices WHERE invoice_no = ?', (invoice_no,))
        key_code = cursor.fetchone()[0]

        cursor.execute('DELETE FROM invoice_line_items WHERE invoice_no = ?', (invoice_no,))
        conn.commit()

        for index, item in enumerate(line_items, start=1):
            item_no = item.get('item_no', f"ITEM{index}")
            cursor.execute('SELECT item_code FROM items WHERE item_no = ?', (item_no,))
            item_result = cursor.fetchone()
            if item_result:
                item_code = item_result[0]
            else:
                cursor.execute('''
                    INSERT INTO items (item_no, description, unit, default_unit_price)
                    OUTPUT INSERTED.item_code
                    VALUES (?, ?, ?, ?)
                ''', (
                    item_no,
                    item.get('description', ''),
                    item.get('unit', 'Piece'),
                    item.get('unit_price', 0.0)
                ))
                item_code = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO invoice_line_items
                (key_code, invoice_no, item_code, quantity, unit_price, total_price, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                key_code,
                invoice_no,
                item_code,
                item.get('quantity', 0),
                item.get('unit_price', 0.0),
                item.get('total_price', 0.0),
                index
            ))
        conn.commit()

        cursor.execute('SELECT SUM(total_price) FROM invoice_line_items WHERE invoice_no = ?', (invoice_no,))
        subtotal = Decimal(str(cursor.fetchone()[0] or '0.00'))
        tax = Decimal(str(invoice_data.get('tax', '0.00')))
        discount = Decimal(str(invoice_data.get('discount', '0.00')))
        total = subtotal + tax - discount

        cursor.execute('''
            UPDATE invoices
            SET subtotal = ?, tax = ?, discount = ?, total = ?
            WHERE invoice_no = ?
        ''', (
            subtotal,
            tax,
            discount,
            total,
            invoice_no
        ))
        conn.commit()

        return jsonify({'success': True, 'message': 'Invoice updated in database'})
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/save-invoice', methods=['POST'])
def save_invoice():
    try:
        data = request.get_json()
        invoice_no = data.get('invoice_no')

        temp_invoices = session.get('temp_invoices', {})
        if invoice_no not in temp_invoices:
            return jsonify({'success': False, 'error': 'Invoice not found in session'}), 404

        invoice = temp_invoices[invoice_no]
        line_items = invoice['line_items']

        exists = check_invoice_exists(invoice_no)
        if exists:
            return jsonify({'success': False, 'error': 'Invoice already exists in database'}), 400

        invoice_date = invoice['invoice_date']
        due_date = invoice['due_date']
        print(f"Raw dates from session for invoice {invoice_no}: invoice_date={invoice_date}, due_date={due_date}")

        try:
            invoice_date = datetime.strptime(invoice_date.replace('/', '-'), '%d-%m-%Y').strftime('%Y-%m-%d') if invoice_date else None
            due_date = datetime.strptime(due_date.replace('/', '-'), '%d-%m-%Y').strftime('%Y-%m-%d') if due_date else None
        except (ValueError, TypeError) as e:
            print(f"Error parsing dates for invoice {invoice_no}: invoice_date={invoice_date}, due_date={due_date}, error={e}")
            try:
                invoice_date = datetime.strptime(invoice_date, '%d-%b-%Y').strftime('%Y-%m-%d') if invoice_date else None
                due_date = datetime.strptime(due_date, '%d-%b-%Y').strftime('%Y-%m-%d') if due_date else None
            except (ValueError, TypeError) as e2:
                print(f"Error parsing DD-MMM-YYYY dates: {e2}")
                invoice_date = None
                due_date = None

        print(f"Saving invoice {invoice_no}: invoice_date={invoice_date}, due_date={due_date}")

        insert_invoice_with_line_items(
            invoice_no=invoice_no,
            company_name=invoice['company_name'],
            gst_number=invoice['gst_number'],
            street=invoice['street'],
            city=invoice['city'],
            state=invoice['state'],
            zipcode=invoice['zipcode'],
            country=invoice['country'],
            terms=invoice['terms'],
            shipping_method=invoice['shipping_method'],
            subtotal=Decimal(str(invoice['subtotal'])),
            discount=Decimal(str(invoice['discount'])),
            tax=Decimal(str(invoice['tax'])),
            total=Decimal(str(invoice['total'])),
            invoice_date=invoice_date,
            due_date=due_date,
            po_number=invoice['po_number'],
            line_items=line_items,
            key_name=invoice['key_name'],
            supplier_name=invoice['supplier_name']
        )

        del temp_invoices[invoice_no]
        session['temp_invoices'] = temp_invoices
        session.modified = True

        return jsonify({'success': True, 'message': f'Invoice {invoice_no} saved to database'})
    except Exception as e:
        print(f"Error saving invoice {invoice_no}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def delete_line_item(invoice_no, item_code):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM invoice_line_items WHERE invoice_no = ? AND item_code = ?', (invoice_no, item_code))
        rows_affected = cursor.rowcount
        conn.commit()
        print(f"delete_line_item: {rows_affected} rows deleted for item_code {item_code} in invoice {invoice_no}")
        return rows_affected > 0
    except Exception as e:
        print(f"Error deleting line item {item_code}: {str(e)}")
        return False
    finally:
        conn.close()

def update_line_item(invoice_no, item_code, quantity, unit_price, total_price, line_number=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT key_code FROM invoices WHERE invoice_no = ?', (invoice_no,))
        key_code = cursor.fetchone()[0]

        if line_number is None:
            cursor.execute('SELECT line_number FROM invoice_line_items WHERE invoice_no = ? AND item_code = ?', 
                           (invoice_no, item_code))
            existing_item = cursor.fetchone()
            if existing_item:
                line_number = existing_item[0]
            else:
                cursor.execute('SELECT MAX(line_number) FROM invoice_line_items WHERE invoice_no = ?', (invoice_no,))
                max_line_number = cursor.fetchone()[0]
                line_number = 1 if max_line_number is None else max_line_number + 1

        cursor.execute('SELECT * FROM invoice_line_items WHERE invoice_no = ? AND item_code = ?', (invoice_no, item_code))
        exists = cursor.fetchone() is not None

        if exists:
            cursor.execute('''
                UPDATE invoice_line_items
                SET quantity = ?, unit_price = ?, total_price = ?, line_number = ?
                WHERE invoice_no = ? AND item_code = ?
            ''', (quantity, unit_price, total_price, line_number, invoice_no, item_code))
            print(f"Updated item_code {item_code} with line_number {line_number}")
        else:
            cursor.execute('''
                INSERT INTO invoice_line_items (
                    key_code, invoice_no, item_code, quantity, unit_price, total_price, line_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                key_code, invoice_no, item_code, quantity, unit_price, total_price, line_number
            ))
            print(f"Inserted item_code {item_code} with line_number {line_number}")
        conn.commit()
    except Exception as e:
        print(f"Error updating/inserting line item {item_code}: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def update_invoice_totals(invoice_no, subtotal, tax, total):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE invoices SET subtotal = ?, tax = ?, total = ? WHERE invoice_no = ?',
                    (subtotal, tax, total, invoice_no))
        conn.commit()
        print(f"Updated totals for invoice {invoice_no}: subtotal={subtotal}, tax={tax}, total={total}")
    except Exception as e:
        print(f"Error updating invoice totals: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

@app.route('/api/debug-routes')
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify(routes)

@app.route('/api/check-database-health')
def check_database_health():
    try:
        test_connection()
        check_for_hanging_transactions()
        fix_orphaned_line_items()
        debug_database_state()
        return jsonify({
            'success': True,
            'message': 'Database health check completed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def rebuild_indexes():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        print("Rebuilding indexes...")
        cursor.execute('''
            IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoice_line_items_invoice_no')
            ALTER INDEX IX_invoice_line_items_invoice_no ON invoice_line_items REBUILD
        ''')
        cursor.execute('''
            IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoice_line_items_item_code')
            ALTER INDEX IX_invoice_line_items_item_code ON invoice_line_items REBUILD
        ''')
        cursor.execute("UPDATE STATISTICS invoice_line_items WITH FULLSCAN")
        cursor.execute("UPDATE STATISTICS invoices WITH FULLSCAN")
        print("Indexes rebuilt successfully")
        conn.commit()
    except Exception as e:
        print(f"Error rebuilding indexes: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()

def test_connection():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        print("Database connection test successful")
    finally:
        cursor.close()
        conn.close()

def check_for_hanging_transactions():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                t.transaction_id,
                t.name,
                t.transaction_begin_time,
                s.session_id,
                s.host_name,
                s.program_name,
                s.login_name
            FROM sys.dm_tran_active_transactions t
            LEFT JOIN sys.dm_exec_sessions s ON t.transaction_id = s.transaction_id
            WHERE t.transaction_begin_time < DATEADD(MINUTE, -5, GETDATE())
        ''')
        rows = cursor.fetchall()
        if rows:
            print(f"Found {len(rows)} hanging transactions:")
            for row in rows:
                print(f"Transaction ID: {row.transaction_id}, Name: {row.name}, Started: {row.transaction_begin_time}, Session: {row.session_id}")
        else:
            print("No hanging transactions found")
    finally:
        cursor.close()
        conn.close()

def fix_orphaned_line_items():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM invoice_line_items
            WHERE invoice_no NOT IN (SELECT invoice_no FROM invoices)
        ''')
        deleted = cursor.rowcount
        conn.commit()
        print(f"Deleted {deleted} orphaned line items")
    finally:
        cursor.close()
        conn.close()

def debug_database_state():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
        line_item_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM items")
        item_count = cursor.fetchone()[0]
        print(f"Database state: {invoice_count} invoices, {line_item_count} line items, {item_count} items")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_indexes()
    app.run(port=5001, debug=True)