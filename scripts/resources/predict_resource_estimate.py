import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = BASE_DIR / "data" / "resources" / "models"

ISSUE_TYPES = [
    "Blocked Drain",
    "Garbage Accumulation",
    "Other",
    "Pothole",
    "Road Damage",
    "Streetlight",
    "Water Leakage",
    "Waterlogging"
]

SEVERITIES = [
    "High",
    "Low",
    "Medium"
]


def predict_resource_estimate(
    issue_type,
    latitude,
    longitude,
    severity,
    estimated_area
):

    input_data = pd.DataFrame([{
        "issue_type": issue_type,
        "latitude": latitude,
        "longitude": longitude,
        "severity": severity,
        "estimated_area": estimated_area
    }])

    # Use the same categories used during training
    input_data["issue_type"] = pd.Categorical(
        input_data["issue_type"],
        categories=ISSUE_TYPES
    )

    input_data["severity"] = pd.Categorical(
        input_data["severity"],
        categories=SEVERITIES
    )

    X = pd.get_dummies(
        input_data,
        columns=["issue_type", "severity"]
    )

    predictions = {}

    for model_name in ["workers", "duration", "cost"]:

        model = XGBRegressor()

        model.load_model(
            MODEL_DIR / f"{model_name}_model.json"
        )

        # Make sure feature order exactly matches training
        model_features = model.get_booster().feature_names

        X = X.reindex(
            columns=model_features,
            fill_value=False
        )

        predictions[model_name] = model.predict(X)[0]

    return {
        "estimated_workers": round(
            predictions["workers"]
        ),
        "estimated_duration_hours": round(
            predictions["duration"], 1
        ),
        "estimated_total_cost": round(
            predictions["cost"]
        )
    }


if __name__ == "__main__":

    result = predict_resource_estimate(
        issue_type="Pothole",
        latitude=18.718913,
        longitude=73.695537,
        severity="Medium",
        estimated_area=4.5
    )

    print("\nRESOURCE ESTIMATE")
    print(f"Workers: {result['estimated_workers']}")
    print(
        f"Duration: "
        f"{result['estimated_duration_hours']} hours"
    )
    print(
        f"Total Cost: "
        f"₹{result['estimated_total_cost']}"
    )