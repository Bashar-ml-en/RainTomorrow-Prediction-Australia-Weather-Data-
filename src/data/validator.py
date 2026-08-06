import pandera as pa
from pandera import DataFrameSchema, Column, Check
import yaml

def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Enforces strict boundaries checking to verify coordinates belong to Malaysian territory."""
    lat_ok = 0.8 <= latitude <= 8.0
    lon_ok = 99.0 <= longitude <= 120.0
    if not (lat_ok and lon_ok):
        raise ValueError(
            f"Geographical coordinates ({latitude}, {longitude}) are outside Malaysian boundaries "
            f"(Latitude: [0.8, 8.0] N, Longitude: [99.0, 120.0] E)."
        )
    return True

def get_weather_schema(config_path="configs/config.yaml"):
    """Loads configuration and returns a Pandera validation schema for hourly weather metrics."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    cities = [city["name"] for city in config["data"]["cities"]]
    
    # Pre-validate all cities coordinates in the config
    for city in config["data"]["cities"]:
        validate_coordinates(city["latitude"], city["longitude"])
        
    schema = DataFrameSchema({
        "temperature_2m": Column(pa.Float, Check.in_range(15.0, 45.0), coerce=True),
        "relative_humidity_2m": Column(pa.Float, Check.in_range(0.0, 100.0), coerce=True),
        "surface_pressure": Column(pa.Float, Check.in_range(900.0, 1080.0), coerce=True),
        "wind_speed_10m": Column(pa.Float, Check.greater_than_or_equal_to(0.0), coerce=True),
        "wind_direction_10m": Column(pa.Float, Check.in_range(0.0, 360.0), coerce=True),
        "rain": Column(pa.Float, Check.greater_than_or_equal_to(0.0), coerce=True),
        "city": Column(pa.String, Check.isin(cities), coerce=True),
        "monsoon_period": Column(pa.String, Check.isin(["Northeast Monsoon", "Southwest Monsoon", "Inter-monsoon"]), coerce=True),
        "rain_next_hour": Column(pa.Float, Check.isin([0.0, 1.0]), nullable=True, coerce=True)
    })
    return schema

def validate_data(df, config_path="configs/config.yaml"):
    """Validates the input dataframe using the Pandera schema."""
    schema = get_weather_schema(config_path)
    return schema.validate(df)
