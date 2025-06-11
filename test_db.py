import pyodbc

# SQL Server connection configuration
db_config = {
    'server': 'AQEEF\SQLEXPRESS',  # Replace with your SQL Server instance name, e.g., 'AQEEF\SQLEXPRESS\SQLEXPRESS'
    'database': 'sales_forecasting2',
    'user': 'sa',  # Replace with your SQL Server username
    'password': 'Aqeef123',  # Replace with your SQL Server password
    'driver': '{ODBC Driver 17 for SQL Server}'  # Adjust based on your installed ODBC driver
}

try:
    # Create connection string
    conn_str = (
        f"DRIVER={db_config['driver']};"
        f"SERVER={db_config['server']};"
        f"DATABASE={db_config['database']};"
        f"UID={db_config['user']};"
        f"PWD={db_config['password']}"
    )
    
    # Connect to SQL Server
    conn = pyodbc.connect(conn_str)
    print("Connection successful!")
    conn.close()
except Exception as err:
    print(f"Connection failed: {err}")