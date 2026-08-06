import os
import sqlite3
import pandas as pd
import requests
import yaml
from datetime import datetime, timedelta

from src.data.data_loader import date_to_monsoon
from src.models.predict import RainPredictor

def init_db(db_path):
    """Initializes the SQLite database table for hourly prediction archiving."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop table if exists to update schema
    cursor.execute("DROP TABLE IF EXISTS forecasts")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            forecast_time TEXT,
            city TEXT,
            temperature_2m REAL,
            relative_humidity_2m REAL,
            surface_pressure REAL,
            wind_speed_10m REAL,
            wind_direction_10m REAL,
            rain REAL,
            predicted_rain_next_hour INTEGER,
            probability REAL,
            weather_code INTEGER,
            monsoon_period TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_prediction(db_path, data_dict):
    """Logs a single hourly prediction record to the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO forecasts (
            timestamp, forecast_time, city, temperature_2m, relative_humidity_2m,
            surface_pressure, wind_speed_10m, wind_direction_10m, rain,
            predicted_rain_next_hour, probability, weather_code, monsoon_period
        ) VALUES (
            :timestamp, :forecast_time, :city, :temperature_2m, :relative_humidity_2m,
            :surface_pressure, :wind_speed_10m, :wind_direction_10m, :rain,
            :predicted_rain_next_hour, :probability, :weather_code, :monsoon_period
        )
    """, data_dict)
    conn.commit()
    conn.close()

def run_real_time_prediction(config_path="configs/config.yaml"):
    # 1. Load configs
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    db_path = config["paths"]["database_path"]
    init_db(db_path)
    
    # 2. Instantiate Predictor
    predictor = RainPredictor(config_path)
    
    # 3. Process cities forecast (Tomorrow's 24 hours)
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    print(f"--- Weather Forecast for Tomorrow ({tomorrow_str}) ---")
    
    forecast_records = []
    for city in config["data"]["cities"]:
        print(f"\nFetching forecast variables for {city['name']}...")
        params = {
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,rain,weather_code",
            "forecast_days": 2,  # Fetch today and tomorrow
            "timezone": "Asia/Singapore"
        }
        
        response = requests.get(config["data"]["forecast_api_url"], params=params)
        if response.status_code != 200:
            print(f"Failed to fetch forecast for {city['name']}")
            continue
            
        data = response.json()
        hourly = data.get("hourly", {})
        if not hourly:
            print(f"No hourly forecast data found for {city['name']}")
            continue
            
        # Build hourly dataframe
        df_all_hourly = pd.DataFrame({
            "time": pd.to_datetime(hourly["time"]),
            "temperature_2m": hourly["temperature_2m"],
            "relative_humidity_2m": hourly["relative_humidity_2m"],
            "surface_pressure": hourly["surface_pressure"],
            "wind_speed_10m": hourly["wind_speed_10m"],
            "wind_direction_10m": hourly["wind_direction_10m"],
            "rain": hourly["rain"],
            "weather_code": hourly["weather_code"]
        })
        
        # Filter for tomorrow's 24 hours (e.g. tomorrow_str)
        df_tomorrow = df_all_hourly[df_all_hourly["time"].dt.strftime("%Y-%m-%d") == tomorrow_str].copy()
        if df_tomorrow.empty:
            print(f"No forecast found for tomorrow in {city['name']}")
            continue
            
        # Add categorical fields required by pipeline
        df_tomorrow["city"] = city["name"]
        df_tomorrow["monsoon_period"] = df_tomorrow["time"].apply(date_to_monsoon)
        
        # Predict
        preds, probs = predictor.predict(df_tomorrow)
        
        df_tomorrow["predicted_rain_next_hour"] = preds
        df_tomorrow["probability"] = probs
        
        # Log to Database
        for _, row in df_tomorrow.iterrows():
            log_record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "forecast_time": row["time"].strftime("%Y-%m-%d %H:%M"),
                "city": city["name"],
                "temperature_2m": float(row["temperature_2m"]),
                "relative_humidity_2m": float(row["relative_humidity_2m"]),
                "surface_pressure": float(row["surface_pressure"]),
                "wind_speed_10m": float(row["wind_speed_10m"]),
                "wind_direction_10m": float(row["wind_direction_10m"]),
                "rain": float(row["rain"]),
                "predicted_rain_next_hour": int(row["predicted_rain_next_hour"]),
                "probability": float(row["probability"]),
                "weather_code": int(row["weather_code"]),
                "monsoon_period": str(row["monsoon_period"])
            }
            log_prediction(db_path, log_record)
            forecast_records.append(log_record)
            
        print(f"Logged 24 hourly predictions for {city['name']}.")
        
    print("\n--- Daily predictions archived in SQLite database ---")
    return forecast_records

if __name__ == "__main__":
    run_real_time_prediction()
