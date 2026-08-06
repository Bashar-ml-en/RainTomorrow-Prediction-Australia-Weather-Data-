import pytest
import pandas as pd
import numpy as np
import pandera as pa
from src.data.validator import validate_data
from src.features.pipeline import build_preprocessor

def test_pandera_invalid_humidity():
    """Verifies that the Pandera validation schema raises an error when hourly humidity is out of bounds."""
    invalid_df = pd.DataFrame([{
        "temperature_2m": 32.0,
        "relative_humidity_2m": 120.0,  # Invalid: > 100%
        "surface_pressure": 1010.0,
        "wind_speed_10m": 10.0,
        "wind_direction_10m": 180.0,
        "rain": 0.0,
        "city": "Kuala Lumpur",
        "monsoon_period": "Northeast Monsoon",
        "rain_next_hour": 0.0
    }])
    
    with pytest.raises(pa.errors.SchemaError):
        validate_data(invalid_df)

def test_preprocessor_imputation():
    """Verifies that the preprocessing pipeline handles hourly NaNs without crashing using imputers."""
    preprocessor = build_preprocessor()
    
    # Small training set for fitting the transformers
    df_fit = pd.DataFrame([
        {
            "temperature_2m": 30.0,
            "relative_humidity_2m": 80.0,
            "surface_pressure": 1010.0,
            "wind_speed_10m": 12.0,
            "wind_direction_10m": 180.0,
            "rain": 0.0,
            "city": "Kuala Lumpur",
            "monsoon_period": "Northeast Monsoon"
        },
        {
            "temperature_2m": 32.0,
            "relative_humidity_2m": 85.0,
            "surface_pressure": 1008.0,
            "wind_speed_10m": 15.0,
            "wind_direction_10m": 200.0,
            "rain": 5.0,
            "city": "Kuala Lumpur",
            "monsoon_period": "Northeast Monsoon"
        }
    ])
    
    # Test record containing NaN values to be imputed
    df_missing = pd.DataFrame([{
        "temperature_2m": np.nan,  # Missing temperature to be imputed by mean
        "relative_humidity_2m": 80.0,
        "surface_pressure": 1010.0,
        "wind_speed_10m": np.nan,  # Missing wind speed to be imputed by mean
        "wind_direction_10m": 180.0,
        "rain": 0.0,
        "city": "Kuala Lumpur",
        "monsoon_period": "Northeast Monsoon"
    }])
    
    preprocessor.fit(df_fit)
    transformed = preprocessor.transform(df_missing)
    
    # Verify no NaN values exist in the preprocessed outputs
    assert transformed.shape == (1, transformed.shape[1])
    assert not np.isnan(transformed).any()

def test_valid_malaysian_coordinates():
    from src.data.validator import validate_coordinates
    assert validate_coordinates(3.1390, 101.6869) is True

def test_invalid_coordinates_raise_value_error():
    from src.data.validator import validate_coordinates
    import pytest
    with pytest.raises(ValueError):
        validate_coordinates(51.5074, -0.1278)
