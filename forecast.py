import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import Parallel, delayed
import multiprocessing
import pyodbc
from datetime import datetime

# SQL Server connection configuration
db_config = {
    'server': 'AQEEF\SQLEXPRESS',  # Replace with your SQL Server instance, e.g., 'AQEEF\SQLEXPRESS\SQLEXPRESS'
    'database': 'sales_forecasting2',
    'user': 'sa',  # Replace with your SQL Server username
    'password': 'Aqeef123',  # Replace with your SQL Server password
    'driver': '{ODBC Driver 17 for SQL Server}'  # Adjust based on your installed ODBC driver
}

def load_sales_data(period_type='MS'):
    try:
        conn_str = (
            f"DRIVER={db_config['driver']};"
            f"SERVER={db_config['server']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['user']};"
            f"PWD={db_config['password']}"
        )
        conn = pyodbc.connect(conn_str)
        
        if period_type == 'MS':
            date_trunc = "DATEADD(MONTH, DATEDIFF(MONTH, 0, order_date), 0)"
        elif period_type == 'QS':
            date_trunc = "DATEADD(QUARTER, DATEDIFF(QUARTER, 0, order_date), 0)"
        elif period_type == 'YS':
            date_trunc = "DATEADD(YEAR, DATEDIFF(YEAR, 0, order_date), 0)"
        else:
            date_trunc = "CAST(order_date AS DATE)"
        
        query = f"""
            SELECT 
                {date_trunc} AS ds,
                SUM(total_amount) AS y
            FROM sales_orders
            WHERE order_date IS NOT NULL
                AND total_amount IS NOT NULL
            GROUP BY {date_trunc}
            ORDER BY ds
        """
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        print("Query results:", results)  # Debug: Print raw results
        print("Number of columns:", len(results[0]) if results else 0)
        cursor.close()
        
        df = pd.read_sql(query, conn)
        print("DataFrame shape:", df.shape)  # Debug: Print shape
        print("DataFrame columns:", df.columns)
        
        df['ds'] = pd.to_datetime(df['ds'])
        
        conn.close()
        
        if df.empty:
            raise ValueError("No sales data retrieved from the database")
        
        return df
    
    except Exception as e:
        raise Exception(f"Error loading sales data: {str(e)}")

def calculate_accuracy_metrics(actual_values, predicted_values):
    """
    Calculate accuracy metrics for the forecast model.
    
    Args:
        actual_values (array-like): The actual values
        predicted_values (array-like): The predicted values
    
    Returns:
        dict: Dictionary containing various accuracy metrics
    """
    # Remove any NaN values
    mask = ~np.isnan(actual_values) & ~np.isnan(predicted_values)
    actual = np.array(actual_values)[mask]
    predicted = np.array(predicted_values)[mask]
    
    # If we don't have enough data, return None
    if len(actual) < 2:
        return None
    
    # Calculate metrics
    mae = mean_absolute_error(actual, predicted)
    mse = mean_squared_error(actual, predicted)
    rmse = np.sqrt(mse)
    
    # Calculate MAPE (Mean Absolute Percentage Error)
    actual_safe = np.where(actual == 0, 0.0001, actual)
    mape = np.mean(np.abs((actual - predicted) / actual_safe)) * 100
    
    # Calculate R² score
    r2 = r2_score(actual, predicted)
    
    # Calculate mean forecast accuracy percentage
    accuracy = 100 - mape
    accuracy = max(0, min(accuracy, 100))  # Clip between 0 and 100
    
    return {
        'MAE': float(mae),
        'MSE': float(mse),
        'RMSE': float(rmse),
        'MAPE': float(mape),
        'R2': float(r2),
        'AccuracyPercentage': float(accuracy)
    }

def generate_forecast(actual_data, forecast_start_date=None, period_type='MS'):
    try:
        if not {'ds', 'y'}.issubset(actual_data.columns):
            raise ValueError("actual_data must contain 'ds' and 'y' columns")
        if actual_data['ds'].isnull().any() or actual_data['y'].isnull().any():
            raise ValueError("actual_data contains null values in 'ds' or 'y'")

        actual_data['ds'] = pd.to_datetime(actual_data['ds'])
        actual_data['y'] = actual_data['y'].astype(float)

        # Cap training data and exclude outliers
        if len(actual_data) > 24:
            actual_data = actual_data.tail(24)
        actual_data = actual_data[actual_data['y'] > 100000]  # Adjust threshold

        if actual_data.empty:
            raise ValueError("No valid data after filtering outliers")

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=(period_type == 'D'),
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            n_changepoints=10,
            interval_width=0.95,
            stan_backend='CMDSTANPY'
        )
        model.fit(actual_data)

        if forecast_start_date:
            start_date = pd.to_datetime(forecast_start_date)
        else:
            if period_type == 'MS':
                start_date = actual_data['ds'].max() + pd.DateOffset(months=1)
            elif period_type == 'QS':
                start_date = actual_data['ds'].max() + pd.DateOffset(months=3)
            elif period_type == 'YS':
                start_date = actual_data['ds'].max() + pd.DateOffset(years=1)
            else:
                start_date = actual_data['ds'].max() + pd.DateOffset(days=1)

        future_dates = pd.DataFrame({
            'ds': pd.date_range(start=start_date, periods=6, freq=period_type)
        })
        all_dates = pd.DataFrame({
            'ds': pd.concat([actual_data['ds'], future_dates['ds']], ignore_index=True).sort_values().unique()
        })

        forecast = model.predict(all_dates)
        predicted_data = forecast[forecast['ds'].isin(actual_data['ds'])][['ds', 'yhat']].copy()
        forecast_data = forecast[forecast['ds'] >= start_date][['ds', 'yhat']].copy()
        forecast_data = forecast_data[forecast_data['yhat'] > 0]

        accuracy_metrics = calculate_accuracy_metrics(
            actual_data['y'].values,
            predicted_data['yhat'].values
        )

        return predicted_data, forecast_data, accuracy_metrics

    except Exception as e:
        logging.error(f"Forecasting error: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to generate forecast: {str(e)}")
    
def _cross_validate_fold(i, actual_data, period_type):
    """
    Helper function for cross-validation in parallel.
    
    Args:
        i (int): Index for the fold
        actual_data (pd.DataFrame): DataFrame with 'ds' (date) and 'y' (sales) columns
        period_type (str): Frequency of the forecast periods
    
    Returns:
        dict: Cross-validation metrics for the fold
    """
    try:
        # Cap the training data size to the most recent 24 periods
        train_data = actual_data.iloc[:i]
        if len(train_data) > 24:
            train_data = train_data.tail(24)
        
        test_data = actual_data.iloc[i:i+6]
        
        if len(test_data) < 1:
            return None
        
        # Train model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=(period_type == 'D'),
            daily_seasonality=False,
            changepoint_prior_scale=0.01,
            n_changepoints=5,
            mcmc_samples=0,
            interval_width=0.95,
            stan_backend='CMDSTANPY'
        )
        model.fit(train_data)
        
        # Make predictions
        future = pd.DataFrame({'ds': test_data['ds']})
        forecast = model.predict(future)
        
        # Calculate metrics
        actual = test_data['y'].values
        predicted = forecast['yhat'].values
        
        metrics = calculate_accuracy_metrics(actual, predicted)
        if metrics:
            return {
                'train_end': train_data['ds'].max(),
                'test_start': test_data['ds'].min(),
                'test_end': test_data['ds'].max(),
                'accuracy': metrics['AccuracyPercentage'],
                'mae': metrics['MAE'],
                'rmse': metrics['RMSE']
            }
        return None
    except Exception as e:
        print(f"Error in fold {i}: {str(e)}")
        return None

def cross_validate_model(actual_data, initial_periods=12, period_type='MS'):
    """
    Perform cross-validation on the forecast model.
    
    Args:
        actual_data (pd.DataFrame): DataFrame with 'ds' (date) and 'y' (sales) columns.
        initial_periods (int): Number of initial periods to use for training.
        period_type (str): Frequency of the forecast periods ('MS', 'QS', 'YS', 'D').
        
    Returns:
        pd.DataFrame: Cross-validation results with actual vs predicted values and metrics.
    """
    try:
        # Validate input data
        if not {'ds', 'y'}.issubset(actual_data.columns):
            raise ValueError("actual_data must contain 'ds' and 'y' columns")
        if actual_data['ds'].isnull().any() or actual_data['y'].isnull().any():
            raise ValueError("actual_data contains null values in 'ds' or 'y'")
        
        # Ensure we have enough data
        if len(actual_data) <= initial_periods + 6:
            raise ValueError("Not enough data for cross-validation")
        
        # Sort data by date
        actual_data = actual_data.sort_values('ds').reset_index(drop=True)
        
        # Determine number of CPU cores for parallelization
        num_cores = min(multiprocessing.cpu_count(), 4)  # Limit to 4 cores to avoid overuse
        
        # Run cross-validation in parallel with a step size of 4
        cv_results = Parallel(n_jobs=num_cores)(
            delayed(_cross_validate_fold)(i, actual_data, period_type)
            for i in range(initial_periods, len(actual_data) - 5, 4)
        )
        
        # Filter out None results and convert to DataFrame
        cv_results = [result for result in cv_results if result is not None]
        if not cv_results:
            raise ValueError("No valid cross-validation results obtained")
        
        return pd.DataFrame(cv_results)
    
    except Exception as e:
        raise Exception(f"Cross-validation error: {str(e)}")

# Example usage
if __name__ == "__main__":
    try:
        # Load sales data from SQL Server
        sales_data = load_sales_data(period_type='MS')
        print("Loaded sales data:")
        print(sales_data.head())
        
        # Generate forecast
        predicted, forecast, metrics = generate_forecast(sales_data, period_type='MS')
        print("\nPredicted data (historical):")
        print(predicted.head())
        print("\nForecast data (future):")
        print(forecast.head())
        print("\nAccuracy metrics:")
        print(metrics)
        
        # Perform cross-validation
        cv_results = cross_validate_model(sales_data, initial_periods=12, period_type='MS')
        print("\nCross-validation results:")
        print(cv_results)
        
    except Exception as e:
        print(f"Error: {str(e)}")