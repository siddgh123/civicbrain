from __future__ import annotations

import getpass
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "candidate_pairs.csv"
)

RESULT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_engine_results.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_engine_summary.csv"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_engine_config.json"
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SPATIAL_RADIUS_METERS = 300.0
RECENT_WINDOW_DAYS = 7
RECENT_WINDOW_HOURS = RECENT_WINDOW_DAYS * 24.0

TEXT_WEIGHT = 0.70
DISTANCE_WEIGHT = 0.20
RECENCY_WEIGHT = 0.10

DUPLICATE_THRESHOLD = 0.59
UNCERTAIN_LOWER_BOUND = 0.55

DECISION_SOURCE = "AI"

DB_HOST = os.getenv("CIVICBRAIN_DB_HOST", "localhost")
DB_PORT = int(os.getenv("CIVICBRAIN_DB_PORT", "5432"))
DB_NAME = os.getenv("CIVICBRAIN_DB_NAME", "civicbrain")
DB_USER = os.getenv("CIVICBRAIN_DB_USER", "postgres")


def normalize_complaint_id(value: object) -> int:
    """Accept both 1 / '1' and C001 / c001 forms."""
    if pd.isna(value):
        raise ValueError("Complaint ID is missing.")

    text = str(value).strip()

    if not text:
        raise ValueError("Complaint ID is empty.")

    if text[:1].lower() == "c":
        text = text[1:]

    complaint_id = int(text)

    if complaint_id <= 0:
        raise ValueError(
            f"Complaint ID must be positive: {value!r}"
        )

    return complaint_id


def connect_db():
    password = os.getenv("CIVICBRAIN_DB_PASSWORD")

    if password is None:
        password = getpass.getpass(
            f"PostgreSQL password for {DB_USER}@{DB_HOST}: "
        )

    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=password,
        )
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL connection failed. "
            "Check that PostgreSQL is running and the credentials "
            "are correct."
        ) from exc

    # Keep psycopg2's default transactional mode.
    # The engine performs reads, inserts/updates, validation, then commits
    # once at the end. Exceptions are rolled back by the caller.
    return connection


def fetch_complaints(connection) -> pd.DataFrame:
    query = """
        SELECT
            complaint_id,
            title,
            description,
            submitted_at
        FROM public.complaints
        ORDER BY complaint_id
    """

    df = pd.read_sql_query(
        query,
        connection,
    )

    if df.empty:
        raise RuntimeError(
            "public.complaints returned zero rows."
        )

    df["complaint_id"] = pd.to_numeric(
        df["complaint_id"],
        errors="raise",
    ).astype(int)

    df["submitted_at"] = pd.to_datetime(
        df["submitted_at"],
        utc=True,
        errors="coerce",
    )

    if df["submitted_at"].isna().any():
        bad = df.loc[
            df["submitted_at"].isna(),
            "complaint_id",
        ].tolist()
        raise RuntimeError(
            "Missing/invalid submitted_at in complaints: "
            + ", ".join(map(str, bad))
        )

    df["title"] = df["title"].fillna("").astype(str)
    df["description"] = (
        df["description"]
        .fillna("")
        .astype(str)
    )

    df["combined_text"] = (
        df["title"].str.strip()
        + "\n"
        + df["description"].str.strip()
    ).str.strip()

    return df


def fetch_candidate_pairs() -> pd.DataFrame:
    if not CANDIDATE_FILE.exists():
        raise FileNotFoundError(
            f"Candidate-pair file not found:\n{CANDIDATE_FILE}"
        )

    df = pd.read_csv(CANDIDATE_FILE)

    required = [
        "complaint_id_1",
        "complaint_id_2",
        "distance_meters",
        "time_difference_hours",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "candidate_pairs.csv is missing required columns:\n"
            + "\n".join(f" - {c}" for c in missing)
        )

    df["complaint_id_1"] = df[
        "complaint_id_1"
    ].map(normalize_complaint_id)

    df["complaint_id_2"] = df[
        "complaint_id_2"
    ].map(normalize_complaint_id)

    for column in [
        "distance_meters",
        "time_difference_hours",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[
        [
            "distance_meters",
            "time_difference_hours",
        ]
    ].isna().any().any():
        raise ValueError(
            "Candidate pairs contain invalid distance/time values."
        )

    if (df["complaint_id_1"] == df["complaint_id_2"]).any():
        raise ValueError(
            "Self-pairs detected in candidate_pairs.csv."
        )

    if (df["distance_meters"] < 0).any():
        raise ValueError(
            "Negative distances detected."
        )

    if (df["time_difference_hours"] < 0).any():
        raise ValueError(
            "Negative time differences detected."
        )

    if (
        df["distance_meters"]
        > SPATIAL_RADIUS_METERS
        + 1e-9
    ).any():
        raise ValueError(
            "Candidate file contains a pair outside the configured "
            f"{SPATIAL_RADIUS_METERS:.0f}m candidate radius."
        )

    # Candidate pairs were built with a broader inspection window.
    # Final engine window is now fixed to 7 days.
    eligible = df[
        df["time_difference_hours"]
        <= RECENT_WINDOW_HOURS + 1e-9
    ].copy()

    if eligible.empty:
        raise RuntimeError(
            "No candidate pairs remain after the 7-day recent-window filter."
        )

    pair_keys = (
        eligible.apply(
            lambda row: tuple(
                sorted(
                    [
                        int(row["complaint_id_1"]),
                        int(row["complaint_id_2"]),
                    ]
                )
            ),
            axis=1,
        )
    )

    if pair_keys.duplicated().any():
        raise ValueError(
            "Duplicate unordered candidate pairs detected."
        )

    return eligible.reset_index(drop=True)


def build_text_embeddings(
    complaints: pd.DataFrame,
    candidate_pairs: pd.DataFrame,
):
    complaint_lookup = complaints.set_index(
        "complaint_id"
    )["combined_text"].to_dict()

    required_ids = sorted(
        set(
            candidate_pairs[
                "complaint_id_1"
            ].tolist()
            + candidate_pairs[
                "complaint_id_2"
            ].tolist()
        )
    )

    missing_ids = [
        complaint_id
        for complaint_id in required_ids
        if complaint_id not in complaint_lookup
    ]

    if missing_ids:
        raise RuntimeError(
            "Candidate pairs reference complaint IDs not present "
            "in public.complaints:\n"
            + ", ".join(map(str, missing_ids))
        )

    texts = []
    for complaint_id in required_ids:
        text = complaint_lookup[complaint_id]

        if not text.strip():
            raise RuntimeError(
                f"Complaint {complaint_id} has empty title/description."
            )

        texts.append(text)

    print()
    print("LOADING SENTENCE TRANSFORMER")
    print("-" * 80)
    print(f"Model                       : {MODEL_NAME}")

    model = SentenceTransformer(
        MODEL_NAME
    )

    print("Model status                : OK")

    print()
    print("GENERATING EMBEDDINGS")
    print("-" * 80)

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    embedding_lookup = {
        complaint_id: embedding
        for complaint_id, embedding in zip(
            required_ids,
            embeddings,
        )
    }

    print(
        f"Embeddings generated        : {len(embedding_lookup)}"
    )

    return embedding_lookup


def calculate_results(
    candidate_pairs: pd.DataFrame,
    complaints: pd.DataFrame,
    embedding_lookup: dict[int, np.ndarray],
) -> pd.DataFrame:
    complaint_time = complaints.set_index(
        "complaint_id"
    )["submitted_at"].to_dict()

    rows = []

    for pair_number, row in enumerate(
        candidate_pairs.itertuples(index=False),
        start=1,
    ):
        complaint_a = int(
            row.complaint_id_1
        )
        complaint_b = int(
            row.complaint_id_2
        )

        text_similarity = float(
            np.dot(
                embedding_lookup[complaint_a],
                embedding_lookup[complaint_b],
            )
        )

        text_similarity = float(
            np.clip(
                text_similarity,
                0.0,
                1.0,
            )
        )

        distance_meters = float(
            row.distance_meters
        )

        time_difference_hours = float(
            row.time_difference_hours
        )

        distance_score = float(
            np.clip(
                1.0
                - (
                    distance_meters
                    / SPATIAL_RADIUS_METERS
                ),
                0.0,
                1.0,
            )
        )

        recency_score = float(
            np.clip(
                1.0
                - (
                    time_difference_hours
                    / RECENT_WINDOW_HOURS
                ),
                0.0,
                1.0,
            )
        )

        duplicate_score = float(
            np.clip(
                TEXT_WEIGHT * text_similarity
                + DISTANCE_WEIGHT * distance_score
                + RECENCY_WEIGHT * recency_score,
                0.0,
                1.0,
            )
        )

        if duplicate_score >= DUPLICATE_THRESHOLD:
            decision = "DUPLICATE"
            review_required = False
        elif (
            duplicate_score
            >= UNCERTAIN_LOWER_BOUND
        ):
            decision = "UNCERTAIN"
            review_required = True
        else:
            decision = "NOT_DUPLICATE"
            review_required = False

        rows.append(
            {
                "pair_id": f"ENG{pair_number:04d}",
                "complaint_id_1": complaint_a,
                "complaint_id_2": complaint_b,
                "text_similarity": text_similarity,
                "distance_meters": distance_meters,
                "distance_score": distance_score,
                "time_difference_hours": time_difference_hours,
                "recency_score": recency_score,
                "duplicate_score": duplicate_score,
                "decision": decision,
                "decision_source": DECISION_SOURCE,
                "review_required": review_required,
                "submitted_at_1": complaint_time[
                    complaint_a
                ],
                "submitted_at_2": complaint_time[
                    complaint_b
                ],
            }
        )

    result_df = pd.DataFrame(rows)

    return result_df


def check_relation_table_empty(connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM public.duplicate_relation"
        )
        count = int(cursor.fetchone()[0])

    return count


def validate_complaint_schema_for_load(
    connection,
) -> None:
    required_columns = {
        "duplicate_status",
        "master_complaint_id",
        "matched_complaint_id",
        "duplicate_checked_at",
        "duplicate_review_required",
    }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='complaints'
            """
        )

        present = {
            row[0]
            for row in cursor.fetchall()
        }

    missing = required_columns - present

    if missing:
        raise RuntimeError(
            "Required Step 12 complaint columns are missing:\n"
            + "\n".join(
                f" - {column}"
                for column in sorted(missing)
            )
        )


def decide_master_assignments(
    result_df: pd.DataFrame,
    complaints: pd.DataFrame,
) -> tuple[dict[int, int], dict[int, int | None], dict[int, str]]:
    """
    Returns:
      complaint_to_master:
          only duplicate member complaints get a non-null root.
      matched_complaint:
          best direct match for each complaint.
      conflict_comment:
          complaint -> explanation when a duplicate pair would merge
          two different existing masters. Such cases remain manual review.
    """

    complaint_time = complaints.set_index(
        "complaint_id"
    )["submitted_at"].to_dict()

    complaint_to_master: dict[int, int] = {}
    matched_complaint: dict[int, int | None] = {}
    conflict_comment: dict[int, str] = {}

    # Best direct scored match used for complaint-level matched_complaint_id.
    for row in result_df.sort_values(
        "duplicate_score",
        ascending=False,
    ).itertuples(index=False):

        if row.decision not in (
            "DUPLICATE",
            "UNCERTAIN",
        ):
            continue

        a = int(row.complaint_id_1)
        b = int(row.complaint_id_2)

        matched_complaint.setdefault(
            a,
            b,
        )
        matched_complaint.setdefault(
            b,
            a,
        )

    # Process only strong duplicate relations chronologically.
    duplicate_rows = result_df[
        result_df["decision"] == "DUPLICATE"
    ].copy()

    duplicate_rows["pair_latest_time"] = (
        duplicate_rows[
            [
                "submitted_at_1",
                "submitted_at_2",
            ]
        ].max(axis=1)
    )

    duplicate_rows = duplicate_rows.sort_values(
        [
            "pair_latest_time",
            "duplicate_score",
        ],
        ascending=[
            True,
            False,
        ],
    )

    for row in duplicate_rows.itertuples(index=False):
        a = int(row.complaint_id_1)
        b = int(row.complaint_id_2)

        master_a = complaint_to_master.get(a)
        master_b = complaint_to_master.get(b)

        if master_a is None and master_b is None:
            time_a = complaint_time[a]
            time_b = complaint_time[b]

            if time_a <= time_b:
                master = a
                member = b
            else:
                master = b
                member = a

            complaint_to_master[member] = master

        elif master_a is not None and master_b is None:
            complaint_to_master[b] = master_a

        elif master_a is None and master_b is not None:
            complaint_to_master[a] = master_b

        elif master_a == master_b:
            # Already belongs to the same master.
            pass

        else:
            comment = (
                "Duplicate relation connects two different existing "
                "master issues; automatic master merge blocked. "
                "Officer review required."
            )

            conflict_comment[a] = comment
            conflict_comment[b] = comment

    return (
        complaint_to_master,
        matched_complaint,
        conflict_comment,
    )


def insert_engine_results(
    connection,
    result_df: pd.DataFrame,
    complaints: pd.DataFrame,
) -> None:
    (
        complaint_to_master,
        matched_complaint,
        conflict_comment,
    ) = decide_master_assignments(
        result_df,
        complaints,
    )

    now = datetime.now(timezone.utc)

    relation_rows = []

    for row in result_df.itertuples(index=False):
        a = int(row.complaint_id_1)
        b = int(row.complaint_id_2)

        master_id = None
        review_required = bool(
            row.review_required
        )
        review_comment = None

        if row.decision == "DUPLICATE":
            master_a = complaint_to_master.get(a)
            master_b = complaint_to_master.get(b)

            if a in conflict_comment or b in conflict_comment:
                review_required = True
                review_comment = conflict_comment.get(
                    a,
                    conflict_comment.get(b),
                )
                master_id = None

            elif master_a is not None:
                master_id = master_a
            elif master_b is not None:
                master_id = master_b
            else:
                # This should only be possible if master assignment
                # could not be safely established.
                review_required = True
                review_comment = (
                    "Duplicate decision has no safe master assignment; "
                    "manual review required."
                )

        elif row.decision == "UNCERTAIN":
            review_required = True
            review_comment = (
                "Borderline duplicate score; automatic merge disabled."
            )

        relation_rows.append(
            (
                a,
                master_id,
                b,
                float(row.text_similarity),
                float(row.distance_meters),
                float(row.time_difference_hours),
                float(row.duplicate_score),
                row.decision,
                DECISION_SOURCE,
                review_required,
                None,
                None,
                None,
                review_comment,
                now,
            )
        )

    relation_sql = """
        INSERT INTO public.duplicate_relation (
            complaint_id,
            master_complaint_id,
            similar_complaint_id,
            text_similarity,
            distance_meters,
            time_difference_hours,
            duplicate_score,
            decision,
            decision_source,
            review_required,
            review_decision,
            reviewed_by,
            reviewed_at,
            review_comment,
            created_at
        )
        VALUES %s
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            relation_sql,
            relation_rows,
            page_size=200,
        )

    # Determine complaint-level status.
    involved_ids = sorted(
        set(
            result_df["complaint_id_1"].tolist()
            + result_df["complaint_id_2"].tolist()
        )
    )

    status_by_complaint: dict[int, str] = {}

    for complaint_id in involved_ids:
        rows = result_df[
            (
                result_df["complaint_id_1"]
                == complaint_id
            )
            | (
                result_df["complaint_id_2"]
                == complaint_id
            )
        ]

        has_conflicting_master = (
            complaint_id in conflict_comment
        )

        has_duplicate = (
            (rows["decision"] == "DUPLICATE")
            .any()
        )

        has_uncertain = (
            (rows["decision"] == "UNCERTAIN")
            .any()
        )

        if has_conflicting_master:
            status = "UNCERTAIN"
        elif has_duplicate:
            status = "DUPLICATE"
        elif has_uncertain:
            status = "UNCERTAIN"
        else:
            status = "NOT_DUPLICATE"

        status_by_complaint[
            complaint_id
        ] = status

    update_rows = []

    for complaint_id in involved_ids:
        status = status_by_complaint[
            complaint_id
        ]

        master_id = complaint_to_master.get(
            complaint_id
        )

        # For a master root, keep master_complaint_id NULL.
        # For duplicate members, point to the root complaint.
        if master_id == complaint_id:
            master_id = None

        matched_id = matched_complaint.get(
            complaint_id
        )

        review_required = (
            status == "UNCERTAIN"
            or complaint_id in conflict_comment
        )

        update_rows.append(
            (
                status,
                master_id,
                matched_id,
                now,
                review_required,
                complaint_id,
            )
        )

    update_sql = """
        UPDATE public.complaints AS c
        SET
            duplicate_status = v.duplicate_status,
            master_complaint_id = v.master_complaint_id,
            matched_complaint_id = v.matched_complaint_id,
            duplicate_checked_at = v.duplicate_checked_at,
            duplicate_review_required = v.duplicate_review_required
        FROM (
            VALUES %s
        ) AS v(
            duplicate_status,
            master_complaint_id,
            matched_complaint_id,
            duplicate_checked_at,
            duplicate_review_required,
            complaint_id
        )
        WHERE c.complaint_id = v.complaint_id::bigint
    """

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            update_sql,
            update_rows,
            page_size=200,
        )


def validate_after_load(
    connection,
    expected_relation_rows: int,
) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM public.duplicate_relation
            """
        )
        relation_count = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM public.complaints
            WHERE duplicate_status <> 'NOT_EVALUATED'
            """
        )
        evaluated_complaints = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM public.duplicate_relation
            WHERE complaint_id = similar_complaint_id
            """
        )
        self_pairs = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM public.duplicate_relation
            WHERE decision = 'UNCERTAIN'
              AND review_required <> TRUE
            """
        )
        uncertain_without_review = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM public.complaints c
            LEFT JOIN public.complaints m
              ON m.complaint_id = c.master_complaint_id
            WHERE c.master_complaint_id IS NOT NULL
              AND m.complaint_id IS NULL
            """
        )
        invalid_master_links = int(
            cursor.fetchone()[0]
        )

    checks = {
        "relation_rows": relation_count,
        "expected_relation_rows": expected_relation_rows,
        "evaluated_complaints": evaluated_complaints,
        "self_pairs": self_pairs,
        "uncertain_without_review": uncertain_without_review,
        "invalid_master_links": invalid_master_links,
    }

    if relation_count != expected_relation_rows:
        raise RuntimeError(
            "Post-load relation count mismatch: "
            f"expected {expected_relation_rows}, "
            f"found {relation_count}."
        )

    if self_pairs != 0:
        raise RuntimeError(
            f"Self-pair validation failed: {self_pairs}"
        )

    if uncertain_without_review != 0:
        raise RuntimeError(
            "Some UNCERTAIN relations are missing review_required=true."
        )

    if invalid_master_links != 0:
        raise RuntimeError(
            "Invalid master complaint links detected."
        )

    return checks


def print_summary(
    result_df: pd.DataFrame,
    checks: dict[str, int],
) -> None:
    print()
    print("=" * 80)
    print("DUPLICATE ENGINE RESULT SUMMARY")
    print("=" * 80)

    print(
        result_df[
            "decision"
        ].value_counts().sort_index().to_string()
    )

    print()
    print(
        "Score statistics:"
    )
    print(
        result_df[
            "duplicate_score"
        ].describe()[
            [
                "min",
                "25%",
                "50%",
                "mean",
                "75%",
                "max",
            ]
        ].to_string()
    )

    print()
    print(
        "Text similarity:"
    )
    print(
        result_df[
            "text_similarity"
        ].describe()[
            [
                "min",
                "50%",
                "mean",
                "max",
            ]
        ].to_string()
    )

    print()
    print(
        "Time-window candidate count: "
        f"{len(result_df)}"
    )

    print(
        "DUPLICATE count            : "
        f"{int((result_df['decision'] == 'DUPLICATE').sum())}"
    )

    print(
        "UNCERTAIN count            : "
        f"{int((result_df['decision'] == 'UNCERTAIN').sum())}"
    )

    print(
        "NOT_DUPLICATE count        : "
        f"{int((result_df['decision'] == 'NOT_DUPLICATE').sum())}"
    )

    print()
    print("DATABASE VALIDATION")
    print("-" * 80)

    for key, value in checks.items():
        print(f"{key:30s}: {value}")

    print()
    print(
        "DATABASE LOAD + VALIDATION PASSED"
    )


def save_outputs(
    result_df: pd.DataFrame,
    checks: dict[str, int],
) -> None:
    RESULT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df.to_csv(
        RESULT_FILE,
        index=False,
        encoding="utf-8",
    )

    summary_rows = [
        {
            "metric": "candidate_pairs_eligible_7d",
            "value": len(result_df),
        },
        {
            "metric": "duplicate_count",
            "value": int(
                (
                    result_df["decision"]
                    == "DUPLICATE"
                ).sum()
            ),
        },
        {
            "metric": "uncertain_count",
            "value": int(
                (
                    result_df["decision"]
                    == "UNCERTAIN"
                ).sum()
            ),
        },
        {
            "metric": "not_duplicate_count",
            "value": int(
                (
                    result_df["decision"]
                    == "NOT_DUPLICATE"
                ).sum()
            ),
        },
        {
            "metric": "mean_duplicate_score",
            "value": float(
                result_df[
                    "duplicate_score"
                ].mean()
            ),
        },
        {
            "metric": "mean_text_similarity",
            "value": float(
                result_df[
                    "text_similarity"
                ].mean()
            ),
        },
        {
            "metric": "mean_distance_meters",
            "value": float(
                result_df[
                    "distance_meters"
                ].mean()
            ),
        },
        {
            "metric": "mean_time_difference_hours",
            "value": float(
                result_df[
                    "time_difference_hours"
                ].mean()
            ),
        },
    ]

    for key, value in checks.items():
        summary_rows.append(
            {
                "metric": f"db_check_{key}",
                "value": value,
            }
        )

    pd.DataFrame(
        summary_rows
    ).to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    config = {
        "status": "experimental",
        "engine_version": "step12_duplicate_engine_v1",
        "candidate_radius_meters": SPATIAL_RADIUS_METERS,
        "recent_window_days": RECENT_WINDOW_DAYS,
        "text_model": MODEL_NAME,
        "text_weight": TEXT_WEIGHT,
        "distance_weight": DISTANCE_WEIGHT,
        "recency_weight": RECENCY_WEIGHT,
        "duplicate_threshold": DUPLICATE_THRESHOLD,
        "uncertain_lower_bound": UNCERTAIN_LOWER_BOUND,
        "decision_rules": {
            "duplicate": f"score >= {DUPLICATE_THRESHOLD:.2f}",
            "uncertain": (
                f"{UNCERTAIN_LOWER_BOUND:.2f} <= score "
                f"< {DUPLICATE_THRESHOLD:.2f}"
            ),
            "not_duplicate": (
                f"score < {UNCERTAIN_LOWER_BOUND:.2f}"
            ),
        },
        "master_rule": (
            "When a DUPLICATE relation is confirmed, attach the newer "
            "complaint to the existing verified master. If neither "
            "complaint has a master, the earlier submitted complaint "
            "becomes the canonical master. If two different existing "
            "masters would have to be merged, block automatic merge "
            "and require manual review."
        ),
        "uncertain_rule": (
            "UNCERTAIN relations never auto-merge."
        ),
        "original_records": (
            "Original citizen complaint rows are preserved."
        ),
        "source_data": {
            "candidate_pairs": str(
                CANDIDATE_FILE
                .relative_to(PROJECT_ROOT)
            ),
            "benchmark_status": (
                "The engine operates on the existing synthetic complaint "
                "dataset and current candidate pairs. It does not create "
                "official TDMC ground-truth labels."
            ),
        },
        "validation": checks,
    }

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 80)
    print(
        "CIVICBRAIN STEP 12 — ACTUAL DUPLICATE ENGINE + DATABASE LOAD"
    )
    print("=" * 80)

    print()
    print("CONFIGURATION")
    print("-" * 80)
    print(
        f"Candidate radius             : "
        f"{SPATIAL_RADIUS_METERS:.0f} m"
    )
    print(
        f"Recent window                : "
        f"{RECENT_WINDOW_DAYS} days"
    )
    print(
        f"Text model                   : "
        f"{MODEL_NAME}"
    )
    print(
        f"Weights                      : "
        f"{TEXT_WEIGHT:.2f} / "
        f"{DISTANCE_WEIGHT:.2f} / "
        f"{RECENCY_WEIGHT:.2f}"
    )
    print(
        f"Duplicate threshold          : "
        f"{DUPLICATE_THRESHOLD:.2f}"
    )
    print(
        f"Uncertain lower bound        : "
        f"{UNCERTAIN_LOWER_BOUND:.2f}"
    )

    candidate_pairs = fetch_candidate_pairs()

    print()
    print(
        f"Candidate pairs after 7-day filter: "
        f"{len(candidate_pairs)}"
    )

    connection = connect_db()

    try:
        validate_complaint_schema_for_load(
            connection
        )

        existing_relations = check_relation_table_empty(
            connection
        )

        if existing_relations != 0:
            raise RuntimeError(
                "public.duplicate_relation is not empty "
                f"({existing_relations} rows). "
                "This safe first-load script refuses to overwrite "
                "existing relation/review data."
            )

        complaints = fetch_complaints(
            connection
        )

        if len(complaints) != 500:
            print()
            print(
                "WARNING: public.complaints row count is "
                f"{len(complaints)}, not 500."
            )

        embedding_lookup = build_text_embeddings(
            complaints,
            candidate_pairs,
        )

        print()
        print(
            "SCORING CANDIDATE PAIRS"
        )
        print("-" * 80)

        result_df = calculate_results(
            candidate_pairs,
            complaints,
            embedding_lookup,
        )

        print(
            f"Pairs scored                 : "
            f"{len(result_df)}"
        )

        print()
        print(
            "LOADING RESULTS INTO POSTGRESQL"
        )
        print("-" * 80)

        # psycopg2 starts a transaction automatically when the earlier
        # SELECTs execute. The connection is already in transaction mode,
        # so do not change autocommit state here; doing so inside an active
        # transaction raises: "set_session cannot be used inside a transaction".
        #
        # The transaction will still be atomic because insert_engine_results()
        # is followed by validation and an explicit COMMIT. Any exception
        # triggers the ROLLBACK in the outer exception handler.
        insert_engine_results(
            connection,
            result_df,
            complaints,
        )

        checks = validate_after_load(
            connection,
            expected_relation_rows=len(result_df),
        )

        connection.commit()

        save_outputs(
            result_df,
            checks,
        )

        print_summary(
            result_df,
            checks,
        )

        print()
        print("=" * 80)
        print("OUTPUT FILES")
        print("=" * 80)
        print(
            f"Engine results               : {RESULT_FILE}"
        )
        print(
            f"Engine summary              : {SUMMARY_FILE}"
        )
        print(
            f"Engine config               : {CONFIG_FILE}"
        )

        print()
        print("=" * 80)
        print(
            "ACTUAL DUPLICATE ENGINE + DATABASE LOAD COMPLETE"
        )
        print("=" * 80)

    except Exception:
        connection.rollback()
        print()
        print(
            "ERROR: Transaction rolled back. "
            "No partial Step 12 database load was kept."
        )
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print(
            f"FATAL: {type(exc).__name__}: {exc}"
        )
        sys.exit(1)
