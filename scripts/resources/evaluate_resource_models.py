import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]

TEST_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
    / "split"
    / "test.csv"
)

MODEL_DIR = (
    BASE_DIR
    / "data"
    / "resources"
    / "models"
)

test_df = pd.read_csv(TEST_FILE)

FEATURE_COLUMNS = [
    "issue_type",
    "latitude",
    "longitude",
    "severity",
    "estimated_area"
]

X_test = pd.get_dummies(
    test_df[FEATURE_COLUMNS],
    columns=["issue_type", "severity"]
)

targets = {
    "workers": "estimated_workers",
    "duration": "estimated_duration_hours",
    "cost": "total_cost"
}

for model_name, target_column in targets.items():

    model = XGBRegressor()
    model.load_model(MODEL_DIR / f"{model_name}_model.json")

    y_test = test_df[target_column]
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    print(f"\n{model_name.upper()} MODEL")
    print(f"MAE  : {mae:.2f}")
    print(f"RMSE : {rmse:.2f}")
    print(f"R2   : {r2:.4f}")

print("\nRESOURCE MODEL EVALUATION COMPLETE")