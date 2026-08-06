import joblib
import pandas as pd
import yaml
from src.data.validator import validate_data

class RainPredictor:
    """Wrapper class to load the serialized pipeline model and run verified validation and inference."""
    
    def __init__(self, config_path="configs/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.model_path = self.config["paths"]["model_path"]
        self.config_path = config_path
        
        # Load the joblib pipeline
        self.pipeline = joblib.load(self.model_path)
        
    def predict(self, df_raw):
        """Validates features via Pandera and returns predictions with probability scores."""
        # Ensure target column placeholder is present for schema compliance
        if "rain_next_hour" not in df_raw.columns:
            df_raw["rain_next_hour"] = None
            
        # Validate data columns
        df_validated = validate_data(df_raw, self.config_path)
        
        # Reorder to feature set
        feature_cols = self.config["features"]["numerical"] + self.config["features"]["categorical"]
        X = df_validated[feature_cols]
        
        # Predict
        preds = self.pipeline.predict(X)
        probs = self.pipeline.predict_proba(X)[:, 1]
        
        return preds, probs
