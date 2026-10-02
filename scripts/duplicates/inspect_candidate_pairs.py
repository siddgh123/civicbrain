from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "complaints" / "verified" / "complaints_verified.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "duplicates"
OUTPUT_FILE = OUTPUT_DIR / "candidate_pairs.csv"

# Step 12 project baseline
SPATIAL_RADIUS_METERS = 300

# IMPORTANT:
# Exact recent-window is intentionally not frozen yet.
# We inspect several windows first.
TEST_WINDOWS_DAYS = [7, 14, 30, 60, 90]


def haversine_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return great-circle distance between two GPS coordinates in meters."""
    radius_earth_m = 6_371_000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    return 2 * radius_earth_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def main() -> None:
    print("=" * 72)
    print("CIVICBRAIN STEP 12 — DUPLICATE CANDIDATE INSPECTION")
    print("=" * 72)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Complaint dataset not found:\n{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "complaint_id",
        "category",
        "description",
        "latitude",
        "longitude",
        "created_at",
    ]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    print(f"Input rows loaded        : {len(df)}")

    # Clean numeric fields
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Step 8 CSV uses created_at.
    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce",
        utc=True,
    )

    invalid_gps = df["latitude"].isna() | df["longitude"].isna()
    invalid_time = df["created_at"].isna()

    print(f"Rows with invalid GPS    : {invalid_gps.sum()}")
    print(f"Rows with invalid time   : {invalid_time.sum()}")

    work = df.loc[
        ~invalid_gps & ~invalid_time
    ].copy()

    work = work.sort_values(
        ["created_at", "complaint_id"]
    ).reset_index(drop=True)

    print(f"Usable rows              : {len(work)}")

    if len(work) < 2:
        raise ValueError("At least two usable complaints are required.")

    # ------------------------------------------------------------
    # Inspect candidate counts for different recent windows.
    # No window is frozen yet.
    # ------------------------------------------------------------

    print()
    print("Candidate-pair counts by recent window")
    print("-" * 72)

    window_results = []

    for window_days in TEST_WINDOWS_DAYS:
        pair_count = 0

        for i in range(len(work)):
            current = work.iloc[i]

            for j in range(i + 1, len(work)):
                other = work.iloc[j]

                time_diff_days = abs(
                    (current["created_at"] - other["created_at"]).total_seconds()
                ) / 86400.0

                if time_diff_days > window_days:
                    # Because the data is sorted by time, later rows
                    # will only be farther away.
                    if other["created_at"] > current["created_at"]:
                        break
                    continue

                distance = haversine_meters(
                    float(current["latitude"]),
                    float(current["longitude"]),
                    float(other["latitude"]),
                    float(other["longitude"]),
                )

                if distance <= SPATIAL_RADIUS_METERS:
                    pair_count += 1

        window_results.append(
            {
                "recent_window_days": window_days,
                "candidate_pair_count": pair_count,
            }
        )

        print(
            f"{window_days:>3} days -> {pair_count} candidate pairs"
        )

    # ------------------------------------------------------------
    # Build a candidate dataset using the broadest inspection
    # window for review only.
    # We do NOT label duplicates here.
    # ------------------------------------------------------------

    selected_window = max(TEST_WINDOWS_DAYS)

    rows = []

    for i in range(len(work)):
        a = work.iloc[i]

        for j in range(i + 1, len(work)):
            b = work.iloc[j]

            time_diff_hours = abs(
                (a["created_at"] - b["created_at"]).total_seconds()
            ) / 3600.0

            if time_diff_hours > selected_window * 24:
                if b["created_at"] > a["created_at"]:
                    break
                continue

            distance = haversine_meters(
                float(a["latitude"]),
                float(a["longitude"]),
                float(b["latitude"]),
                float(b["longitude"]),
            )

            if distance <= SPATIAL_RADIUS_METERS:
                rows.append(
                    {
                        "pair_id": f"P{len(rows) + 1:05d}",
                        "complaint_id_1": int(a["complaint_id"]),
                        "complaint_id_2": int(b["complaint_id"]),
                        "category_1": str(a["category"]),
                        "category_2": str(b["category"]),
                        "description_1": str(a["description"]),
                        "description_2": str(b["description"]),
                        "latitude_1": float(a["latitude"]),
                        "longitude_1": float(a["longitude"]),
                        "latitude_2": float(b["latitude"]),
                        "longitude_2": float(b["longitude"]),
                        "submitted_time_1": a["created_at"].isoformat(),
                        "submitted_time_2": b["created_at"].isoformat(),
                        "distance_meters": round(distance, 3),
                        "time_difference_hours": round(time_diff_hours, 3),
                        "actual_duplicate": "",
                        "label_notes": "",
                    }
                )

    candidate_df = pd.DataFrame(rows)

    candidate_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print()
    print(f"Review window used      : {selected_window} days")
    print(f"Spatial radius          : {SPATIAL_RADIUS_METERS} meters")
    print(f"Candidate pairs created : {len(candidate_df)}")
    print(f"Output                  : {OUTPUT_FILE}")

    print("=" * 72)
    print("CANDIDATE PAIR DATASET CREATED")
    print("=" * 72)


if __name__ == "__main__":
    main()