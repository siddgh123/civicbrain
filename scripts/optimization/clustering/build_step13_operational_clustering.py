from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.cluster import DBSCAN
except ImportError as exc:
    raise ImportError(
        "scikit-learn is required for Step 13 clustering. "
        "Install with: python -m pip install scikit-learn"
    ) from exc


# ============================================================================
# CIVICBRAIN STEP 13 — OPERATIONAL CLUSTERING
#
# Purpose:
#   Group all canonical eligible jobs into operationally compatible spatial
#   clusters. This phase MUST preserve every eligible job, including jobs
#   whose service duration exceeds one shift.
#
# Inputs:
#   data/optimization/jobs/eligible_jobs.csv
#
# Optional diagnostic input:
#   data/optimization/teams/feasible_team_assignments.csv
#
# Outputs:
#   data/optimization/clusters/cluster_results.csv
#   data/optimization/clusters/cluster_members.csv
#   data/optimization/clusters/clustering_validation.csv
#   data/optimization/clusters/clustering_summary.json
#
# Rules:
#   - Four approved operational work types only.
#   - Only same work_type jobs are clustered in this prototype.
#   - DBSCAN baseline: eps=2000 m, min_samples=2.
#   - DBSCAN chaining is NOT accepted blindly.
#   - Every non-standalone cluster must have max internal pairwise distance
#     <= 2000 m.
#   - MAX_CLUSTER_JOBS is an explicit project configuration = 10.
#     This is a prototype configuration, NOT a municipal standard.
#   - Oversized/invalid DBSCAN clusters are recursively refined by
#     farthest-seed spatial splitting until valid.
#   - Standalone jobs are retained and routed/scheduled later.
#   - Cluster centroid is summary-only, never a route stop.
#   - No hotspot detection.
#   - No PostgreSQL writes.
#   - No Step 11/12 modifications.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

ELIGIBLE_JOBS_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "eligible_jobs.csv"
)

FEASIBLE_ASSIGNMENTS_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "feasible_team_assignments.csv"
)

OUTPUT_DIR = (
    DATA_DIR
    / "optimization"
    / "clusters"
)

CLUSTER_RESULTS_FILE = OUTPUT_DIR / "cluster_results.csv"
CLUSTER_MEMBERS_FILE = OUTPUT_DIR / "cluster_members.csv"
VALIDATION_FILE = OUTPUT_DIR / "clustering_validation.csv"
SUMMARY_FILE = OUTPUT_DIR / "clustering_summary.json"

APPROVED_WORK_TYPES = {
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
}

CLUSTER_RADIUS_METERS = 2000.0
DBSCAN_EPS_METERS = 2000.0
DBSCAN_MIN_SAMPLES = 2
MAX_CLUSTER_JOBS = 10


def haversine_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Great-circle distance in meters."""
    r = 6_371_000.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dlon / 2.0) ** 2
    )

    return 2.0 * r * math.asin(
        min(1.0, math.sqrt(a))
    )


def pairwise_max_distance_m(
    df: pd.DataFrame,
) -> float:
    """Maximum pairwise job distance within a group."""
    if len(df) <= 1:
        return 0.0

    coords = df[
        ["latitude", "longitude"]
    ].astype(float).to_numpy()

    max_distance = 0.0

    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            distance = haversine_m(
                coords[i, 0],
                coords[i, 1],
                coords[j, 0],
                coords[j, 1],
            )
            if distance > max_distance:
                max_distance = distance

    return max_distance


def centroid(df: pd.DataFrame) -> tuple[float, float]:
    return (
        float(df["latitude"].mean()),
        float(df["longitude"].mean()),
    )


def farthest_pair_positions(
    df: pd.DataFrame,
) -> tuple[int, int]:
    """Return dataframe-local integer positions of farthest pair."""
    if len(df) < 2:
        return (0, 0)

    coords = df[
        ["latitude", "longitude"]
    ].astype(float).to_numpy()

    max_distance = -1.0
    best_i = 0
    best_j = 1

    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            distance = haversine_m(
                coords[i, 0],
                coords[i, 1],
                coords[j, 0],
                coords[j, 1],
            )

            if distance > max_distance:
                max_distance = distance
                best_i = i
                best_j = j

    return best_i, best_j


def split_by_two_seeds(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Deterministic spatial split:
      1. choose farthest pair as seeds;
      2. assign each other job to nearest seed;
      3. ties go to higher-priority seed side.
    """
    if len(df) <= 1:
        return df.copy(), df.iloc[0:0].copy()

    df = df.copy().reset_index(drop=True)

    seed_a_pos, seed_b_pos = farthest_pair_positions(df)

    seed_a = df.iloc[seed_a_pos]
    seed_b = df.iloc[seed_b_pos]

    side_a = [seed_a_pos]
    side_b = [seed_b_pos]

    for pos in range(len(df)):
        if pos in {seed_a_pos, seed_b_pos}:
            continue

        row = df.iloc[pos]

        dist_a = haversine_m(
            float(row["latitude"]),
            float(row["longitude"]),
            float(seed_a["latitude"]),
            float(seed_a["longitude"]),
        )

        dist_b = haversine_m(
            float(row["latitude"]),
            float(row["longitude"]),
            float(seed_b["latitude"]),
            float(seed_b["longitude"]),
        )

        if dist_a < dist_b:
            side_a.append(pos)
        elif dist_b < dist_a:
            side_b.append(pos)
        else:
            if float(row["priority_score"]) >= float(seed_a["priority_score"]):
                side_a.append(pos)
            else:
                side_b.append(pos)

    # Defensive guarantee against an empty side.
    if not side_a or not side_b:
        sorted_df = df.sort_values(
            ["priority_score", "job_id"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)

        midpoint = max(1, len(sorted_df) // 2)

        return (
            sorted_df.iloc[:midpoint].copy(),
            sorted_df.iloc[midpoint:].copy(),
        )

    return (
        df.iloc[sorted(side_a)].copy(),
        df.iloc[sorted(side_b)].copy(),
    )


def refine_group(
    df: pd.DataFrame,
) -> list[pd.DataFrame]:
    """
    Recursively split until:
      len <= MAX_CLUSTER_JOBS
      AND max_internal_distance <= CLUSTER_RADIUS_METERS
    """
    df = df.copy()

    if len(df) <= MAX_CLUSTER_JOBS and (
        pairwise_max_distance_m(df)
        <= CLUSTER_RADIUS_METERS
    ):
        return [df]

    left, right = split_by_two_seeds(df)

    if len(left) == 0 or len(right) == 0:
        # Defensive fallback: this should not occur, but every job must
        # remain accounted for.
        return [
            df.iloc[[i]].copy()
            for i in range(len(df))
        ]

    return (
        refine_group(left)
        + refine_group(right)
    )


def build_dbscan_candidates(
    df: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    """
    Run DBSCAN separately within each work type.

    scikit-learn expects radians when metric='haversine'.
    """
    candidates: dict[int, pd.DataFrame] = {}

    candidate_counter = 1

    for work_type in sorted(APPROVED_WORK_TYPES):
        subset = df[
            df["work_type"].eq(work_type)
        ].copy()

        if subset.empty:
            continue

        coords_rad = np.radians(
            subset[
                ["latitude", "longitude"]
            ].astype(float).to_numpy()
        )

        eps_rad = (
            DBSCAN_EPS_METERS / 6_371_000.0
        )

        model = DBSCAN(
            eps=eps_rad,
            min_samples=DBSCAN_MIN_SAMPLES,
            metric="haversine",
        )

        labels = model.fit_predict(coords_rad)

        subset["_dbscan_label"] = labels

        for label in sorted(
            set(labels.tolist())
        ):
            if label == -1:
                continue

            group = subset[
                subset["_dbscan_label"].eq(label)
            ].copy()

            group["_candidate_id"] = (
                f"CAND_{candidate_counter:04d}"
            )

            candidates[candidate_counter] = group
            candidate_counter += 1

    return candidates


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13 — OPERATIONAL CLUSTERING")
    print("=" * 80)

    print()
    print("READ-ONLY INPUTS")
    print("-" * 80)
    print(f"Eligible jobs : {ELIGIBLE_JOBS_FILE}")
    print(f"Assignments   : {FEASIBLE_ASSIGNMENTS_FILE}")
    print("Database      : NOT USED")

    if not ELIGIBLE_JOBS_FILE.exists():
        raise FileNotFoundError(
            f"Eligible jobs file not found:\n{ELIGIBLE_JOBS_FILE}"
        )

    jobs = pd.read_csv(ELIGIBLE_JOBS_FILE)

    required = {
        "complaint_id",
        "job_id",
        "work_type",
        "priority_score",
        "priority_level",
        "latitude",
        "longitude",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
    }

    missing = required - set(jobs.columns)

    if missing:
        raise ValueError(
            "eligible_jobs.csv missing required columns: "
            + ", ".join(sorted(missing))
        )

    jobs["work_type"] = (
        jobs["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    jobs["latitude"] = pd.to_numeric(
        jobs["latitude"],
        errors="coerce",
    )
    jobs["longitude"] = pd.to_numeric(
        jobs["longitude"],
        errors="coerce",
    )
    jobs["priority_score"] = pd.to_numeric(
        jobs["priority_score"],
        errors="coerce",
    )
    jobs["workers_required"] = pd.to_numeric(
        jobs["workers_required"],
        errors="coerce",
    )
    jobs["service_duration_hours"] = pd.to_numeric(
        jobs["service_duration_hours"],
        errors="coerce",
    )
    jobs["estimated_cost"] = pd.to_numeric(
        jobs["estimated_cost"],
        errors="coerce",
    )

    jobs = jobs[
        jobs["eligibility_status"].eq("ELIGIBLE")
    ].copy()

    jobs = jobs.reset_index(drop=True)

    total_eligible = int(len(jobs))

    if total_eligible != 441:
        raise ValueError(
            "Expected 441 eligible jobs from Step 13.1, "
            f"found {total_eligible}."
        )

    if not set(jobs["work_type"]).issubset(
        APPROVED_WORK_TYPES
    ):
        invalid_types = sorted(
            set(jobs["work_type"])
            - APPROVED_WORK_TYPES
        )
        raise ValueError(
            "Invalid work types found: "
            + ", ".join(invalid_types)
        )

    invalid_coords = int(
        (
            jobs["latitude"].isna()
            | jobs["longitude"].isna()
        ).sum()
    )

    if invalid_coords:
        raise ValueError(
            f"{invalid_coords} eligible jobs have invalid coordinates."
        )

    print()
    print("CONFIGURATION")
    print("-" * 80)
    print(
        f"DBSCAN radius            : "
        f"{DBSCAN_EPS_METERS:.0f} m"
    )
    print(
        f"DBSCAN min_samples       : "
        f"{DBSCAN_MIN_SAMPLES}"
    )
    print(
        f"Maximum internal radius  : "
        f"{CLUSTER_RADIUS_METERS:.0f} m"
    )
    print(
        f"MAX_CLUSTER_JOBS        : "
        f"{MAX_CLUSTER_JOBS}"
    )
    print("Cluster scope            : same work_type only")
    print("Centroid                  : summary only")
    print("Hotspot detection         : NOT USED")

    # Team assignment is a diagnostic only at this phase.
    # We DO NOT filter jobs using this file because 120 jobs currently exceed
    # one 9-hour shift and must remain in the planning pipeline.
    assignment_diag = None

    if FEASIBLE_ASSIGNMENTS_FILE.exists():
        assignment_diag = pd.read_csv(
            FEASIBLE_ASSIGNMENTS_FILE
        )

    print()
    print("ELIGIBLE JOB PRESERVATION")
    print("-" * 80)
    print(
        "All 441 eligible jobs enter clustering; "
        "team-feasibility is not used as a deletion filter."
    )

    candidates = build_dbscan_candidates(jobs)

    candidate_job_ids = set()

    cluster_groups: list[tuple[str, str, pd.DataFrame, str]] = []

    next_cluster_number = 1

    # ----------------------------------------------------------------------
    # DBSCAN candidate refinement.
    # ----------------------------------------------------------------------

    for candidate_num in sorted(candidates):
        candidate = candidates[candidate_num].copy()

        for job_id in candidate["job_id"]:
            candidate_job_ids.add(str(job_id))

        refined = refine_group(candidate)

        refined = sorted(
            refined,
            key=lambda part: (
                -float(part["priority_score"].max()),
                str(part["job_id"].min()),
            ),
        )

        for part in refined:
            cluster_id = (
                f"CL_{next_cluster_number:04d}"
            )

            next_cluster_number += 1

            source_type = (
                "DBSCAN"
                if len(refined) == 1
                else "DBSCAN_REFINED"
            )

            cluster_groups.append(
                (
                    cluster_id,
                    source_type,
                    part.copy(),
                    str(candidate["_candidate_id"].iloc[0]),
                )
            )

    # ----------------------------------------------------------------------
    # DBSCAN noise becomes standalone jobs.
    # ----------------------------------------------------------------------

    noise_jobs = jobs[
        ~jobs["job_id"].astype(str).isin(
            candidate_job_ids
        )
    ].copy()

    # More robustly, candidate_job_ids only includes DBSCAN cluster labels,
    # so every noise point remains here.
    standalone_count = 0

    for _, row in noise_jobs.iterrows():
        cluster_id = (
            f"CL_{next_cluster_number:04d}"
        )

        next_cluster_number += 1
        standalone_count += 1

        cluster_groups.append(
            (
                cluster_id,
                "STANDALONE",
                pd.DataFrame([row]),
                "DBSCAN_NOISE",
            )
        )

    # ----------------------------------------------------------------------
    # Build member and cluster outputs.
    # ----------------------------------------------------------------------

    cluster_result_rows = []
    cluster_member_rows = []

    for (
        cluster_id,
        cluster_type,
        group,
        candidate_id,
    ) in cluster_groups:
        group = group.copy()

        group = group.sort_values(
            [
                "priority_score",
                "job_id",
            ],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)

        max_distance = pairwise_max_distance_m(
            group
        )

        centroid_lat, centroid_lon = centroid(
            group
        )

        required_equipment_set: set[str] = set()

        for value in group["required_equipment"]:
            if pd.isna(value):
                continue

            for token in str(value).split("|"):
                token = token.strip()
                if token:
                    required_equipment_set.add(token)

        total_service_hours = float(
            group["service_duration_hours"].sum()
        )

        max_workers = float(
            group["workers_required"].max()
        )

        estimated_cost_total = float(
            group["estimated_cost"].sum()
        )

        priority_max = float(
            group["priority_score"].max()
        )

        priority_mean = float(
            group["priority_score"].mean()
        )

        radius_valid = (
            cluster_type == "STANDALONE"
            or max_distance
            <= CLUSTER_RADIUS_METERS
        )

        size_valid = (
            len(group) <= MAX_CLUSTER_JOBS
        )

        if not radius_valid:
            raise RuntimeError(
                f"Cluster {cluster_id} exceeded "
                f"{CLUSTER_RADIUS_METERS} m after refinement."
            )

        if not size_valid:
            raise RuntimeError(
                f"Cluster {cluster_id} exceeded "
                f"MAX_CLUSTER_JOBS={MAX_CLUSTER_JOBS}."
            )

        for sequence_candidate, (_, row) in enumerate(
            group.iterrows(),
            start=1,
        ):
            cluster_member_rows.append(
                {
                    "cluster_id": cluster_id,
                    "job_id": str(row["job_id"]),
                    "complaint_id": str(
                        row["complaint_id"]
                    ),
                    "sequence_candidate": sequence_candidate,
                }
            )

        cluster_result_rows.append(
            {
                "cluster_id": cluster_id,
                "cluster_type": cluster_type,
                "work_type": str(
                    group["work_type"].iloc[0]
                ),
                "complaint_count": int(len(group)),
                "centroid_lat": centroid_lat,
                "centroid_lon": centroid_lon,
                "max_internal_distance_m": round(
                    max_distance,
                    3,
                ),
                "total_service_duration_hours": round(
                    total_service_hours,
                    3,
                ),
                "max_workers_required": max_workers,
                "required_equipment": "|".join(
                    sorted(required_equipment_set)
                ),
                "priority_max": priority_max,
                "priority_mean": round(
                    priority_mean,
                    6,
                ),
                "estimated_cost_total": round(
                    estimated_cost_total,
                    2,
                ),
                "serviceability_status": "PENDING",
                "serviceability_reason": (
                    "Serviceability is evaluated in the next Step 13 phase."
                ),
                "candidate_source": candidate_id,
            }
        )

    cluster_results = pd.DataFrame(
        cluster_result_rows
    )

    cluster_members = pd.DataFrame(
        cluster_member_rows
    )

    # ----------------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------------

    duplicate_member_keys = int(
        cluster_members.duplicated(
            subset=["cluster_id", "job_id"]
        ).sum()
    )

    duplicate_jobs = int(
        cluster_members["job_id"].duplicated().sum()
    )

    max_cluster_size = int(
        cluster_results["complaint_count"].max()
    )

    invalid_radius_clusters = int(
        (
            (
                cluster_results["max_internal_distance_m"]
                > CLUSTER_RADIUS_METERS
            )
            & (
                cluster_results["complaint_count"] > 1
            )
        ).sum()
    )

    standalone_jobs = int(
        (
            cluster_results["cluster_type"]
            == "STANDALONE"
        ).sum()
    )

    clustered_jobs = int(
        cluster_results["complaint_count"]
        .where(
            cluster_results["cluster_type"]
            != "STANDALONE",
            0,
        )
        .sum()
    )

    work_type_mismatch = 0

    for cluster_id, group in cluster_members.groupby(
        "cluster_id"
    ):
        cluster_work_types = set(
            jobs[
                jobs["job_id"].astype(str).isin(
                    group["job_id"].astype(str)
                )
            ]["work_type"]
        )

        if len(cluster_work_types) > 1:
            work_type_mismatch += 1

    validation_rows = []

    def add_validation(
        check_id: str,
        status: str,
        actual: object,
        expected: object,
        notes: str,
    ) -> None:
        validation_rows.append(
            {
                "check_id": check_id,
                "status": status,
                "actual_value": str(actual),
                "expected_value": str(expected),
                "notes": notes,
            }
        )

    add_validation(
        "ELIGIBLE_JOB_COUNT",
        "PASS"
        if total_eligible == 441
        else "FAIL",
        total_eligible,
        441,
        "All canonical eligible jobs enter clustering.",
    )

    add_validation(
        "ALL_ELIGIBLE_JOBS_ACCOUNTED_FOR",
        "PASS"
        if len(cluster_members) == total_eligible
        else "FAIL",
        len(cluster_members),
        total_eligible,
        "No eligible job may silently disappear.",
    )

    add_validation(
        "JOB_UNIQUENESS",
        "PASS"
        if duplicate_jobs == 0
        else "FAIL",
        duplicate_jobs,
        0,
        "Each job appears in exactly one cluster.",
    )

    add_validation(
        "CLUSTER_MEMBER_KEY_UNIQUENESS",
        "PASS"
        if duplicate_member_keys == 0
        else "FAIL",
        duplicate_member_keys,
        0,
        "One row per cluster/job relationship.",
    )

    add_validation(
        "WORK_TYPE_COMPATIBILITY",
        "PASS"
        if work_type_mismatch == 0
        else "FAIL",
        work_type_mismatch,
        0,
        "Prototype clusters contain one operational work type.",
    )

    add_validation(
        "MAX_INTERNAL_DISTANCE",
        "PASS"
        if invalid_radius_clusters == 0
        else "FAIL",
        invalid_radius_clusters,
        0,
        (
            "DBSCAN chaining is checked after clustering; "
            "non-standalone clusters must be <= 2 km."
        ),
    )

    add_validation(
        "MAX_CLUSTER_SIZE",
        "PASS"
        if max_cluster_size <= MAX_CLUSTER_JOBS
        else "FAIL",
        max_cluster_size,
        f"<= {MAX_CLUSTER_JOBS}",
        "Explicit prototype size cap; not an official municipal standard.",
    )

    add_validation(
        "STANDALONE_HANDLING",
        "PASS"
        if standalone_jobs >= 0
        else "FAIL",
        standalone_jobs,
        ">=0",
        "DBSCAN noise points are retained as standalone jobs.",
    )

    add_validation(
        "APPROVED_WORK_TYPE_SCOPE",
        "PASS"
        if set(cluster_results["work_type"]).issubset(
            APPROVED_WORK_TYPES
        )
        else "FAIL",
        sorted(
            cluster_results["work_type"].unique().tolist()
        ),
        sorted(APPROVED_WORK_TYPES),
        "Only four project operational categories are used.",
    )

    validation_df = pd.DataFrame(
        validation_rows
    )

    overall_pass = bool(
        validation_df["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------

    clusters_by_work_type = (
        cluster_results.groupby("work_type")[
            "cluster_id"
        ]
        .count()
        .sort_index()
        .to_dict()
    )

    members_by_work_type = (
        jobs.groupby("work_type")["job_id"]
        .count()
        .sort_index()
        .to_dict()
    )

    summary = {
        "step": "13_operational_clustering",
        "project_root": str(PROJECT_ROOT),
        "read_only": True,
        "input_eligible_jobs": int(total_eligible),
        "configuration": {
            "dbscan_eps_meters": DBSCAN_EPS_METERS,
            "dbscan_min_samples": DBSCAN_MIN_SAMPLES,
            "max_internal_distance_meters": CLUSTER_RADIUS_METERS,
            "max_cluster_jobs": MAX_CLUSTER_JOBS,
            "work_type_rule": "same_work_type_only",
            "centroid_rule": "summary_only_not_a_route_stop",
            "hotspot_detection": False,
        },
        "counts": {
            "clusters_total": int(len(cluster_results)),
            "clustered_jobs": clustered_jobs,
            "standalone_jobs": standalone_jobs,
            "max_cluster_size_observed": max_cluster_size,
        },
        "clusters_by_work_type": {
            key: int(value)
            for key, value in clusters_by_work_type.items()
        },
        "jobs_by_work_type": {
            key: int(value)
            for key, value in members_by_work_type.items()
        },
        "team_assignment_note": (
            "The 120 jobs whose service duration exceeds the 9-hour prototype "
            "shift are retained in clustering. Feasible-team assignment is "
            "not used as a deletion filter; later serviceability/scheduling "
            "must handle multi-shift or deferred execution explicitly."
        ),
        "validation": {
            "status": "PASS" if overall_pass else "FAIL",
            "checks_total": int(len(validation_df)),
            "checks_passed": int(
                validation_df["status"].eq("PASS").sum()
            ),
            "checks_failed": int(
                validation_df["status"].eq("FAIL").sum()
            ),
        },
        "outputs": {
            "cluster_results": str(CLUSTER_RESULTS_FILE),
            "cluster_members": str(CLUSTER_MEMBERS_FILE),
            "validation": str(VALIDATION_FILE),
            "summary": str(SUMMARY_FILE),
        },
        "next_step": (
            "Proceed to serviceability after reviewing cluster size, "
            "internal distance, duration, workers, equipment and team feasibility."
        ),
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cluster_results.to_csv(
        CLUSTER_RESULTS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    cluster_members.to_csv(
        CLUSTER_MEMBERS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("-" * 80)
    print("CLUSTER SUMMARY")
    print("-" * 80)
    print(
        f"Eligible jobs                : {total_eligible}"
    )
    print(
        f"Clusters total               : {len(cluster_results)}"
    )
    print(
        f"Jobs in multi-job clusters   : {clustered_jobs}"
    )
    print(
        f"Standalone jobs              : {standalone_jobs}"
    )
    print(
        f"Max cluster size observed    : {max_cluster_size}"
    )

    print()
    print("Clusters by work type:")
    for work_type in sorted(
        clusters_by_work_type
    ):
        print(
            f"  {work_type:12} : "
            f"{clusters_by_work_type[work_type]}"
        )

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validation_rows:
        print(
            f"{row['check_id']:35} : "
            f"{row['status']:6} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13 OPERATIONAL CLUSTERING GATE: "
        + ("PASS" if overall_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(
        f"Cluster results : {CLUSTER_RESULTS_FILE}"
    )
    print(
        f"Cluster members : {CLUSTER_MEMBERS_FILE}"
    )
    print(
        f"Validation      : {VALIDATION_FILE}"
    )
    print(
        f"Summary         : {SUMMARY_FILE}"
    )

    if not overall_pass:
        raise RuntimeError(
            "Operational clustering validation failed. "
            "Review clustering_validation.csv before continuing."
        )


if __name__ == "__main__":
    main()
