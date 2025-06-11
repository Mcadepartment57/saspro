import pyodbc
from config import DB_CONNECTION_STRING
from contextlib import contextmanager
import time
import traceback
from datetime import datetime
from decimal import Decimal

# Enable pyodbc connection pooling
pyodbc.pooling = True

def get_connection():
    """Get a SQL Server connection"""
    return pyodbc.connect(DB_CONNECTION_STRING)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

def create_tables():
    """Create necessary database tables with transaction handling"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            try:
                # Create suppliers table (master table)
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'suppliers')
                    CREATE TABLE suppliers (
                        key_code INT IDENTITY(1,1) PRIMARY KEY,
                        key_name NVARCHAR(50) NOT NULL,
                        supplier_name NVARCHAR(255) NOT NULL,
                        supplier_email NVARCHAR(255),
                        supplier_phone NVARCHAR(20),
                        contact_person NVARCHAR(100),
                        supplier_country NVARCHAR(200),
                        company_name NVARCHAR(510) NOT NULL,
                        gst_number NVARCHAR(30) NOT NULL,
                        street NVARCHAR(510) NOT NULL,
                        city NVARCHAR(200) NOT NULL,
                        state NVARCHAR(200) NOT NULL,
                        zipcode NVARCHAR(40) NOT NULL,
                        country NVARCHAR(200) NOT NULL,
                        terms NVARCHAR(200) NOT NULL,
                        shipping_method NVARCHAR(200) NOT NULL
                    )
                ''')

                # Create items table (master table for line items)
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'items')
                    CREATE TABLE items (
                        item_code INT IDENTITY(1000,1) PRIMARY KEY,
                        CONSTRAINT CHK_item_code_4_digits CHECK (item_code BETWEEN 1000 AND 9999),
                        item_no NVARCHAR(50) NOT NULL UNIQUE,
                        description NVARCHAR(255) NOT NULL,
                        unit NVARCHAR(50) NOT NULL,
                        default_unit_price DECIMAL(18,2) NULL,
                        category NVARCHAR(100) NULL
                    )
                ''')

                # Create invoices table
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'invoices')
                    CREATE TABLE invoices (
                        invoice_no NVARCHAR(50) PRIMARY KEY,
                        key_code INT NOT NULL,
                        invoice_date DATE NULL,
                        due_date DATE NULL,
                        po_number NVARCHAR(100) NOT NULL,
                        subtotal DECIMAL(10,2) NULL,
                        discount DECIMAL(10,2) NULL,
                        tax DECIMAL(10,2) NULL,
                        total DECIMAL(10,2) NULL,
                        FOREIGN KEY (key_code) REFERENCES suppliers(key_code)
                    )
                ''')

                # Create invoice_line_items table
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'invoice_line_items')
                    CREATE TABLE invoice_line_items (
                        key_code INT NOT NULL,
                        invoice_no NVARCHAR(50) NOT NULL,
                        item_code INT NOT NULL,
                        quantity INT NOT NULL,
                        unit_price DECIMAL(18,2) NOT NULL,
                        total_price DECIMAL(18,2) NOT NULL,
                        line_number INT NOT NULL,
                        PRIMARY KEY (invoice_no, line_number),
                        FOREIGN KEY (key_code) REFERENCES suppliers(key_code),
                        FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no),
                        FOREIGN KEY (item_code) REFERENCES items(item_code)
                    )
                ''')

                # Seed suppliers table
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM suppliers WHERE key_name = 'SUPPLIER1')
                    INSERT INTO suppliers (
                        key_name, supplier_name, supplier_email, supplier_phone, contact_person, supplier_country,
                        company_name, gst_number, street, city, state, zipcode, country,
                        terms, shipping_method
                    )
                    VALUES
                        ('SUPPLIER1', 'Tech Solutions Pvt. Ltd.', 'contact@techsolutions.in', '+91-80-12345678', 'Amit Sharma', 'India',
                        'Tech Solutions Pvt. Ltd.', '29AABC1234K1Z5', '123 Tech Street', 'Bangalore', 'Karnataka', '560001', 'India',
                        'Net 30', 'Courier'),
                        ('SUPPLIER2', 'Global Imports Inc.', 'info@globalimports.com', '+1-212-555-0101', 'John Doe', 'USA',
                        'Global Imports Inc.', '19BBCD5678M1Z7', '456 Global Avenue', 'New York', 'NY', '10001', 'USA',
                        'Net 30', 'Freight'),
                        ('SUPPLIER3', 'NexGen Enterprises', 'support@nexgen.ca', '+1-416-555-0199', 'Sarah Lee', 'Canada',
                        'NexGen Enterprises', '39CCDE9012N1Z3', '789 NexGen Road', 'Toronto', 'ON', 'M5V2T6', 'Canada',
                        'Net 30', 'Air')
                ''')

                # Seed items table
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM items WHERE item_no = 'ITEM-0001')
                    INSERT INTO items (item_no, description, unit, default_unit_price, category)
                    VALUES
                        ('ITEM-0001', 'Premium Server Rack with Cooling', 'Piece', 1000.00, 'Electronics'),
                        ('ITEM-0002', 'Server Rack with Cooling and Cable Management', 'Piece', 1200.00, 'Electronics'),
                        ('ITEM-0003', 'Standard Widget', 'Piece', 50.00, 'Components'),
                        ('ITEM-0004', 'High-Capacity Gadget', 'Piece', 200.00, 'Components')
                ''')

                conn.commit()
                print("Tables created and seeded successfully")
            except Exception as e:
                conn.rollback()
                print(f"Error creating tables: {str(e)}")
                raise
            finally:
                conn.autocommit = True
    except Exception as e:
        print(f"Failed to create tables: {str(e)}")
        traceback.print_exc()

def create_indexes():
    """Create necessary indexes with transaction handling"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoice_line_items_invoice_no')
                    CREATE NONCLUSTERED INDEX IX_invoice_line_items_invoice_no ON invoice_line_items (invoice_no)
                ''')
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoice_line_items_item_code')
                    CREATE NONCLUSTERED INDEX IX_invoice_line_items_item_code ON invoice_line_items (item_code)
                ''')
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoices_key_code')
                    CREATE NONCLUSTERED INDEX IX_invoices_key_code ON invoices (key_code)
                ''')
                cursor.execute('''
                    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_invoice_line_items_key_code')
                    CREATE NONCLUSTERED INDEX IX_invoice_line_items_key_code ON invoice_line_items (key_code)
                ''')
                conn.commit()
                print("Indexes created successfully")
            except Exception as e:
                conn.rollback()
                print(f"Error creating indexes: {str(e)}")
                raise
            finally:
                conn.autocommit = True
    except Exception as e:
        print(f"Failed to create indexes: {str(e)}")
        traceback.print_exc()

def optimize_connection_settings():
    """Configure SQL Server-specific optimizations with transaction handling"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            try:
                cursor.execute("SET ARITHABORT ON")
                cursor.execute("SET NUMERIC_ROUNDABORT OFF")
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                conn.commit()
                print("Connection settings optimized successfully")
            except Exception as e:
                conn.rollback()
                print(f"Error optimizing connection settings: {str(e)}")
                raise
            finally:
                conn.autocommit = True
    except Exception as e:
        print(f"Failed to optimize connection settings: {str(e)}")
        traceback.print_exc()

def get_all_suppliers():
    """Retrieve all suppliers from the suppliers table"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key_name, supplier_name FROM suppliers ORDER BY supplier_name")
            suppliers = cursor.fetchall()
            print(f"Retrieved {len(suppliers)} suppliers")
            return suppliers
    except Exception as e:
        print(f"Error retrieving suppliers: {str(e)}")
        traceback.print_exc()
        return []

def get_all_items():
    """Retrieve all items from the items table"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_code, item_no, description, unit, default_unit_price, category FROM items ORDER BY item_no")
            items = cursor.fetchall()
            print(f"Retrieved {len(items)} items")
            return items
    except Exception as e:
        print(f"Error retrieving items: {str(e)}")
        traceback.print_exc()
        return []

def insert_invoice_with_line_items(
    invoice_no, company_name, gst_number, street, city, state, zipcode, country,
    terms, shipping_method, subtotal, discount, tax, total,
    invoice_date, due_date, po_number, line_items,
    key_name, supplier_name
):
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            try:
                # Map key_name to key_code
                cursor.execute("SELECT key_code FROM suppliers WHERE key_name = ?", (key_name,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Supplier with key_name '{key_name}' not found")
                key_code = result[0]

                # Update supplier's terms and shipping_method
                cursor.execute('''
                    UPDATE suppliers
                    SET terms = ?, shipping_method = ?
                    WHERE key_code = ?
                ''', (terms, shipping_method, key_code))

                # Ensure po_number has a default value if not provided
                po_number = po_number if po_number else "UNKNOWN"

                # Insert into invoices table
                cursor.execute('''
                    INSERT INTO invoices (
                        invoice_no, key_code, invoice_date, due_date,
                        po_number, subtotal, discount, tax, total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_no, key_code, invoice_date, due_date,
                    po_number, subtotal, discount, tax, total
                ))
                print(f"Inserted invoice {invoice_no} into database")

                # Insert line items
                for index, item in enumerate(line_items, start=1):
                    item_no = item.get('item_no', f"ITEM{index}")
                    description = item.get('description', '')
                    unit = item.get('unit', 'Piece')
                    default_unit_price = Decimal(str(item.get('unit_price', 0.0)))

                    # Find or insert item in items table
                    cursor.execute('SELECT item_code FROM items WHERE item_no = ?', (item_no,))
                    existing_item = cursor.fetchone()
                    if existing_item:
                        item_code = existing_item[0]
                        cursor.execute('''
                            UPDATE items
                            SET description = ?, unit = ?, default_unit_price = ?
                            WHERE item_code = ?
                        ''', (description, unit, default_unit_price, item_code))
                    else:
                        cursor.execute('''
                            INSERT INTO items (item_no, description, unit, default_unit_price)
                            OUTPUT INSERTED.item_code
                            VALUES (?, ?, ?, ?)
                        ''', (item_no, description, unit, default_unit_price))
                        item_code = cursor.fetchone()[0]

                    cursor.execute('''
                        INSERT INTO invoice_line_items (
                            key_code, invoice_no, item_code, quantity,
                            unit_price, total_price, line_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        key_code,
                        invoice_no,
                        item_code,
                        item.get('quantity', 0),
                        Decimal(str(item.get('unit_price', 0.0))),
                        Decimal(str(item.get('total_price', 0.0))),
                        index
                    ))
                    print(f"Inserted line item {item_no} (item_code: {item_code}) for invoice {invoice_no}")

                conn.commit()
                print(f"Successfully saved invoice {invoice_no} with {len(line_items)} line items")
            except Exception as e:
                conn.rollback()
                print(f"Error saving invoice {invoice_no}: {str(e)}")
                traceback.print_exc()
                raise
            finally:
                conn.autocommit = True
    except Exception as e:
        print(f"Error saving invoice {invoice_no}: {str(e)}")
        traceback.print_exc()
        raise

def check_invoice_exists(invoice_no):
    """Check if an invoice already exists"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE UPPER(invoice_no) = UPPER(?)", (invoice_no,))
            count = cursor.fetchone()[0]
            exists = count > 0
            print(f"Checked existence of invoice {invoice_no}: {exists} (COUNT: {count})")
            if exists:
                cursor.execute("SELECT i.invoice_no, s.supplier_name FROM invoices i JOIN suppliers s ON i.key_code = s.key_code WHERE UPPER(i.invoice_no) = UPPER(?)", (invoice_no,))
                invoice = cursor.fetchone()
                print(f"Found invoice: {invoice}")
            return exists
    except Exception as e:
        print(f"Error checking invoice existence for {invoice_no}: {str(e)}")
        return False

def get_invoice_by_number(invoice_no):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    inv.invoice_no,
                    inv.key_code,
                    inv.invoice_date,
                    inv.due_date,
                    inv.po_number,
                    inv.subtotal,
                    inv.discount,
                    inv.tax,
                    inv.total,
                    sup.supplier_name,
                    sup.gst_number,
                    sup.street,
                    sup.city,
                    sup.state,
                    sup.zipcode,
                    sup.country,
                    sup.terms,
                    sup.shipping_method
                FROM invoices inv
                JOIN suppliers sup ON inv.key_code = sup.key_code
                WHERE inv.invoice_no = ?
            ''', (invoice_no,))
            invoice_data = cursor.fetchone()

            cursor.execute('''
                SELECT 
                    li.key_code,
                    li.invoice_no,
                    li.item_code,
                    it.item_no,
                    it.description,
                    it.unit,
                    li.quantity,
                    li.unit_price,
                    li.total_price,
                    li.line_number
                FROM invoice_line_items li
                JOIN items it ON li.item_code = it.item_code
                WHERE li.invoice_no = ?
                ORDER BY li.line_number ASC
            ''', (invoice_no,))
            line_items = cursor.fetchall()

            return invoice_data, line_items
    except Exception as e:
        print(f"Error retrieving invoice {invoice_no}: {str(e)}")
        traceback.print_exc()
        return None, []

def get_all_invoices():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.invoice_no, s.supplier_name, i.total,
                       COUNT(li.line_number) as line_item_count,
                       i.invoice_date, i.due_date
                FROM invoices i
                JOIN suppliers s ON i.key_code = s.key_code
                LEFT JOIN invoice_line_items li ON li.invoice_no = i.invoice_no
                GROUP BY i.invoice_no, s.supplier_name, i.total, i.invoice_date, i.due_date
                ORDER BY i.invoice_no DESC
            """)
            invoices = cursor.fetchall()
            # Log the types of invoice_date and due_date
            for invoice in invoices:
                print(f"Invoice {invoice[0]}: invoice_date={invoice[4]}, type={type(invoice[4])}, due_date={invoice[5]}, type={type(invoice[5])}")
            return invoices
    except Exception as e:
        print(f"Error retrieving all invoices: {str(e)}")
        traceback.print_exc()
        return []

def delete_invoice(invoice_no):
    """Delete an invoice and all its line items"""
    try:
        with get_db_connection() as conn:
            conn.autocommit = False
            cursor = conn.cursor()
            try:
                # Delete line items
                cursor.execute("SELECT COUNT(*) FROM invoice_line_items WHERE invoice_no = ?", (invoice_no,))
                line_item_count = cursor.fetchone()[0]
                cursor.execute("DELETE FROM invoice_line_items WHERE invoice_no = ?", (invoice_no,))

                # Delete invoice
                cursor.execute("DELETE FROM invoices WHERE invoice_no = ?", (invoice_no,))

                conn.commit()
                print(f"Deleted invoice {invoice_no} with {line_item_count} line items")
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error deleting invoice: {str(e)}")
                return False
            finally:
                conn.autocommit = True
    except Exception as e:
        print(f"Error deleting invoice: {str(e)}")
        return False

def debug_database_state():
    """Print current state of the database for debugging"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM invoices")
            invoice_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
            line_item_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM suppliers")
            supplier_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM items")
            item_count = cursor.fetchone()[0]
            print(f"\n=== DATABASE STATE ===")
            print(f"Total invoices: {invoice_count}")
            print(f"Total line items: {line_item_count}")
            print(f"Total suppliers: {supplier_count}")
            print(f"Total items: {item_count}")
            
            cursor.execute("""
                SELECT invoice_no, COUNT(*) as item_count
                FROM invoice_line_items
                GROUP BY invoice_no
                ORDER BY invoice_no
            """)
            line_items_per_invoice = cursor.fetchall()
            print("Line items per invoice:")
            for row in line_items_per_invoice:
                print(f"  {row.invoice_no}: {row.item_count} items")
            
            cursor.execute("SELECT invoice_no, key_code, invoice_date, due_date FROM invoices ORDER BY invoice_date")
            all_invoices = cursor.fetchall()
            print("All invoices in invoices table:")
            for inv in all_invoices:
                print(f"  {inv.invoice_no}: key_code {inv.key_code}, invoice_date {inv.invoice_date}, due_date {inv.due_date}")
            
            cursor.execute("SELECT key_code, key_name, supplier_name, supplier_email, supplier_country FROM suppliers ORDER BY supplier_name")
            all_suppliers = cursor.fetchall()
            print("All suppliers:")
            for sup in all_suppliers:
                print(f"  {sup.key_code}: {sup.key_name} - {sup.supplier_name} ({sup.supplier_email}, {sup.supplier_country})")
            
            cursor.execute("SELECT item_code, item_no, description, unit, default_unit_price, category FROM items ORDER BY item_no")
            all_items = cursor.fetchall()
            print("All items:")
            for item in all_items:
                print(f"  {item.item_code}: {item.item_no} - {item.description} ({item.unit}, {item.default_unit_price}, {item.category})")
    except Exception as e:
        print(f"Error checking database state: {str(e)}")

def test_connection():
    """Test database connection"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("Database connection test: SUCCESS")
            return True
    except Exception as e:
        print(f"Connection test failed: {str(e)}")
        return False
    
def check_for_hanging_transactions():
    """Check for and kill any hanging or blocking transactions"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    t1.request_session_id AS blocking_session_id,
                    t2.request_session_id AS blocked_session_id,
                    t1.request_status AS blocking_status,
                    t2.request_status AS blocked_status,
                    object_name(t1.resource_associated_entity_id) as blocking_object,
                    object_name(t2.resource_associated_entity_id) as blocked_object,
                    t1.request_mode as blocking_mode,
                    t2.request_mode as blocked_mode,
                    SUBSTRING(st1.text, (t1.request_start_offset/2)+1, 
                        ((CASE t1.request_end_offset WHEN -1 THEN DATALENGTH(st1.text) 
                            ELSE t1.request_end_offset END - t1.request_start_offset)/2) + 1) AS blocking_statement,
                    SUBSTRING(st2.text, (t2.request_start_offset/2)+1, 
                        ((CASE t2.request_end_offset WHEN -1 THEN DATALENGTH(st1.text) 
                            ELSE t2.request_end_offset END - t2.request_start_offset)/2) + 1) AS blocked_statement
                FROM sys.dm_tran_locks t1
                JOIN sys.dm_tran_locks t2 ON t1.resource_associated_entity_id = t2.resource_associated_entity_id
                JOIN sys.dm_exec_connections c1 ON t1.request_session_id = c1.session_id
                JOIN sys.dm_exec_connections c2 ON t2.request_session_id = c2.session_id
                CROSS APPLY sys.dm_exec_sql_text(c1.most_recent_sql_handle) st1
                CROSS APPLY sys.dm_exec_sql_text(c2.most_recent_sql_handle) st2
                WHERE t1.request_session_id <> t2.request_session_id
                AND t1.request_mode IN ('S', 'X', 'U', 'IX', 'IS')
                AND t2.request_mode IN ('S', 'X', 'U', 'IX', 'IS')
                AND t2.request_status = 'WAIT'
            ''')
            
            blocking_transactions = cursor.fetchall()
            if blocking_transactions:
                print(f"Found {len(blocking_transactions)} blocking transactions")
                for tx in blocking_transactions:
                    print(f"Blocking session {tx.blocking_session_id} blocking session {tx.blocked_session_id}")
                    print(f"Blocking object: {tx.blocking_object}, Blocked object: {tx.blocked_object}")
                    print(f"Blocking statement: {tx.blocking_statement}")
                    print(f"Blocked statement: {tx.blocked_statement}")
                    try:
                        cursor.execute(f"KILL {tx.blocking_session_id}")
                        print(f"Killed blocking session {tx.blocking_session_id}")
                    except Exception as e:
                        print(f"Could not kill session {tx.blocking_session_id}: {str(e)}")
            else:
                print("No blocking transactions found")
    except Exception as e:
        print(f"Error checking for blocking transactions: {str(e)}")
        traceback.print_exc()

def fix_orphaned_line_items():
    """Find and fix orphaned line items (not associated with valid invoices)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT li.invoice_no, COUNT(*) as orphaned_count
                FROM invoice_line_items li
                LEFT JOIN invoices i ON li.invoice_no = i.invoice_no
                WHERE i.invoice_no IS NULL
                GROUP BY li.invoice_no
            ''')
            
            orphaned_items = cursor.fetchall()
            if orphaned_items:
                print(f"Found {len(orphaned_items)} invoices with orphaned line items")
                for item in orphaned_items:
                    print(f"Invoice {item.invoice_no} has {item.orphaned_count} orphaned items")
                    cursor.execute("DELETE FROM invoice_line_items WHERE invoice_no = ?", (item.invoice_no,))
                    deleted_count = cursor.rowcount
                    print(f"Deleted {deleted_count} orphaned items for invoice {item.invoice_no}")
                    conn.commit()
            else:
                print("No orphaned line items found")
    except Exception as e:
        print(f"Error fixing orphaned line items: {str(e)}")
        traceback.print_exc()

# Initialize database
if __name__ == '__main__':
    create_tables()
    create_indexes()
    optimize_connection_settings()