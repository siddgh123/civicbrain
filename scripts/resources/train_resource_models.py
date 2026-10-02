import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

TRAIN_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
    / "split"
    / "train.csv"
)

MODEL_DIR = (
    BASE_DIR
    / "data"
    / "resources"
    / "models"
)

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Load training data
train_df = pd.read_csv(TRAIN_FILE)

# Features
FEATURE_COLUMNS = [
    "issue_type",
    "latitude",
    "longitude",
    "severity",
    "estimated_area"
]

# Convert categorical columns
X_train = pd.get_dummies(
    train_df[FEATURE_COLUMNS],
    columns=["issue_type", "severity"]
)

# Targets
targets = {
    "workers": "estimated_workers",
    "duration": "estimated_duration_hours",
    "cost": "total_cost"
}

for model_name, target_column in targets.items():

    y_train = train_df[target_column]

    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42
    )

    model.fit(X_train, y_train)

    model_path = MODEL_DIR / f"{model_name}_model.json"

    model.save_model(model_path)

    print(f"{model_name} model trained")
    print(f"Saved: {model_path}")

print("\nRESOURCE MODELS TRAINING COMPLETE")