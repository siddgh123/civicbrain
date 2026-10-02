from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "complaints"
    / "verified"
    / "complaints_verified.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "duplicates"
OUTPUT_FILE = OUTPUT_DIR / "duplicate_benchmark.csv"
CONFIG_FILE = OUTPUT_DIR / "duplicate_benchmark_config.json"
SUMMARY_FILE = OUTPUT_DIR / "duplicate_benchmark_summary.csv"

RANDOM_SEED = 42

TOTAL_PAIRS = 300
POSITIVE_PAIRS = 150
NEGATIVE_PAIRS = 150

# Synthetic duplicate variants are intentionally kept close enough
# for the model to consider them plausible duplicates.
POSITIVE_MAX_DISTANCE_M = 80
POSITIVE_MAX_TIME_HOURS = 72

# Negative pairs are selected from distinct synthetic complaint instances
# that are still within the 300 m candidate-search baseline.
NEGATIVE_MAX_DISTANCE_M = 300


def haversine_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_m = 6_371_000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(d_lambda / 2.0) ** 2
    )

    return (
        2.0
        * earth_radius_m
        * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    )


def offset_coordinate(
    lat: float,
    lon: float,
    distance_m: float,
    bearing_rad: float,
) -> tuple[float, float]:
    """Create a small synthetic location offset in meters."""
    earth_radius_m = 6_371_000.0

    lat_rad = math.radians(lat)

    d_lat = (
        distance_m * math.cos(bearing_rad) / earth_radius_m
    )
    d_lon = (
        distance_m
        * math.sin(bearing_rad)
        / (earth_radius_m * max(math.cos(lat_rad), 1e-8))
    )

    new_lat = lat + math.degrees(d_lat)
    new_lon = lon + math.degrees(d_lon)

    return new_lat, new_lon


def normalize_text(value: object) -> str:
    if value is None:
        return ""

    return " ".join(str(value).split())


def make_synthetic_duplicate_text(
    description: str,
    category: str,
    variant_number: int,
) -> str:
    """
    Create a controlled semantic paraphrase.
    The variant remains based on the same source complaint so the
    benchmark label is known by construction.
    """
    text = normalize_text(description)

    replacements = [
        ("is not functioning", "is not working"),
        ("is not functioning.", "is not working."),
        ("is not working", "has stopped working"),
        ("is not working.", "has stopped working."),
        ("has accumulated", "has built up"),
        ("has built up", "has accumulated"),
        ("has been dumped", "has been left"),
        ("has blocked", "has caused a blockage in"),
        ("is blocked", "has become blocked"),
        ("is not flowing", "is not draining properly"),
        ("requires cleaning and maintenance", "needs cleaning and maintenance"),
        ("needs repair", "requires repair"),
        ("causing difficulty for commuters", "creating difficulty for commuters"),
        ("creating difficulty for commuters", "causing problems for commuters"),
        ("not been collected", "has not been cleared"),
        ("road surface is damaged", "the road surface is damaged"),
    ]

    transformed = text

    # Apply a small, deterministic number of substitutions.
    if variant_number % 2 == 0:
        for old, new in replacements[:8]:
            if old.lower() in transformed.lower():
                transformed = transformed.replace(old, new)

    # Controlled paraphrase wrapper.
    if variant_number % 3 == 0:
        return (
            f"Residents report that {transformed.rstrip('.')} "
            f"in this area."
        )

    if variant_number % 3 == 1:
        return (
            f"The reported {category.lower()} problem is that "
            f"{transformed.rstrip('.')}."
        )

    return transformed


def balanced_base_selection(
    df: pd.DataFrame,
    count: int,
) -> pd.DataFrame:
    """
    Deterministic round-robin selection across categories.
    This prevents the positive benchmark from being dominated by one
    complaint category.
    """
    categories = sorted(
        df["category"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .unique()
    )

    groups = {
        category: (
            df[
                df["category"]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
                == category
            ]
            .sort_values("complaint_id")
            .reset_index(drop=True)
        )
        for category in categories
    }

    selected_rows: list[pd.Series] = []
    cursor = {category: 0 for category in categories}

    while len(selected_rows) < count:
        added_this_round = False

        for category in categories:
            group = groups[category]
            position = cursor[category]

            if position >= len(group):
                continue

            selected_rows.append(group.iloc[position])
            cursor[category] += 1
            added_this_round = True

            if len(selected_rows) == count:
                break

        if not added_this_round:
            break

    if len(selected_rows) < count:
        raise ValueError(
            f"Could only select {len(selected_rows)} base complaints; "
            f"{count} required."
        )

    return pd.DataFrame(selected_rows)


def build_positive_pairs(
    bases: pd.DataFrame,
    rng: random.Random,
) -> list[dict]:
    rows: list[dict] = []

    for index, base in bases.reset_index(drop=True).iterrows():
        distance = rng.uniform(3.0, POSITIVE_MAX_DISTANCE_M)
        bearing = rng.uniform(0.0, 2.0 * math.pi)

        lat2, lon2 = offset_coordinate(
            float(base["latitude"]),
            float(base["longitude"]),
            distance,
            bearing,
        )

        time_shift_hours = rng.uniform(1.0, POSITIVE_MAX_TIME_HOURS)
        base_time = pd.Timestamp(base["created_at"])

        variant_text = make_synthetic_duplicate_text(
            normalize_text(base["description"]),
            normalize_text(base["category"]),
            index + 1,
        )

        rows.append(
            {
                "pair_id": f"DP{len(rows) + 1:04d}",
                "pair_type": "synthetic_positive",
                "complaint_id_1": int(base["complaint_id"]),
                "complaint_id_2": f"SYN_DUP_{int(base['complaint_id']):04d}",
                "category_1": normalize_text(base["category"]),
                "category_2": normalize_text(base["category"]),
                "description_1": normalize_text(base["description"]),
                "description_2": variant_text,
                "latitude_1": float(base["latitude"]),
                "longitude_1": float(base["longitude"]),
                "latitude_2": lat2,
                "longitude_2": lon2,
                "submitted_time_1": base_time.isoformat(),
                "submitted_time_2": (
                    base_time + pd.Timedelta(hours=time_shift_hours)
                ).isoformat(),
                "distance_meters": round(distance, 3),
                "time_difference_hours": round(
                    time_shift_hours,
                    3,
                ),
                "category_match": True,
                "actual_duplicate": 1,
                "label_source": "synthetic_by_construction",
                "label_notes": (
                    "Complaint 2 is a controlled synthetic variant "
                    "of complaint 1 representing the same benchmark "
                    "master issue."
                ),
            }
        )

    return rows


def build_negative_pairs(
    df: pd.DataFrame,
    count: int,
) -> list[dict]:
    """
    Build hard negative pairs from distinct source complaint instances.

    Preference:
      1. same category + <= 300 m
      2. different category + <= 300 m

    Because these are synthetic source complaint instances, the benchmark
    treats different source complaint IDs as different benchmark issues.
    """
    work = df.copy().reset_index(drop=True)

    rows: list[dict] = []
    used_pairs: set[tuple[int, int]] = set()

    same_category_candidates: list[dict] = []
    different_category_candidates: list[dict] = []

    for i in range(len(work)):
        a = work.iloc[i]

        for j in range(i + 1, len(work)):
            b = work.iloc[j]

            distance = haversine_meters(
                float(a["latitude"]),
                float(a["longitude"]),
                float(b["latitude"]),
                float(b["longitude"]),
            )

            if distance > NEGATIVE_MAX_DISTANCE_M:
                continue

            category_a = normalize_text(a["category"]).lower()
            category_b = normalize_text(b["category"]).lower()

            pair = {
                "a": a,
                "b": b,
                "distance": distance,
            }

            if category_a == category_b:
                same_category_candidates.append(pair)
            else:
                different_category_candidates.append(pair)

    # Deterministic selection.
    same_category_candidates.sort(
        key=lambda x: (
            x["distance"],
            int(x["a"]["complaint_id"]),
            int(x["b"]["complaint_id"]),
        )
    )

    different_category_candidates.sort(
        key=lambda x: (
            x["distance"],
            int(x["a"]["complaint_id"]),
            int(x["b"]["complaint_id"]),
        )
    )

    # Target at least 2/3 hard negatives from same-category nearby pairs
    # when available, with remaining slots from different categories.
    same_target = min(
        len(same_category_candidates),
        int(round(count * 2 / 3)),
    )

    selected_candidates = (
        same_category_candidates[:same_target]
        + different_category_candidates[
            : max(0, count - same_target)
        ]
    )

    # If still short, fill from the remaining candidate pool.
    if len(selected_candidates) < count:
        remaining = (
            same_category_candidates[same_target:]
            + different_category_candidates
        )

        for candidate in remaining:
            if len(selected_candidates) >= count:
                break

            key = (
                int(candidate["a"]["complaint_id"]),
                int(candidate["b"]["complaint_id"]),
            )

            if key in used_pairs:
                continue

            selected_candidates.append(candidate)

    for candidate in selected_candidates[:count]:
        a = candidate["a"]
        b = candidate["b"]

        key = (
            int(a["complaint_id"]),
            int(b["complaint_id"]),
        )

        if key in used_pairs:
            continue

        used_pairs.add(key)

        time_a = pd.Timestamp(a["created_at"])
        time_b = pd.Timestamp(b["created_at"])

        rows.append(
            {
                "pair_id": f"DP{POSITIVE_PAIRS + len(rows) + 1:04d}",
                "pair_type": "synthetic_negative",
                "complaint_id_1": int(a["complaint_id"]),
                "complaint_id_2": int(b["complaint_id"]),
                "category_1": normalize_text(a["category"]),
                "category_2": normalize_text(b["category"]),
                "description_1": normalize_text(a["description"]),
                "description_2": normalize_text(b["description"]),
                "latitude_1": float(a["latitude"]),
                "longitude_1": float(a["longitude"]),
                "latitude_2": float(b["latitude"]),
                "longitude_2": float(b["longitude"]),
                "submitted_time_1": time_a.isoformat(),
                "submitted_time_2": time_b.isoformat(),
                "distance_meters": round(
                    candidate["distance"],
                    3,
                ),
                "time_difference_hours": round(
                    abs((time_a - time_b).total_seconds()) / 3600.0,
                    3,
                ),
                "category_match": (
                    normalize_text(a["category"]).lower()
                    == normalize_text(b["category"]).lower()
                ),
                "actual_duplicate": 0,
                "label_source": "synthetic_by_construction",
                "label_notes": (
                    "Complaints 1 and 2 are independent synthetic "
                    "source complaint instances; they are treated as "
                    "different benchmark issues even when category and "
                    "location are similar."
                ),
            }
        )

    if len(rows) < count:
        raise ValueError(
            f"Only {len(rows)} negative pairs could be built; "
            f"{count} required."
        )

    return rows[:count]


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — SYNTHETIC DUPLICATE BENCHMARK")
    print("=" * 78)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Step 8 complaint dataset not found:\n{INPUT_FILE}"
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

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    df["complaint_id"] = pd.to_numeric(
        df["complaint_id"],
        errors="raise",
    )

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce",
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce",
    )

    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce",
        utc=True,
    )

    df["category"] = (
        df["category"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["description"] = (
        df["description"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    before = len(df)

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "created_at",
        ]
    ).copy()

    df = df[
        (df["category"] != "")
        & (df["description"] != "")
    ].copy()

    df = (
        df.sort_values("complaint_id")
        .drop_duplicates("complaint_id")
        .reset_index(drop=True)
    )

    print(f"Input complaints loaded     : {before}")
    print(f"Usable source complaints     : {len(df)}")

    if len(df) < 150:
        raise ValueError(
            "At least 150 usable source complaints are required."
        )

    # Select 150 source complaints in a category-balanced deterministic way.
    bases = balanced_base_selection(
        df,
        POSITIVE_PAIRS,
    )

    print(f"Positive base complaints     : {len(bases)}")

    rng = random.Random(RANDOM_SEED)

    positive_rows = build_positive_pairs(
        bases,
        rng,
    )

    negative_rows = build_negative_pairs(
        df,
        NEGATIVE_PAIRS,
    )

    benchmark = pd.DataFrame(
        positive_rows + negative_rows
    )

    # Stable final ordering.
    benchmark = benchmark.sort_values(
        "pair_id"
    ).reset_index(drop=True)

    benchmark["benchmark_order"] = range(
        1,
        len(benchmark) + 1,
    )

    # Reorder useful fields first.
    columns = [
        "benchmark_order",
        "pair_id",
        "pair_type",
        "complaint_id_1",
        "complaint_id_2",
        "category_1",
        "category_2",
        "category_match",
        "description_1",
        "description_2",
        "latitude_1",
        "longitude_1",
        "latitude_2",
        "longitude_2",
        "submitted_time_1",
        "submitted_time_2",
        "distance_meters",
        "time_difference_hours",
        "actual_duplicate",
        "label_source",
        "label_notes",
    ]

    benchmark = benchmark[columns]

    benchmark.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # Summary.
    benchmark["distance_bucket"] = pd.cut(
        benchmark["distance_meters"],
        bins=[-0.001, 50, 100, 150, 200, 250, 300, float("inf")],
        labels=[
            "0-50m",
            "50-100m",
            "100-150m",
            "150-200m",
            "200-250m",
            "250-300m",
            ">300m",
        ],
        include_lowest=True,
        right=True,
    )

    benchmark["time_bucket"] = pd.cut(
        benchmark["time_difference_hours"],
        bins=[
            -0.001,
            24,
            72,
            168,
            720,
            1440,
            float("inf"),
        ],
        labels=[
            "0-1d",
            "1-3d",
            "3-7d",
            "7-30d",
            "30-60d",
            ">60d",
        ],
        include_lowest=True,
        right=True,
    )

    summary_rows = []

    for pair_type, group in benchmark.groupby(
        "pair_type",
        sort=True,
    ):
        summary_rows.append(
            {
                "pair_type": pair_type,
                "pair_count": len(group),
                "mean_distance_m": round(
                    group["distance_meters"].mean(),
                    3,
                ),
                "median_distance_m": round(
                    group["distance_meters"].median(),
                    3,
                ),
                "max_distance_m": round(
                    group["distance_meters"].max(),
                    3,
                ),
                "mean_time_difference_h": round(
                    group["time_difference_hours"].mean(),
                    3,
                ),
                "median_time_difference_h": round(
                    group["time_difference_hours"].median(),
                    3,
                ),
                "max_time_difference_h": round(
                    group["time_difference_hours"].max(),
                    3,
                ),
                "same_category_count": int(
                    group["category_match"].astype(bool).sum()
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    config = {
        "version": "1.0",
        "random_seed": RANDOM_SEED,
        "total_pairs": TOTAL_PAIRS,
        "positive_pairs": POSITIVE_PAIRS,
        "negative_pairs": NEGATIVE_PAIRS,
        "positive_construction": {
            "definition": (
                "Complaint 2 is a controlled synthetic variant "
                "of Complaint 1 and therefore represents the same "
                "benchmark master issue."
            ),
            "max_distance_m": POSITIVE_MAX_DISTANCE_M,
            "max_time_difference_hours": POSITIVE_MAX_TIME_HOURS,
        },
        "negative_construction": {
            "definition": (
                "Complaint pairs come from distinct synthetic source "
                "complaint instances and are therefore different "
                "benchmark issues by construction."
            ),
            "max_distance_m": NEGATIVE_MAX_DISTANCE_M,
        },
        "label_source": "synthetic_by_construction",
        "official_tdmc_duplicate_labels": False,
        "note": (
            "This benchmark is for methodology/model evaluation. "
            "It is not official TDMC ground truth and must not be "
            "reported as real municipal duplicate-detection accuracy."
        ),
    }

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Final validation checks.
    duplicate_pair_ids = int(
        benchmark["pair_id"].duplicated().sum()
    )

    positive_count = int(
        (benchmark["actual_duplicate"] == 1).sum()
    )

    negative_count = int(
        (benchmark["actual_duplicate"] == 0).sum()
    )

    missing_labels = int(
        benchmark["actual_duplicate"].isna().sum()
    )

    distances_over_limit = int(
        (
            benchmark.loc[
                benchmark["pair_type"] == "synthetic_positive",
                "distance_meters",
            ]
            > POSITIVE_MAX_DISTANCE_M
        ).sum()
    )

    print()
    print("BENCHMARK SUMMARY")
    print("-" * 78)
    print(f"Total benchmark pairs       : {len(benchmark)}")
    print(f"Known duplicate pairs      : {positive_count}")
    print(f"Known non-duplicate pairs  : {negative_count}")
    print(f"Missing labels             : {missing_labels}")
    print(f"Duplicate pair IDs         : {duplicate_pair_ids}")
    print(
        "Positive pairs > 80 m      : "
        f"{distances_over_limit}"
    )

    print()
    print(
        "Pair type distribution:"
    )
    print(
        benchmark["pair_type"]
        .value_counts()
        .to_string()
    )

    print()
    print("Distance buckets:")
    print(
        benchmark["distance_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print("Time-difference buckets:")
    print(
        benchmark["time_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print(f"Benchmark output            : {OUTPUT_FILE}")
    print(f"Benchmark config            : {CONFIG_FILE}")
    print(f"Benchmark summary           : {SUMMARY_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 78)
    print(
        "actual_duplicate labels are known by synthetic construction, "
        "not from official TDMC duplicate annotations."
    )
    print(
        "These labels are suitable for a controlled prototype benchmark "
        "and threshold/evaluation experiments."
    )
    print(
        "They must not be presented as real municipal ground truth."
    )

    print()
    print("=" * 78)
    print("SYNTHETIC DUPLICATE BENCHMARK CREATED")
    print("=" * 78)


if __name__ == "__main__":
    main()
