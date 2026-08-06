import os
import joblib
import pandas as pd
import numpy as np
import yaml
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import mlflow
import mlflow.sklearn

from src.data.data_loader import load_malaysian_weather
from src.data.validator import validate_data
from src.features.pipeline import build_preprocessor

def train_model(config_path="configs/config.yaml"):
    # 1. Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    paths_cfg = config["paths"]
    model_cfg = config["model"]
    grid_cfg = model_cfg["grid_search"]
    
    # Ensure directory structures exist
    os.makedirs(paths_cfg["model_dir"], exist_ok=True)
    os.makedirs(os.path.dirname(paths_cfg["database_path"]), exist_ok=True)
    
    # 2. Fetch and Validate Data
    print("Fetching and processing historical weather dataset...")
    df = load_malaysian_weather(config_path)
    
    print("Validating dataset via Pandera quality gateway...")
    df_validated = validate_data(df, config_path)
    
    # 3. Features-Target split
    target_col = config["features"]["target"]
    feature_cols = config["features"]["numerical"] + config["features"]["categorical"]
    
    X = df_validated[feature_cols]
    y = df_validated[target_col]
    
    # 4. Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=model_cfg["test_size"], 
        random_state=model_cfg["random_state"],
        stratify=y
    )
    
    # 5. Build Pipeline
    preprocessor = build_preprocessor(config_path)
    clf_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', RandomForestClassifier(random_state=model_cfg["random_state"]))
    ])
    
    # 6. Grid Search CV Setup
    print("Starting Grid Search CV parameter optimization...")
    cv = GridSearchCV(
        clf_pipeline, 
        param_grid=grid_cfg, 
        cv=5, 
        scoring='f1', 
        n_jobs=-1,
        verbose=1
    )
    
    # 7. MLflow Experiment Tracking
    mlflow.set_experiment("Malaysia-MultiCity-HourlyRainPrediction")
    with mlflow.start_run() as run:
        print(f"MLflow Active Run ID: {run.info.run_id}")
        
        # Fit GridSearchCV
        cv.fit(X_train, y_train)
        
        # Get Best Estimator
        best_pipeline = cv.best_estimator_
        best_params = cv.best_params_
        
        # Log Best Hyperparameters
        for key, value in best_params.items():
            mlflow.log_param(key, value)
            
        print(f"Optimal Parameters Found: {best_params}")
        
        # Evaluate on Test Set
        y_pred = best_pipeline.predict(X_test)
        y_prob = best_pipeline.predict_proba(X_test)[:, 1] if hasattr(best_pipeline, "predict_proba") else None
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob) if y_prob is not None else 0.0
        
        # Log Metrics
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("roc_auc", auc)
        
        print("\nEvaluation Metrics on Test Set:")
        print(f" - Accuracy:  {accuracy:.4f}")
        print(f" - Precision: {precision:.4f}")
        print(f" - Recall:    {recall:.4f}")
        print(f" - F1-Score:  {f1:.4f}")
        print(f" - ROC-AUC:   {auc:.4f}\n")
        
        # Save local copy of model
        model_path = paths_cfg["model_path"]
        joblib.dump(best_pipeline, model_path)
        print(f"Saved optimal model pipeline to {model_path}")
        
        # Log Pipeline binary as MLflow Artifact
        mlflow.sklearn.log_model(best_pipeline, "model", serialization_format="pickle")
        print("Logged model pipeline as MLflow artifact.")
        
    print("Training process finished successfully!")

if __name__ == "__main__":
    train_model()
