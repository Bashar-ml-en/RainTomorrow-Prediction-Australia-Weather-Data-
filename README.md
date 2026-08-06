# Semenanjung & Borneo Hourly Rainfall Forecaster (Malaysia)

An enterprise-grade, sequence-aware Machine Learning pipeline and interactive web application designed to predict hourly rainfall for major cities across Malaysia. 

This repository has migrated from a legacy temperate-zone daily notebook into a **production-ready, real-time hourly forecasting system** powered by a Scikit-Learn Random Forest pipeline, FastAPI, Pandera validation, SQLite cache logging, and a React + Vite glassmorphic dashboard.

---

## 🚀 System Architecture

The application is split into a modular backend and frontend monorepo architecture:

```
[Vite + React SPA]  ──(API Requests)──>  [FastAPI Backend] ──> [Scikit-Learn ML Pipeline]
(Vercel Hosting)                         (Render / Railway)      (Random Forest Classifier)
                                                │
                                                ▼
                                      [(SQLite Forecast Cache)]
```

### Key Technical Specs:
*   **Hourly Resolution**: The model is trained on sequential hourly weather data to forecast the rain state of Hour $H+1$ given weather parameters at Hour $H$.
*   **Database Caching**: API requests check a local SQLite database for predictions generated in the last 60 minutes. If valid, they return instantly to avoid rate-limiting on external weather services.
*   **Geographic Quality Gate**: Implements a Pandera data quality validation layer that enforces strict tropical climate bounds and Malaysian territorial coordinates.

---

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, Uvicorn, Pandas, Scikit-Learn, Joblib, Pandera, MLflow.
*   **Frontend**: React, Vite, CSS3 custom property themes (Dark, Light, and Cyber Neon), SVG data visualizations.
*   **Data Sources**: Open-Meteo Weather Archive & Forecast API.

---

## 📂 Project Structure

```
├── configs/
│   └── config.yaml           # Centralized pipeline configurations & hyperparameter search space
├── data/
│   └── predictions.db        # SQLite forecast cache database (automatically initialized)
├── frontend/                 # Vite + React user interface dashboard workspace
│   ├── src/
│   │   ├── App.jsx           # Main React component managing visual states & timeline navigation
│   │   ├── main.jsx
│   │   └── index.css         # CSS design system (Responsive grids & Glassmorphic variables)
│   ├── package.json
│   └── vite.config.js        # Vite dev proxy rules for backend routing
├── models/
│   └── pipeline.joblib       # Serialized Random Forest model pipeline binary
├── scripts/
│   └── fetch_and_predict.py  # Standalone scheduled inference runner
├── src/
│   ├── data/
│   │   ├── data_loader.py    # Raw hourly weather ingestion & target label shifting
│   │   └── validator.py      # Pandera schemas for tropical ranges and coordinates
│   ├── features/
│   │   └── pipeline.py       # ColumnTransformer mapping encoders & standard scaling
│   ├── models/
│   │   ├── train.py          # MLflow logged model fitting with GridSearchCV F1 optimization
│   │   └── predict.py        # Validated batch inference wrapper
│   └── api.py                # FastAPI route endpoints
└── tests/
    └── test_pipeline.py      # Pytest validation check cases
```

---

## ⚡ Setup & Installation

### Prerequisite: Python & Node.js
Ensure you have Python 3.10+ and Node.js v18+ installed on your local machine.

### 1. Backend Installation & Training
1.  Clone the repository and navigate to the project directory:
    ```bash
    git clone https://github.com/Bashar-ml-en/RainToday-Prediction.git
    cd RainToday-Prediction
    ```
2.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Train the model using 10 years of historical weather data across 7 Malaysian cities:
    ```bash
    python -m src.models.train
    ```
    *This runs a 5-fold cross-validation grid search to optimize F1-score and logs parameters directly to your local MLflow server.*
4.  Start the FastAPI backend server:
    ```bash
    python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
    ```

### 2. Frontend Installation & Dev Run
1.  Open a new terminal window and navigate to the frontend folder:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Launch the Vite dev server:
    ```bash
    npm run dev
    ```
4.  Visit **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 📊 Model Evaluation (Hourly Test Set)
*   **F1-Score**: `77.23%`
*   **Accuracy**: `83.15%`
*   **ROC-AUC (Confidence)**: `88.33%`
*   **Target Rule**: Rain is classified as positive (`1.0`) if precipitation in the next hour $\ge 0.1\text{ mm}$.
