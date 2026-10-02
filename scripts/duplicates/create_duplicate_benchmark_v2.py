from __future__ import annotations

import json
import math
import random
from collections import defaultdict
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
OUTPUT_FILE = OUTPUT_DIR / "duplicate_benchmark_v2.csv"
SUMMARY_FILE = OUTPUT_DIR / "duplicate_benchmark_v2_summary.csv"
CONFIG_FILE = OUTPUT_DIR / "duplicate_benchmark_v2_config.json"

RANDOM_SEED = 42

TOTAL_PAIRS = 300
POSITIVE_PAIRS = 150
NEGATIVE_PAIRS = 150

SPATIAL_RADIUS_M = 300

# Distance strata used by both positive and negative examples.
DISTANCE_BINS = [
    (0.0, 50.0, "0-50m"),
    (50.0, 100.0, "50-100m"),
    (100.0, 150.0, "100-150m"),
    (150.0, 200.0, "150-200m"),
    (200.0, 250.0, "200-250m"),
    (250.0, 299.0, "250-300m"),
]

# Recent-time strata used by both positive and negative examples.
TIME_BINS = [
    (0.25, 72.0, "0-3d"),
    (72.01, 168.0, "3-7d"),
    (168.01, 720.0, "7-30d"),
    (720.01, 1440.0, "30-60d"),
    (1440.01, 2160.0, "60-90d"),
]

POSITIVE_PER_STRATUM = 5

# Negative benchmark composition.
NEGATIVE_SAME_CATEGORY = 100
NEGATIVE_DIFFERENT_CATEGORY = 50


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split())


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
        * math.atan2(
            math.sqrt(a),
            math.sqrt(max(0.0, 1.0 - a)),
        )
    )


def offset_coordinate(
    lat: float,
    lon: float,
    distance_m: float,
    bearing_rad: float,
) -> tuple[float, float]:
    """Create a synthetic coordinate at a controlled distance."""
    earth_radius_m = 6_371_000.0
    lat_rad = math.radians(lat)

    d_lat = (
        distance_m * math.cos(bearing_rad) / earth_radius_m
    )

    d_lon = (
        distance_m
        * math.sin(bearing_rad)
        / (
            earth_radius_m
            * max(abs(math.cos(lat_rad)), 1e-8)
        )
    )

    return (
        lat + math.degrees(d_lat),
        lon + math.degrees(d_lon),
    )


def paraphrase(text: str, category: str, variant: int) -> str:
    """Create controlled semantic variants without changing the issue."""
    text = normalize_text(text)
    category = normalize_text(category).lower()

    replacements = [
        ("is not functioning", "is not working"),
        ("is not functioning.", "is not working."),
        ("is not working", "has stopped working"),
        ("has accumulated", "has built up"),
        ("has been dumped", "has been left"),
        ("has blocked", "has caused a blockage in"),
        ("is blocked", "has become blocked"),
        ("is not flowing", "is not draining properly"),
        ("requires cleaning", "needs cleaning"),
        ("requires repair", "needs repair"),
        ("needs repair", "requires repair"),
        ("causing difficulty for commuters", "creating difficulty for commuters"),
        ("creating difficulty for commuters", "causing problems for commuters"),
        ("not been collected", "has not been cleared"),
        ("road surface is damaged", "the road surface has been damaged"),
    ]

    result = text

    # Apply deterministic substitutions.
    if variant % 2 == 0:
        for old, new in replacements:
            if old.lower() in result.lower():
                result = result.replace(old, new)
                break

    templates = [
        f"Residents report a {category} problem: {result.rstrip('.')}.",
        f"The reported {category} issue is that {result.rstrip('.')}.",
        f"A civic complaint has been raised because {result.rstrip('.')}.",
        f"People in the area have reported that {result.rstrip('.')}.",
    ]

    return templates[variant % len(templates)]


def load_source_data() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Canonical Step 8 complaint dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = [
        "complaint_id",
        "category",
        "description",
        "latitude",
        "longitude",
        "created_at",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    df["complaint_id"] = pd.to_numeric(
        df["complaint_id"],
        errors="coerce",
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

    df = df.dropna(
        subset=[
            "complaint_id",
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

    if len(df) < 150:
        raise ValueError(
            f"Only {len(df)} usable complaints available; 150 are required."
        )

    return df


def balanced_base_selection(
    df: pd.DataFrame,
    count: int,
) -> pd.DataFrame:
    """Select source complaints round-robin across categories."""
    groups = defaultdict(list)

    for _, row in df.iterrows():
        category = normalize_text(row["category"])
        groups[category].append(row)

    categories = sorted(groups)

    for category in categories:
        groups[category] = sorted(
            groups[category],
            key=lambda row: int(row["complaint_id"]),
        )

    selected = []
    position = 0

    while len(selected) < count:
        added = False

        for category in categories:
            group = groups[category]

            if position < len(group):
                selected.append(group[position])
                added = True

                if len(selected) == count:
                    break

        if not added:
            break

        position += 1

    if len(selected) != count:
        raise ValueError(
            f"Could not select {count} balanced base complaints."
        )

    return pd.DataFrame(selected).reset_index(drop=True)


def choose_distance_and_time(
    index: int,
    rng: random.Random,
) -> tuple[float, str, float, str]:
    distance_index = (index // POSITIVE_PER_STRATUM) % len(DISTANCE_BINS)
    time_index = (
        (index // POSITIVE_PER_STRATUM)
        // len(DISTANCE_BINS)
    ) % len(TIME_BINS)

    d_low, d_high, d_label = DISTANCE_BINS[distance_index]
    t_low, t_high, t_label = TIME_BINS[time_index]

    distance = rng.uniform(
        max(1.0, d_low),
        d_high,
    )

    time_hours = rng.uniform(
        t_low,
        t_high,
    )

    return (
        distance,
        d_label,
        time_hours,
        t_label,
    )


def build_positive_pairs(
    bases: pd.DataFrame,
    rng: random.Random,
) -> list[dict]:
    rows = []

    for index, base in bases.iterrows():
        distance, distance_bucket, time_hours, time_bucket = (
            choose_distance_and_time(index, rng)
        )

        bearing = rng.uniform(
            0.0,
            2.0 * math.pi,
        )

        lat2, lon2 = offset_coordinate(
            float(base["latitude"]),
            float(base["longitude"]),
            distance,
            bearing,
        )

        time1 = pd.Timestamp(base["created_at"])
        time2 = time1 + pd.Timedelta(hours=time_hours)

        description1 = normalize_text(base["description"])
        description2 = paraphrase(
            description1,
            normalize_text(base["category"]),
            index,
        )

        rows.append(
            {
                "pair_id": f"V2P{index + 1:04d}",
                "pair_type": "synthetic_positive",
                "complaint_id_1": int(base["complaint_id"]),
                "complaint_id_2": f"SYN_DUP_{int(base['complaint_id']):04d}",
                "category_1": normalize_text(base["category"]),
                "category_2": normalize_text(base["category"]),
                "category_match": True,
                "description_1": description1,
                "description_2": description2,
                "latitude_1": float(base["latitude"]),
                "longitude_1": float(base["longitude"]),
                "latitude_2": lat2,
                "longitude_2": lon2,
                "submitted_time_1": time1.isoformat(),
                "submitted_time_2": time2.isoformat(),
                "distance_meters": round(distance, 3),
                "distance_bucket": distance_bucket,
                "time_difference_hours": round(
                    time_hours,
                    3,
                ),
                "time_bucket": time_bucket,
                "actual_duplicate": 1,
                "label_source": "synthetic_by_construction",
                "label_notes": (
                    "Complaint 2 is a controlled semantic variant of "
                    "Complaint 1 and represents the same benchmark issue."
                ),
            }
        )

    return rows


def make_negative_candidates(
    df: pd.DataFrame,
    same_category: bool,
) -> list[tuple[int, int]]:
    candidates = []

    for i in range(len(df)):
        a = df.iloc[i]
        category_a = normalize_text(a["category"]).lower()

        for j in range(i + 1, len(df)):
            b = df.iloc[j]
            category_b = normalize_text(b["category"]).lower()

            if same_category and category_a != category_b:
                continue

            if not same_category and category_a == category_b:
                continue

            # Avoid exact text duplicates in negative construction.
            text_a = normalize_text(a["description"]).lower()
            text_b = normalize_text(b["description"]).lower()

            if text_a == text_b:
                continue

            candidates.append(
                (
                    int(a["complaint_id"]),
                    int(b["complaint_id"]),
                )
            )

    return candidates


def select_negative_base_pairs(
    df: pd.DataFrame,
    count: int,
    same_category: bool,
) -> list[tuple[int, int]]:
    candidates = make_negative_candidates(
        df,
        same_category,
    )

    if len(candidates) < count:
        raise ValueError(
            f"Only {len(candidates)} negative candidates available "
            f"for same_category={same_category}; {count} required."
        )

    # Deterministic spread across the candidate list.
    step = max(
        1,
        len(candidates) // count,
    )

    selected = []
    cursor = 0
    seen = set()

    while len(selected) < count and cursor < len(candidates) * 2:
        pair = candidates[cursor % len(candidates)]

        if pair not in seen:
            selected.append(pair)
            seen.add(pair)

        cursor += step

    # Safe fallback.
    if len(selected) < count:
        for pair in candidates:
            if pair in seen:
                continue

            selected.append(pair)
            seen.add(pair)

            if len(selected) == count:
                break

    if len(selected) != count:
        raise ValueError(
            "Could not construct the requested number of negative pairs."
        )

    return selected


def build_negative_pairs(
    df: pd.DataFrame,
    count: int,
    same_category: bool,
    start_index: int,
    rng: random.Random,
) -> list[dict]:
    by_id = {
        int(row["complaint_id"]): row
        for _, row in df.iterrows()
    }

    base_pairs = select_negative_base_pairs(
        df,
        count,
        same_category,
    )

    rows = []

    for local_index, (id1, id2) in enumerate(base_pairs):
        global_index = start_index + local_index

        distance, distance_bucket, time_hours, time_bucket = (
            choose_distance_and_time(
                global_index,
                rng,
            )
        )

        a = by_id[id1]
        b = by_id[id2]

        bearing = rng.uniform(
            0.0,
            2.0 * math.pi,
        )

        lat2, lon2 = offset_coordinate(
            float(a["latitude"]),
            float(a["longitude"]),
            distance,
            bearing,
        )

        time1 = pd.Timestamp(a["created_at"])
        time2 = time1 + pd.Timedelta(hours=time_hours)

        rows.append(
            {
                "pair_id": f"V2N{start_index + local_index + 1:04d}",
                "pair_type": (
                    "synthetic_negative_same_category"
                    if same_category
                    else "synthetic_negative_different_category"
                ),
                "complaint_id_1": id1,
                "complaint_id_2": id2,
                "category_1": normalize_text(a["category"]),
                "category_2": normalize_text(b["category"]),
                "category_match": (
                    normalize_text(a["category"]).lower()
                    == normalize_text(b["category"]).lower()
                ),
                "description_1": normalize_text(a["description"]),
                "description_2": normalize_text(b["description"]),
                "latitude_1": float(a["latitude"]),
                "longitude_1": float(a["longitude"]),
                "latitude_2": lat2,
                "longitude_2": lon2,
                "submitted_time_1": time1.isoformat(),
                "submitted_time_2": time2.isoformat(),
                "distance_meters": round(
                    distance,
                    3,
                ),
                "distance_bucket": distance_bucket,
                "time_difference_hours": round(
                    time_hours,
                    3,
                ),
                "time_bucket": time_bucket,
                "actual_duplicate": 0,
                "label_source": "synthetic_by_construction",
                "label_notes": (
                    "Complaints 1 and 2 come from distinct source "
                    "complaint instances and represent different "
                    "benchmark issues. The pair is intentionally kept "
                    "within the candidate search space to create a "
                    "hard negative."
                ),
            }
        )

    return rows


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — DUPLICATE BENCHMARK V2")
    print("=" * 78)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rng = random.Random(RANDOM_SEED)

    df = load_source_data()

    print(f"Canonical Step 8 rows loaded : {len(df)}")

    bases = balanced_base_selection(
        df,
        POSITIVE_PAIRS,
    )

    positive_rows = build_positive_pairs(
        bases,
        rng,
    )

    negative_same_rows = build_negative_pairs(
        df,
        NEGATIVE_SAME_CATEGORY,
        same_category=True,
        start_index=POSITIVE_PAIRS,
        rng=rng,
    )

    negative_diff_rows = build_negative_pairs(
        df,
        NEGATIVE_DIFFERENT_CATEGORY,
        same_category=False,
        start_index=(
            POSITIVE_PAIRS
            + NEGATIVE_SAME_CATEGORY
        ),
        rng=rng,
    )

    benchmark = pd.DataFrame(
        positive_rows
        + negative_same_rows
        + negative_diff_rows
    )

    if len(benchmark) != TOTAL_PAIRS:
        raise AssertionError(
            f"Expected {TOTAL_PAIRS} rows, got {len(benchmark)}."
        )

    benchmark["benchmark_order"] = range(
        1,
        len(benchmark) + 1,
    )

    benchmark = benchmark[
        [
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
            "distance_bucket",
            "time_difference_hours",
            "time_bucket",
            "actual_duplicate",
            "label_source",
            "label_notes",
        ]
    ]

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    assert (
        benchmark["actual_duplicate"].value_counts().to_dict()
        == {1: 150, 0: 150}
    )

    duplicate_pair_ids = int(
        benchmark["pair_id"].duplicated().sum()
    )

    missing_labels = int(
        benchmark["actual_duplicate"].isna().sum()
    )

    invalid_distance = int(
        (
            (benchmark["distance_meters"] <= 0)
            | (benchmark["distance_meters"] > SPATIAL_RADIUS_M)
        ).sum()
    )

    invalid_time = int(
        (
            (benchmark["time_difference_hours"] <= 0)
            | (benchmark["time_difference_hours"] > 2160)
        ).sum()
    )

    positive_distance_outside = int(
        (
            benchmark.loc[
                benchmark["actual_duplicate"] == 1,
                "distance_meters",
            ]
            > SPATIAL_RADIUS_M
        ).sum()
    )

    positive_time_outside = int(
        (
            benchmark.loc[
                benchmark["actual_duplicate"] == 1,
                "time_difference_hours",
            ]
            > 2160
        ).sum()
    )

    same_category_negative = int(
        (
            (benchmark["actual_duplicate"] == 0)
            & (benchmark["category_match"].astype(bool))
        ).sum()
    )

    different_category_negative = int(
        (
            (benchmark["actual_duplicate"] == 0)
            & (~benchmark["category_match"].astype(bool))
        ).sum()
    )

    if (
        duplicate_pair_ids
        or missing_labels
        or invalid_distance
        or invalid_time
        or positive_distance_outside
        or positive_time_outside
    ):
        print()
        print("VALIDATION FAILURE DETAILS")
        print("-" * 78)
        print(f"Duplicate pair IDs       : {duplicate_pair_ids}")
        print(f"Missing labels           : {missing_labels}")
        print(f"Invalid distances        : {invalid_distance}")
        print(f"Invalid time differences : {invalid_time}")
        print(f"Positive distance >300m  : {positive_distance_outside}")
        print(f"Positive time >90 days   : {positive_time_outside}")
        raise AssertionError(
            "Benchmark validation failed. See details above."
        )

    # ------------------------------------------------------------
    # Save
    # ------------------------------------------------------------

    benchmark.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
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
                "min_distance_m": round(
                    group["distance_meters"].min(),
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
                "min_time_difference_h": round(
                    group["time_difference_hours"].min(),
                    3,
                ),
                "max_time_difference_h": round(
                    group["time_difference_hours"].max(),
                    3,
                ),
                "same_category_count": int(
                    group["category_match"].astype(bool).sum()
                ),
                "duplicate_label": int(
                    group["actual_duplicate"].iloc[0]
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
        "version": "2.0",
        "random_seed": RANDOM_SEED,
        "total_pairs": TOTAL_PAIRS,
        "positive_pairs": POSITIVE_PAIRS,
        "negative_pairs": NEGATIVE_PAIRS,
        "negative_same_category_pairs": NEGATIVE_SAME_CATEGORY,
        "negative_different_category_pairs": NEGATIVE_DIFFERENT_CATEGORY,
        "spatial_candidate_radius_m": SPATIAL_RADIUS_M,
        "distance_strata": [
            {
                "min_m": low,
                "max_m": high,
                "label": label,
            }
            for low, high, label in DISTANCE_BINS
        ],
        "time_strata_hours": [
            {
                "min_h": low,
                "max_h": high,
                "label": label,
            }
            for low, high, label in TIME_BINS
        ],
        "positive_definition": (
            "Controlled semantic variant of one source complaint, "
            "therefore same benchmark issue."
        ),
        "negative_definition": (
            "Two distinct source complaints, intentionally placed "
            "inside the candidate-search space, therefore different "
            "benchmark issues by construction."
        ),
        "label_source": "synthetic_by_construction",
        "official_tdmc_duplicate_labels": False,
        "note": (
            "Benchmark V2 is a controlled prototype evaluation set. "
            "It is not official TDMC ground truth and must not be "
            "reported as real municipal accuracy."
        ),
    }

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Print complete summary
    # ------------------------------------------------------------

    print()
    print("VALIDATION")
    print("-" * 78)
    print(f"Total rows                  : {len(benchmark)}")
    print(
        f"Positive labels (1)         : "
        f"{int((benchmark['actual_duplicate'] == 1).sum())}"
    )
    print(
        f"Negative labels (0)         : "
        f"{int((benchmark['actual_duplicate'] == 0).sum())}"
    )
    print(f"Duplicate pair IDs          : {duplicate_pair_ids}")
    print(f"Missing labels              : {missing_labels}")
    print(f"Invalid distances           : {invalid_distance}")
    print(f"Invalid time differences    : {invalid_time}")
    print(
        f"Positive distance >300m     : "
        f"{positive_distance_outside}"
    )
    print(
        f"Positive time >90 days      : "
        f"{positive_time_outside}"
    )

    print()
    print("NEGATIVE PAIR COMPOSITION")
    print("-" * 78)
    print(
        f"Same-category negatives     : "
        f"{same_category_negative}"
    )
    print(
        f"Different-category negatives: "
        f"{different_category_negative}"
    )

    print()
    print("PAIR-TYPE SUMMARY")
    print("-" * 78)
    print(summary.to_string(index=False))

    print()
    print("DISTANCE STRATA")
    print("-" * 78)
    print(
        benchmark["distance_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print("TIME STRATA")
    print("-" * 78)
    print(
        benchmark["time_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print(f"Benchmark output             : {OUTPUT_FILE}")
    print(f"Summary output               : {SUMMARY_FILE}")
    print(f"Config output                : {CONFIG_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 78)
    print(
        "Benchmark V2 uses synthetic labels by construction."
    )
    print(
        "It is designed to prevent a trivial evaluation that separates "
        "duplicates from non-duplicates only by distance or recency."
    )
    print(
        "It must not be presented as official TDMC duplicate ground truth."
    )

    print()
    print("=" * 78)
    print("DUPLICATE BENCHMARK V2 CREATED AND VALIDATED")
    print("=" * 78)


if __name__ == "__main__":
    main()
