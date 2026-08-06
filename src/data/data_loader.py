import os
import time
import requests
import pandas as pd
import yaml
from datetime import datetime

def load_config(config_path="configs/config.yaml"):
    """Loads configuration settings from a YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def date_to_monsoon(dt):
    """Maps a datetime object to a Malaysian monsoon period."""
    month = dt.month
    if month in [11, 12, 1, 2, 3]:
        return "Northeast Monsoon"
    elif month in [5, 6, 7, 8, 9]:
        return "Southwest Monsoon"
    else:
        return "Inter-monsoon"

def fetch_city_history(api_url, city_name, lat, lon, start_date, end_date):
    """Fetches hourly weather from Open-Meteo and returns raw hourly records, with retries."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,rain",
        "timezone": "Asia/Singapore"  # Malaysian time zone
    }
    
    max_retries = 5
    retry_delay = 5  # Seconds to wait
    
    for attempt in range(max_retries):
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            break
            
        # If rate limit exceeded
        if "limit exceeded" in response.text.lower() or response.status_code == 429:
            print(f"Rate limit hit for {city_name}. Waiting {retry_delay} seconds (Attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            retry_delay += 5  # Increase delay
        else:
            raise Exception(f"Failed to fetch data for {city_name}: {response.text}")
    else:
        raise Exception(f"Max retries exceeded for {city_name}.")
        
    data = response.json()
    hourly = data.get("hourly", {})
    if not hourly:
        raise Exception(f"No hourly data found for {city_name}")
        
    # Build dataframe from hourly readings
    df_hourly = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "temperature_2m": hourly["temperature_2m"],
        "relative_humidity_2m": hourly["relative_humidity_2m"],
        "surface_pressure": hourly["surface_pressure"],
        "wind_speed_10m": hourly["wind_speed_10m"],
        "wind_direction_10m": hourly["wind_direction_10m"],
        "rain": hourly["rain"]
    })
    
    df_hourly["city"] = city_name
    df_hourly["monsoon_period"] = df_hourly["time"].apply(date_to_monsoon)
    
    return df_hourly

def load_malaysian_weather(config_path="configs/config.yaml"):
    """Fetches and processes multi-city weather data, creating next hour's target rain labels."""
    config = load_config(config_path)
    data_cfg = config["data"]
    
    all_cities_data = []
    for city in data_cfg["cities"]:
        print(f"Fetching historical hourly weather data for {city['name']}...")
        city_df = fetch_city_history(
            api_url=data_cfg["archive_api_url"],
            city_name=city["name"],
            lat=city["latitude"],
            lon=city["longitude"],
            start_date=data_cfg["start_date"],
            end_date=data_cfg["end_date"]
        )
        
        # Sort chronologically by time
        city_df = city_df.sort_values("time")
        
        # Target label: rain next hour is 1 if next hour's rain >= 0.1mm
        city_df["rain_next_hour"] = (city_df["rain"].shift(-1) >= 0.1).astype(float)
        
        # Drop the last row as next hour's actual rain is unknown
        city_df = city_df.dropna(subset=["rain_next_hour"])
        all_cities_data.append(city_df)
        time.sleep(2)  # Delay between requests to avoid rate limits
        
    combined_df = pd.concat(all_cities_data, ignore_index=True)
    return combined_df

if __name__ == "__main__":
    df = load_malaysian_weather()
    print(f"Loaded {df.shape[0]} hourly records across {df['city'].nunique()} cities.")
    print(df.head())
