from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import yaml

def build_preprocessor(config_path="configs/config.yaml"):
    """Builds a Scikit-Learn ColumnTransformer preprocessor based on YAML parameters."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    num_features = config["features"]["numerical"]
    cat_features = config["features"]["categorical"]
    
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(transformers=[
        ('num', numeric_transformer, num_features),
        ('cat', categorical_transformer, cat_features)
    ])
    
    return preprocessor
