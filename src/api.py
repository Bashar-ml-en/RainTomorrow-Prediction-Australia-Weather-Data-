import os
import sqlite3
import requests
import yaml
import time
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.data.data_loader import date_to_monsoon
from src.models.predict import RainPredictor
from scripts.fetch_and_predict import init_db, log_prediction

app = FastAPI(title="Malaysian Hourly Rain Predictor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

CONFIG_PATH = "configs/config.yaml"

# Load Config
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

db_path = config["paths"]["database_path"]
init_db(db_path)

# Initialize Predictor
predictor = RainPredictor(CONFIG_PATH)

@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the main dashboard user interface."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Web UI template not found.")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/cities")
def get_cities():
    """Returns the list of configured Malaysian cities."""
    return config["data"]["cities"]

@app.get("/api/forecast")
def get_forecast():
    """Returns tomorrow's hourly forecasts. Checks local SQLite cache first; requests missing cities from Open-Meteo in a batch request."""
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    results = []
    
    cities = config["data"]["cities"]
    
    # 1. Identify which cities need live fetches vs. cached reads
    uncached_cities = []
    
    for city in cities:
        cached_records = []
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            time_threshold = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                SELECT * FROM forecasts 
                WHERE city = ? AND forecast_time LIKE ? AND timestamp >= ?
                ORDER BY forecast_time ASC
            """, (city["name"], f"{tomorrow_str}%", time_threshold))
            rows = cursor.fetchall()
            conn.close()
            cached_records = [dict(row) for row in rows]
        except Exception as e:
            print(f"Error checking cache for {city['name']}: {str(e)}")
            cached_records = []
            
        if len(cached_records) >= 20:  # Ensure we have a nearly complete day's hourly set
            results.append({
                "city": city["name"],
                "monsoon_period": cached_records[0]["monsoon_period"],
                "hourly_records": cached_records
            })
            print(f"Loaded {city['name']} forecast from local database cache.")
        else:
            uncached_cities.append(city)
            
    # 2. If there are any uncached cities, fetch them in a batch request
    if uncached_cities:
        print(f"Fetching live forecast for uncached cities: {[c['name'] for c in uncached_cities]}")
        try:
            latitudes = [str(city["latitude"]) for city in uncached_cities]
            longitudes = [str(city["longitude"]) for city in uncached_cities]
            
            params = {
                "latitude": ",".join(latitudes),
                "longitude": ",".join(longitudes),
                "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,rain,weather_code",
                "forecast_days": 2,
                "timezone": "Asia/Singapore"
            }
            response = requests.get(config["data"]["forecast_api_url"], params=params, timeout=15)
            if response.status_code == 200:
                data_list = response.json()
                if not isinstance(data_list, list):
                    data_list = [data_list]
                    
                for idx, city in enumerate(uncached_cities):
                    if idx >= len(data_list):
                        break
                    city_data = data_list[idx]
                    hourly = city_data.get("hourly", {})
                    if not hourly:
                        continue
                        
                    # Build hourly DataFrame
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
                    
                    # Filter for tomorrow's 24 hours
                    df_tomorrow = df_all_hourly[df_all_hourly["time"].dt.strftime("%Y-%m-%d") == tomorrow_str].copy()
                    if df_tomorrow.empty:
                        continue
                        
                    # Add categorical variables
                    df_tomorrow["city"] = city["name"]
                    df_tomorrow["monsoon_period"] = df_tomorrow["time"].apply(date_to_monsoon)
                    
                    # Predict
                    preds, probs = predictor.predict(df_tomorrow)
                    
                    df_tomorrow["predicted_rain_next_hour"] = preds
                    df_tomorrow["probability"] = probs
                    
                    # Save predictions to SQLite database and append to result list
                    city_records = []
                    for _, row in df_tomorrow.iterrows():
                        record = {
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
                            "monsoon_period": row["monsoon_period"]
                          }
                        log_prediction(db_path, record)
                        city_records.append(record)
                        
                    results.append({
                        "city": city["name"],
                        "monsoon_period": df_tomorrow.iloc[0]["monsoon_period"],
                        "hourly_records": city_records
                    })
            else:
                raise Exception(f"Batch fetch failed with code {response.status_code}")
        except Exception as e:
            print(f"Error in batch forecast: {str(e)}. Falling back to single queries...")
            for city in uncached_cities:
                try:
                    params = {
                        "latitude": city["latitude"],
                        "longitude": city["longitude"],
                        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,rain,weather_code",
                        "forecast_days": 2,
                        "timezone": "Asia/Singapore"
                    }
                    response = requests.get(config["data"]["forecast_api_url"], params=params, timeout=10)
                    if response.status_code != 200:
                        continue
                    city_data = response.json()
                    hourly = city_data.get("hourly", {})
                    if not hourly:
                        continue
                        
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
                    df_tomorrow = df_all_hourly[df_all_hourly["time"].dt.strftime("%Y-%m-%d") == tomorrow_str].copy()
                    if df_tomorrow.empty:
                        continue
                    df_tomorrow["city"] = city["name"]
                    df_tomorrow["monsoon_period"] = df_tomorrow["time"].apply(date_to_monsoon)
                    
                    preds, probs = predictor.predict(df_tomorrow)
                    df_tomorrow["predicted_rain_next_hour"] = preds
                    df_tomorrow["probability"] = probs
                    
                    city_records = []
                    for _, row in df_tomorrow.iterrows():
                        record = {
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
                            "monsoon_period": row["monsoon_period"]
                        }
                        log_prediction(db_path, record)
                        city_records.append(record)
                        
                    results.append({
                        "city": city["name"],
                        "monsoon_period": df_tomorrow.iloc[0]["monsoon_period"],
                        "hourly_records": city_records
                    })
                    time.sleep(1.5)
                except Exception as inner_e:
                    print(f"Error on single fallback query for {city['name']}: {str(inner_e)}")
                    continue
                
    return results

@app.get("/api/history")
def get_history():
    """Returns the history of predictions saved in SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM forecasts ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
