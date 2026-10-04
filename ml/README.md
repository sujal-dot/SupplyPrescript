# Machine Learning Environment

This directory houses future ML models, experiment notebooks, and preprocessing/training scripts for demand forecasting and supply chain predictive analytics.

## Directory Structure

```text
ml/
├── models/       # Serialized models (.joblib, .json)
├── notebooks/    # Jupyter exploration and experimentation notebooks
├── scripts/      # Data preprocessing and model training scripts
├── requirements.txt # Python dependencies for ML
└── README.md
```

## Dependencies

- `pandas` — Data manipulation and time series handling
- `numpy` — Numerical computations and vectorized operations
- `scikit-learn` — Baseline models, evaluation metrics, and transformers
- `xgboost` — Gradient boosting algorithms
- `joblib` — Model persistence and serialization

## Usage

Dependencies are managed in `requirements.txt` and installed in the project virtual environment:

```bash
pip install -r ml/requirements.txt
```
