import logging
import os
from flask import Flask, render_template, jsonify, request
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
from forecast import generate_forecast, cross_validate_model
from flask_cors import CORS


# Initialize Flask app
app = Flask(__name__, static_url_path='/dashboard/static')
CORS(app)


# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# SQL Server connection configuration using environment variables
db_config = {
    'server': os.getenv('DB_SERVER', 'AQEEF\SQLEXPRESS'),
    'database': os.getenv('DB_NAME', 'sales_forecasting2'),
    'user': os.getenv('DB_USER', 'sa'),
    'password': os.getenv('DB_PASSWORD', 'Aqeef123'),
    'driver': '{ODBC Driver 17 for SQL Server}'
}

def get_connection_string():
    return (
        f"DRIVER={db_config['driver']};"
        f"SERVER={db_config['server']};"
        f"DATABASE={db_config['database']};"
        f"UID={db_config['user']};"
        f"PWD={db_config['password']}"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/pending-orders')
def pending_orders():
    try:
        today = datetime.now()
        start_date = today - timedelta(days=7)
        end_date = today
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()
        query = """
            SELECT so.order_id, c.customer_name, sp.salesperson_name, so.order_date, so.total_amount
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.customer_id
            JOIN salespersons sp ON so.salesperson_id = sp.salesperson_id
            WHERE so.order_date >= ? AND so.order_date <= ?
            ORDER BY so.order_date DESC
        """
        cursor.execute(query, (start_date_str, end_date_str))
        results = cursor.fetchall()

        orders = [
            {
                'order_id': row.order_id,
                'customer_name': row.customer_name,
                'salesperson_name': row.salesperson_name,
                'order_date': row.order_date.strftime('%d-%m-%y'),
                'total_amount': f"${row.total_amount:,.2f}"
            } for row in results
        ]
        cursor.close()
        conn.close()
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Error in pending_orders: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-performers')
def top_performers():
    try:
        logger.debug("Starting /api/top-performers")
        filter_value = request.args.get('filter', 'this-month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        logger.debug(f"Parameters: filter={filter_value}, start_date={start_date}, end_date={end_date}")

        if start_date and end_date:
            start_date_str = start_date
            end_date_str = end_date
        else:
            today = datetime.now()
            if filter_value == 'today':
                start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = today
            elif filter_value == 'yesterday':
                start_date = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = (today - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            elif filter_value == 'this-week':
                start_date = today - timedelta(days=today.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = today
            else:  # this-month
                start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = today
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()
        query = """
            SELECT sp.salesperson_name, SUM(so.total_amount) AS total_sales
            FROM sales_orders so
            JOIN salespersons sp ON so.salesperson_id = sp.salesperson_id
            WHERE so.order_date >= ? AND so.order_date <= ?
            GROUP BY sp.salesperson_name
            ORDER BY total_sales DESC
        """
        logger.debug(f"Executing query: {query} with params: {start_date_str}, {end_date_str}")
        cursor.execute(query, (start_date_str, end_date_str))
        results = cursor.fetchall()

        if not results and filter_value == 'today':
            logger.info("No data for 'today', falling back to 2024-01-01 to 2025-06-03")
            start_date_str = '2024-01-01 00:00:00'
            cursor.execute(query, (start_date_str, end_date_str))
            results = cursor.fetchall()

        if not results:
            logger.warning("No data returned from query")
            performers = []
        else:
            sales_data = pd.DataFrame(
                [(row.salesperson_name, float(row.total_sales)) for row in results],
                columns=['salesperson_name', 'total_sales']
            )
            max_sales = sales_data['total_sales'].max() if not sales_data.empty else 1
            performers = [
                {
                    'name': row.salesperson_name,
                    'sales': row.total_sales,
                    'progress': (row.total_sales / max_sales) * 100,
                    'image': 'https://via.placeholder.com/48'
                } for _, row in sales_data.iterrows()
            ]

        cursor.close()
        conn.close()
        return jsonify(performers[:5])

    except Exception as e:
        logger.error(f"Error in top_performers: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-activity')
def recent_activity():
    try:
        filter_value = request.args.get('filter', 'today')
        today = datetime.now()
        if filter_value == 'today':
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today
        elif filter_value == 'yesterday':
            start_date = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (today - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif filter_value == 'this-week':
            start_date = today - timedelta(days=today.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today
        else:  # this-month
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = today
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()
        query = """
            SELECT so.order_id, c.customer_name, so.order_date, so.total_amount
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.customer_id
            WHERE so.order_date >= ? AND so.order_date <= ?
            ORDER BY so.order_date DESC
        """
        cursor.execute(query, (start_date_str, end_date_str))
        results = cursor.fetchall()
        activities = [
            {
                'order_id': row.order_id,
                'description': f"Order {row.order_id} by {row.customer_name}",
                'details': f"${row.total_amount:,.2f} on {row.order_date.strftime('%d-%m-%y')}",
                'type': 'order'
            } for row in results
        ]
        cursor.close()
        conn.close()
        return jsonify({'activities': activities[:5]})
    except Exception as e:
        logger.error(f"Error in recent_activity: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-orders-unique-customers')
def sales_orders_unique_customers():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            """
            SELECT COUNT(DISTINCT customer_id) AS new_customers
            FROM (
                SELECT customer_id, MIN(order_date) AS first_order
                FROM sales_orders
                GROUP BY customer_id
            ) first_orders
            """
        ]

        params = []
        where_clauses = []
        if start_date:
            where_clauses.append("first_order >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("first_order <= ?")
            params.append(end_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query = " ".join(query_parts)
        cursor.execute(query, params)
        result = cursor.fetchone()

        new_customers = int(result.new_customers) if result.new_customers else 0

        cursor.close()
        conn.close()

        return jsonify({'new_customers': new_customers})

    except Exception as e:
        logger.error(f"Error in sales_orders_unique_customers: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary-metrics')
def summary_metrics():
    try:
        logger.debug("Starting /api/summary-metrics")
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        logger.debug(f"Parameters: start_date={start_date}, end_date={end_date}")

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            """
            SELECT 
                SUM(total_amount) AS total_sales,
                AVG(total_amount) AS avg_order_value,
                COUNT(*) AS num_orders
            FROM sales_orders
            """
        ]
        params = []
        where_clauses = []
        if start_date:
            where_clauses.append("order_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("order_date <= ?")
            params.append(end_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query = " ".join(query_parts)
        logger.debug(f"Executing main query: {query} with params: {params}")
        cursor.execute(query, params)
        result = cursor.fetchone()

        total_sales = float(result.total_sales) if result.total_sales else 0.0
        avg_order_value = float(result.avg_order_value) if result.avg_order_value else 0.0
        num_orders = int(result.num_orders) if result.num_orders else 0

        query = """
            SELECT 
                DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0) AS month,
                SUM(total_amount) AS total_sales
            FROM sales_orders
            WHERE order_date IS NOT NULL
                AND total_amount IS NOT NULL
            GROUP BY DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0)
            ORDER BY month
        """
        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            actual_data = pd.DataFrame(columns=['ds', 'y'])
        else:
            actual_data = pd.DataFrame([(row.month, row.total_sales) for row in results], columns=['ds', 'y'])

        if not actual_data.empty:
            actual_data['ds'] = pd.to_datetime(actual_data['ds'])
            actual_data['y'] = actual_data['y'].astype(float)

        forecast_accuracy = 0.0
        if not actual_data.empty and len(actual_data) >= 12:
            cv_results = cross_validate_model(
                actual_data=actual_data,
                initial_periods=12,
                period_type='MS'
            )
            forecast_accuracy = float(cv_results['accuracy'].mean()) if not cv_results.empty else 0.0

        cursor.close()
        conn.close()

        response = {
            'total_sales': total_sales,
            'avg_order_value': avg_order_value,
            'num_orders': num_orders,
            'forecast_accuracy': forecast_accuracy
        }
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in summary_metrics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-trend')
def sales_trend():
    try:
        period_type = request.args.get('period_type', 'MS')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        forecast_start = request.args.get('forecast_start')
        selected_date = request.args.get('selected_date')

        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400
            start_date = start_date or selected_date
            end_date = end_date or (selected_date_dt + pd.offsets.MonthEnd(0)).strftime('%Y-%m-%d')

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query = """
            SELECT
                DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0) AS month,
                SUM(total_amount) AS total_sales
            FROM sales_orders
            WHERE order_date IS NOT NULL AND total_amount IS NOT NULL
            AND order_date >= ? AND order_date <= ?
            GROUP BY DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0)
            ORDER BY month
        """
        cursor.execute(query, [start_date, end_date])
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        if not results:
            return jsonify({
                'actual': {'periods': [], 'sales': []},
                'predicted': {'periods': [], 'sales': []},
                'forecast': {'periods': [], 'sales': []},
                'accuracy_metrics': {},
                'period_type': period_type
            }), 200

        df = pd.DataFrame([(row.month, row.total_sales) for row in results], columns=['ds', 'y'])
        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].astype(float)

        df = df[df['y'] > 100000]

        if df.empty:
            return jsonify({
                'actual': {'periods': [], 'sales': []},
                'predicted': {'periods': [], 'sales': []},
                'forecast': {'periods': [], 'sales': []},
                'accuracy_metrics': {},
                'period_type': period_type
            }), 200

        actual_df = pd.DataFrame([(row.month, row.total_sales) for row in results], columns=['ds', 'y'])
        actual_df['ds'] = pd.to_datetime(actual_df['ds'])
        actual_df['y'] = actual_df['y'].astype(float)

        predicted_data, forecast_data, accuracy_metrics = generate_forecast(
            df, forecast_start_date=forecast_start, period_type=period_type
        )

        return jsonify({
            'actual': {
                'periods': actual_df['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'sales': actual_df['y'].tolist()
            },
            'predicted': {
                'periods': predicted_data['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'sales': predicted_data['yhat'].tolist()
            },
            'forecast': {
                'periods': forecast_data['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'sales': forecast_data['yhat'].tolist()
            },
            'accuracy_metrics': accuracy_metrics,
            'period_type': period_type
        })

    except Exception as e:
        logger.error(f"Error in sales_trend: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast-accuracy')
def forecast_accuracy():
    try:
        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query = """
            SELECT 
                DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0) AS month,
                SUM(total_amount) AS total_sales
            FROM sales_orders
            GROUP BY DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0)
            ORDER BY month
        """
        cursor.execute(query)
        results = cursor.fetchall()

        actual_data = pd.DataFrame([(row.month, row.total_sales) for row in results], columns=['ds', 'y'])
        actual_data['ds'] = pd.to_datetime(actual_data['ds'])
        actual_data['y'] = actual_data['y'].astype(float)

        cursor.close()
        conn.close()

        cv_results = cross_validate_model(
            actual_data=actual_data,
            initial_periods=12,
            period_type='MS'
        )

        overall_accuracy = float(cv_results['accuracy'].mean()) if not cv_results.empty else 0

        _, _, accuracy_metrics = generate_forecast(
            actual_data=actual_data,
            forecast_start_date='2026-02-01'
        )

        return jsonify({
            'model_accuracy': accuracy_metrics,
            'cross_validation': {
                'overall_accuracy': overall_accuracy,
                'results': cv_results.to_dict(orient='records') if not cv_results.empty else []
            }
        })

    except Exception as e:
        logger.error(f"Error in forecast_accuracy: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/regions')
def get_regions():
    try:
        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT (country + ' - ' + state) AS region_label
            FROM regions
            ORDER BY region_label
        """
        cursor.execute(query)
        results = cursor.fetchall()

        regions = [row.region_label for row in results]

        cursor.close()
        conn.close()

        return jsonify({'regions': regions})

    except Exception as e:
        logger.error(f"Error in get_regions: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-by-region')
def sales_by_region():
    try:
        region_label = request.args.get('region_label')
        selected_date = request.args.get('selected_date')
        logger.debug(f"Parameters: region_label={region_label}, selected_date={selected_date}")

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            "SELECT (r.country + ' - ' + r.state) AS region_label, SUM(so.total_amount) AS total_sales",
            "FROM sales_orders so",
            "JOIN regions r ON so.region_id = r.region_id"
        ]

        params = []
        where_clauses = []
        if region_label:
            where_clauses.append("(r.country + ' - ' + r.state) = ?")
            params.append(region_label)
        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400
            where_clauses.append("so.order_date <= ?")
            params.append(selected_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("GROUP BY r.region_id, r.country, r.state")
        query_parts.append("ORDER BY total_sales DESC")

        query = " ".join(query_parts)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No data returned for sales by region")
            return jsonify({'regions': [], 'sales': []}), 200

        # Create DataFrame using dictionary comprehension
        region_data = pd.DataFrame(
            [{'region_label': row[0], 'total_sales': float(row[1])} for row in results]
        )

        cursor.close()
        conn.close()

        response = {
            'regions': region_data['region_label'].tolist(),
            'sales': region_data['total_sales'].tolist()
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_by_region: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-funnel')
def sales_funnel():
    try:
        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query = """
            SELECT 
                SUM(CASE WHEN status = 'Lead' THEN 1 ELSE 0 END) AS leads,
                SUM(CASE WHEN status = 'Opportunity' THEN 1 ELSE 0 END) AS quotes,
                SUM(CASE WHEN status = 'Order' THEN 1 ELSE 0 END) AS orders,
                SUM(CASE WHEN status = 'Invoice' THEN 1 ELSE 0 END) AS invoices
            FROM leads
        """
        cursor.execute(query)
        results = cursor.fetchone()

        cursor.close()
        conn.close()

        response = {
            'leads': int(results.leads) if results.leads else 0,
            'quotes': int(results.quotes) if results.quotes else 0,
            'orders': int(results.orders) if results.orders else 0,
            'invoices': int(results.invoices) if results.invoices else 0
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_funnel: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-by-customer')
def sales_by_customer():
    try:
        selected_date = request.args.get('selected_date')
        logger.debug(f"Parameters: selected_date={selected_date}")

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            "SELECT c.customer_name, SUM(so.total_amount) AS total_sales",
            "FROM sales_orders so",
            "JOIN customers c ON so.customer_id = c.customer_id"
        ]

        params = []
        where_clauses = []
        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400
            where_clauses.append("so.order_date <= ?")
            params.append(selected_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("GROUP BY c.customer_id, c.customer_name")
        query_parts.append("ORDER BY total_sales DESC")
        query = " ".join(query_parts)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No data returned for sales by customer")
            return jsonify({
                'customers': [],
                'revenues': [],
                'cumulative_percentages': []
            }), 200

        # Create DataFrame, handling None customer names
        customer_data = pd.DataFrame(
            [{'customer_name': row[0] or 'Unknown', 'total_sales': float(row[1])} for row in results]
        )

        if customer_data.empty:
            logger.warning("No data returned for sales by customer")
            return jsonify({
                'customers': [],
                'revenues': [],
                'cumulative_percentages': []
            }), 200

        total_revenue = customer_data['total_sales'].sum()
        customer_data['cumulative_sales'] = customer_data['total_sales'].cumsum()
        customer_data['cumulative_percentage'] = (customer_data['cumulative_sales'] / total_revenue * 100).round(2) if total_revenue > 0 else 0

        cursor.close()
        conn.close()

        response = {
            'customers': customer_data['customer_name'].tolist(),
            'revenues': customer_data['total_sales'].tolist(),
            'cumulative_percentages': customer_data['cumulative_percentage'].tolist()
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_by_customer: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-by-salesperson')
def sales_by_salesperson():
    try:
        logger.debug("Starting /api/sales-by-salesperson")
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        logger.debug(f"Parameters: start_date={start_date}, end_date={end_date}")

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            """
            SELECT s.salesperson_name, SUM(so.total_amount) AS total_sales
            FROM sales_orders so
            JOIN salespersons s ON so.salesperson_id = s.salesperson_id
            """
        ]
        params = []
        where_clauses = [
            "so.order_date IS NOT NULL",
            "so.total_amount IS NOT NULL"
        ]
        if start_date:
            where_clauses.append("so.order_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("so.order_date <= ?")
            params.append(end_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
        query_parts.append("GROUP BY s.salesperson_name")
        query_parts.append("ORDER BY total_sales DESC")

        query = " ".join(query_parts)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No data returned")
            return jsonify({'salespersons': [], 'sales': []}), 200

        salesperson_data = pd.DataFrame(
            [{'salesperson_name': row[0], 'total_sales': float(row[1])} for row in results]
        )

        cursor.close()
        conn.close()

        response = {
            'salespersons': salesperson_data['salesperson_name'].tolist(),
            'sales': salesperson_data['total_sales'].tolist()
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_by_salesperson: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-target-vs-achievement')
def sales_target_vs_achievement():
    try:
        selected_date = request.args.get('selected_date')
        logger.debug(f"Parameters: selected_date={selected_date}")

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_targets = """
            SELECT s.salesperson_name, st.target_period, st.target_amount, st.salesperson_id
            FROM sales_targets st
            JOIN salespersons s ON st.salesperson_id = s.salesperson_id
            ORDER BY st.target_period, s.salesperson_name
        """
        cursor.execute(query_targets)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No target data returned")
            return jsonify({
                'labels': [],
                'targets': [],
                'achieved': [],
                'percentages': []
            }), 200

        target_data = pd.DataFrame(
            [{
                'salesperson_name': row[0],
                'target_period': row[1],
                'target_amount': float(row[2]),
                'salesperson_id': row[3]
            } for row in results]
        )

        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400
            target_data = target_data[target_data['target_period'] <= selected_date]

        if target_data.empty:
            logger.warning("No target data returned")
            return jsonify({
                'labels': [],
                'targets': [],
                'achieved': [],
                'percentages': []
            }), 200

        labels = []
        targets = []
        achieved = []
        percentages = []

        for _, row in target_data.iterrows():
            salesperson_id = row.salesperson_id
            target_period = row.target_period
            target_amount = row.target_amount

            target_date = pd.to_datetime(target_period)
            start_date = target_date
            end_date = target_date + pd.offsets.MonthEnd(0)

            query_actual = """
                SELECT SUM(so.total_amount) AS actual_sales
                FROM sales_orders so
                WHERE so.salesperson_id = ?
                AND so.order_date BETWEEN ? AND ?
            """
            cursor.execute(query_actual, (salesperson_id, start_date, end_date))
            actual_result = cursor.fetchone()
            actual_sales = float(actual_result.actual_sales) if actual_result.actual_sales else 0.0

            achievement_percentage = (actual_sales / target_amount * 100) if target_amount > 0 else 0

            label = f"{row.salesperson_name} ({target_date.strftime('%Y-%m')})"

            labels.append(label)
            targets.append(target_amount)
            achieved.append(actual_sales)
            percentages.append(achievement_percentage)

        cursor.close()
        conn.close()

        response = {
            'labels': labels,
            'targets': targets,
            'achieved': achieved,
            'percentages': percentages
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_target_vs_achievement: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-by-category')
def sales_by_category():
    try:
        period_type = request.args.get('period_type', 'MS')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        selected_date = request.args.get('selected_date')
        logger.debug(f"Parameters: period_type={period_type}, start_date={start_date}, end_date={end_date}, selected_date={selected_date}")

        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400
            if period_type == 'MS':
                start_date = selected_date
                end_date = (selected_date_dt + pd.offsets.MonthEnd(0)).strftime('%Y-%m-%d')
            elif period_type == 'QS':
                quarter = (selected_date_dt.month - 1) // 3 + 1
                start_date = f"{selected_date_dt.year}-{(quarter-1)*3+1:02d}-01"
                end_date = (pd.to_datetime(start_date) + pd.offsets.QuarterEnd(0)).strftime('%Y-%m-%d')
            else:  # YS
                start_date = f"{selected_date_dt.year}-01-01"
                end_date = f"{selected_date_dt.year}-12-31"

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            "SELECT p.category, SUM(so.total_amount) AS total_sales",
            "FROM sales_orders so",
            "JOIN products p ON so.product_id = p.product_id"
        ]

        params = []
        where_clauses = []
        if start_date:
            where_clauses.append("so.order_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("so.order_date <= ?")
            params.append(end_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("GROUP BY p.category")
        query_parts.append("ORDER BY total_sales DESC")
        query = " ".join(query_parts)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No data returned for sales by category")
            return jsonify({'categories': [], 'sales': []}), 200

        category_data = pd.DataFrame(
            [{'category': row[0], 'total_sales': float(row[1])} for row in results]
        )

        if category_data.empty:
            logger.warning("No data returned for sales by category")
            return jsonify({'categories': [], 'sales': []}), 200

        total_sales = category_data['total_sales'].sum()
        category_data['sales_percentage'] = (category_data['total_sales'] / total_sales * 100).round(2)

        cursor.close()
        conn.close()

        response = {
            'categories': category_data['category'].tolist(),
            'sales': category_data['sales_percentage'].tolist()
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_by_category: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-growth-rate')
def sales_growth_rate():
    try:
        period_type = request.args.get('period_type', 'MS')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        logger.debug(f"Parameters: period_type={period_type}, start_date={start_date}, end_date={end_date}")

        if start_date and end_date:
            start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if end_date_dt > datetime.now():
                return jsonify({'error': 'end_date cannot be in the future'}), 400

        period_mapping = {
            'D': {'sql_group_by': 'CAST(order_date AS DATE)'},
            'MS': {'sql_group_by': 'DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0)'},
            'QS': {'sql_group_by': 'DATEADD(QUARTER, DATEDIFF(QUARTER, 0, order_date), 0)'},
            'YS': {'sql_group_by': 'DATEADD(YEAR, DATEDIFF(YEAR, 0, order_date), 0)'}
        }

        period_format = period_mapping.get(period_type, period_mapping['MS'])

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        query_parts = [
            f"SELECT {period_format['sql_group_by']} AS period, SUM(total_amount) AS total_sales",
            "FROM sales_orders"
        ]

        params = []
        where_clauses = []
        if start_date:
            where_clauses.append("order_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("order_date <= ?")
            params.append(end_date)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append(f"GROUP BY {period_format['sql_group_by']}")
        query_parts.append("ORDER BY period")

        query = " ".join(query_parts)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()

        sales_data = pd.DataFrame(
            [{'period': row[0], 'total_sales': float(row[1])} for row in results]
        )
        sales_data['period'] = pd.to_datetime(sales_data['period'])
        sales_data['total_sales'] = sales_data['total_sales'].astype(float)

        if sales_data.empty:
            logger.warning("No data returned for sales growth rate")
            return jsonify({
                'periods': [],
                'growth_rates': [],
                'period_type': period_type
            }), 200

        sales_data['previous_sales'] = sales_data['total_sales'].shift(1)
        sales_data['growth_rate'] = ((sales_data['total_sales'] - sales_data['previous_sales']) /
                                     sales_data['previous_sales'].replace(0, 0.0001) * 100).round(2)
        sales_data = sales_data.dropna(subset=['growth_rate'])

        cursor.close()
        conn.close()

        response = {
            'periods': sales_data['period'].dt.strftime('%Y-%m-%d').tolist(),
            'growth_rates': sales_data['growth_rate'].tolist(),
            'period_type': period_type
        }
        logger.debug(f"Response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in sales_growth_rate: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/repeat-vs-new-sales')
def repeat_vs_new_sales():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period_type = request.args.get('period_type', 'MS')
        selected_date = request.args.get('selected_date')
        logger.debug(f"Parameters: start_date={start_date}, end_date={end_date}, period_type={period_type}, selected_date={selected_date}")

        if period_type not in ['MS', 'QS', 'YS']:
            return jsonify({'error': 'Invalid period_type. Must be MS, QS, or YS.'}), 400

        if selected_date:
            selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            if selected_date_dt > datetime.now():
                return jsonify({'error': 'selected_date cannot be in the future'}), 400

        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()

        if period_type == 'MS':
            date_trunc = "DATEADD(MONTH, DATEDIFF(MONTH, 0, so.order_date), 0)"
        elif period_type == 'QS':
            date_trunc = "DATEADD(QUARTER, DATEDIFF(QUARTER, 0, so.order_date), 0)"
        else:  # YS
            date_trunc = "DATEADD(YEAR, DATEDIFF(YEAR, 0, so.order_date), 0)"

        query_order_count = f"""
            SELECT 
                {date_trunc} AS period,
                so.customer_id, 
                COUNT(*) AS order_count
            FROM sales_orders so
        """
        query_parts_count = [query_order_count]
        params = []
        where_clauses = []
        if start_date:
            where_clauses.append("so.order_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("so.order_date <= ?")
            params.append(end_date)
        if selected_date:
            if period_type == 'MS':
                where_clauses.append(f"{date_trunc} = ?")
                params.append(selected_date)
            elif period_type == 'QS':
                selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
                year = selected_date_dt.year
                quarter = (selected_date_dt.month - 1) // 3 + 1
                start_date = f"{year}-{(quarter-1)*3+1:02d}-01"
                where_clauses.append(f"{date_trunc} = ?")
                params.append(start_date)
            else:  # YS
                year = datetime.strptime(selected_date, '%Y-%m-%d').year
                where_clauses.append(f"YEAR(so.order_date) = ?")
                params.append(year)

        if where_clauses:
            query_parts_count.append("WHERE " + " AND ".join(where_clauses))

        query_parts_count.append("GROUP BY " + date_trunc + ", so.customer_id")
        query_count = " ".join(query_parts_count)
        logger.debug(f"Executing order count query: {query_count} with params: {params}")
        cursor.execute(query_count, params)
        results = cursor.fetchall()
        logger.debug(f"Raw query results: {results}")

        if not results:
            logger.warning("No data returned for order counts")
            return jsonify({
                'period_type': period_type,
                'periods': [],
                'repeat_sales': [],
                'new_sales': []
            }), 200

        order_counts = pd.DataFrame(
            [{'period': row[0], 'customer_id': row[1], 'order_count': row[2]} for row in results]
        )

        query_first_order = """
            SELECT 
                customer_id,
                MIN(order_date) AS first_order_date
            FROM sales_orders
            GROUP BY customer_id
        """
        cursor.execute(query_first_order)
        first_orders_results = cursor.fetchall()
        first_orders = pd.DataFrame(
            [{'customer_id': row[0], 'first_order_date': row[1]} for row in first_orders_results]
        )

        if period_type == 'MS':
            first_orders['first_order_period'] = first_orders['first_order_date'].apply(
                lambda x: x.strftime('%Y-%m-01') if pd.notnull(x) else None
            )
        elif period_type == 'QS':
            first_orders['first_order_period'] = first_orders['first_order_date'].apply(
                lambda x: f"{x.year}-{(x.month-1)//3*3+1:02d}-01" if pd.notnull(x) else None
            )
        else:  # YS
            first_orders['first_order_period'] = first_orders['first_order_date'].apply(
                lambda x: str(x.year) if pd.notnull(x) else None
            )

        order_counts = pd.merge(order_counts, first_orders[['customer_id', 'first_order_period']], on='customer_id')
        order_counts['customer_type'] = order_counts.apply(
            lambda row: 'new' if pd.to_datetime(row['period']).strftime('%Y-%m-%d') == row['first_order_period'] else 'repeat',
            axis=1
        )

        query_sales = f"""
            SELECT 
                {date_trunc} AS period,
                so.customer_id, 
                SUM(so.total_amount) AS total_amount
            FROM sales_orders so
        """
        query_parts_sales = [query_sales]
        if where_clauses:
            query_parts_sales.append("WHERE " + " AND ".join(where_clauses))

        query_parts_sales.append("GROUP BY " + date_trunc + ", so.customer_id")
        query_sales_final = " ".join(query_parts_sales)
        cursor.execute(query_sales_final, params)
        sales_results = cursor.fetchall()

        sales_data = pd.DataFrame(
            [{'period': row[0], 'customer_id': row[1], 'total_amount': float(row[2])} for row in sales_results]
        )

        if order_counts.empty or sales_data.empty:
            logger.warning("No data returned for repeat vs new sales")
            return jsonify({
                'period_type': period_type,
                'periods': [],
                'repeat_sales': [],
                'new_sales': []
            }), 200

        merged_data = pd.merge(sales_data, order_counts[['period', 'customer_id', 'customer_type']],
                              on=['period', 'customer_id'])
        merged_data['total_amount'] = merged_data['total_amount'].astype(float)

        sales_by_type = merged_data.groupby(['period', 'customer_type'])['total_amount'].sum().reset_index()
        sales_pivot = sales_by_type.pivot(index='period', columns='customer_type', values='total_amount').fillna(0)

        if 'new' not in sales_pivot.columns:
            sales_pivot['new'] = 0.0
        if 'repeat' not in sales_pivot.columns:
            sales_pivot['repeat'] = 0.0

        sales_pivot = sales_pivot.sort_index()
        sales_pivot.index = sales_pivot.index.astype(str)

        response = {
            'period_type': period_type,
            'periods': sales_pivot.index.tolist(),
            'repeat_sales': sales_pivot['repeat'].tolist(),
            'new_sales': sales_pivot['new'].tolist()
        }
        logger.debug(f"Response: {response}")

        cursor.close()
        conn.close()

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in repeat_vs_new_sales: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)