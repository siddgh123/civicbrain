from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13.3 — TEAM MASTER + TEAM EQUIPMENT
#
# Purpose:
#   Create the Step 13 prototype team configuration for the four approved
#   operational work types:
#
#       ROAD
#       WATER
#       GARBAGE
#       ELECTRICITY
#
# Inputs:
#   data/optimization/jobs/normalized_job_resources.csv
#   data/optimization/config/equipment_catalog.csv
#
# Outputs:
#   data/optimization/teams/team_master.csv
#   data/optimization/teams/team_equipment.csv
#   data/optimization/teams/team_master_validation.csv
#   data/optimization/teams/team_master_summary.json
#
# IMPORTANT:
#   - No PostgreSQL writes.
#   - No Step 10 retraining.
#   - No Step 11 changes.
#   - No Step 12 changes.
#   - No hotspot detection.
#   - Four operational work types only.
#   - Team workforce/equipment quantities are explicitly marked as
#     synthetic prototype assumptions.
#   - Depot coordinates are intentionally left unresolved because no
#     authoritative depot coordinate is present in the current inputs.
#   - Do NOT invent a depot location.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

RESOURCE_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "normalized_job_resources.csv"
)

EQUIPMENT_CATALOG_FILE = (
    DATA_DIR
    / "optimization"
    / "config"
    / "equipment_catalog.csv"
)

OUTPUT_DIR = DATA_DIR / "optimization" / "teams"

TEAM_MASTER_FILE = OUTPUT_DIR / "team_master.csv"
TEAM_EQUIPMENT_FILE = OUTPUT_DIR / "team_equipment.csv"
VALIDATION_FILE = OUTPUT_DIR / "team_master_validation.csv"
SUMMARY_FILE = OUTPUT_DIR / "team_master_summary.json"

APPROVED_WORK_TYPES = [
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
]

# Prototype team structure:
# ROAD and WATER capacities follow the project methodology example.
# GARBAGE and ELECTRICITY are added because the frozen CivicBrain scope
# contains four operational categories.
TEAM_DEFINITIONS = [
    {
        "team_id": "T001",
        "team_name": "Road Team A",
        "team_type": "ROAD",
        "worker_capacity": 6,
        "working_start": "08:00",
        "working_end": "17:00",
    },
    {
        "team_id": "T002",
        "team_name": "Water Team A",
        "team_type": "WATER",
        "worker_capacity": 5,
        "working_start": "08:00",
        "working_end": "17:00",
    },
    {
        "team_id": "T003",
        "team_name": "Garbage Team A",
        "team_type": "GARBAGE",
        "worker_capacity": 4,
        "working_start": "08:00",
        "working_end": "17:00",
    },
    {
        "team_id": "T004",
        "team_name": "Electricity Team A",
        "team_type": "ELECTRICITY",
        "worker_capacity": 4,
        "working_start": "08:00",
        "working_end": "17:00",
    },
]

SYNTHETIC_TEAM_SOURCE = "synthetic_prototype"

# No actual depot coordinate is available in the current Step 13 inputs.
# Keep them blank rather than inventing a location.
DEPOT_LAT = ""
DEPOT_LON = ""
DEPOT_STATUS = "TO_BE_CONFIGURED"


def validation_row(
    check_id: str,
    status: str,
    actual: object,
    expected: object,
    notes: str,
) -> dict:
    return {
        "check_id": check_id,
        "status": status,
        "actual_value": str(actual),
        "expected_value": str(expected),
        "notes": notes,
    }


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not RESOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Normalized resource file not found:\n{RESOURCE_FILE}"
        )

    if not EQUIPMENT_CATALOG_FILE.exists():
        raise FileNotFoundError(
            f"Equipment catalog not found:\n{EQUIPMENT_CATALOG_FILE}"
        )

    resources = pd.read_csv(RESOURCE_FILE)
    equipment = pd.read_csv(EQUIPMENT_CATALOG_FILE)

    required_resources = {
        "complaint_id",
        "job_id",
        "work_type",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
    }

    missing_resources = required_resources - set(resources.columns)
    if missing_resources:
        raise ValueError(
            "Normalized resource dataset missing columns: "
            + ", ".join(sorted(missing_resources))
        )

    required_equipment = {
        "equipment_type",
        "available_quantity",
        "status",
        "source",
    }

    missing_equipment = required_equipment - set(equipment.columns)
    if missing_equipment:
        raise ValueError(
            "Equipment catalog missing columns: "
            + ", ".join(sorted(missing_equipment))
        )

    return resources, equipment


def parse_equipment(value: object) -> list[str]:
    raw = clean_text(value)
    if not raw:
        return []
    return sorted(
        {
            token.strip()
            for token in raw.split("|")
            if token.strip()
        }
    )


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.3 — TEAM MASTER + TEAM EQUIPMENT")
    print("=" * 80)

    print()
    print("READ-ONLY INPUTS")
    print("-" * 80)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Resources    : {RESOURCE_FILE}")
    print(f"Equipment    : {EQUIPMENT_CATALOG_FILE}")
    print("Database     : NOT USED")

    resources, equipment_catalog = load_inputs()

    resources["work_type"] = (
        resources["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    resources["required_equipment"] = (
        resources["required_equipment"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ----------------------------------------------------------------------
    # Team master
    # ----------------------------------------------------------------------

    team_master_rows = []

    for team in TEAM_DEFINITIONS:
        team_master_rows.append(
            {
                "team_id": team["team_id"],
                "team_name": team["team_name"],
                "team_type": team["team_type"],
                "worker_capacity": team["worker_capacity"],
                "working_start": team["working_start"],
                "working_end": team["working_end"],
                "depot_lat": DEPOT_LAT,
                "depot_lon": DEPOT_LON,
                "depot_status": DEPOT_STATUS,
                "status": "ACTIVE",
                "source": SYNTHETIC_TEAM_SOURCE,
            }
        )

    team_master = pd.DataFrame(team_master_rows)

    # ----------------------------------------------------------------------
    # Equipment requirement by operational work type
    #
    # Data-driven: use only equipment actually observed in the normalized
    # Step 10 requirements for that work type.
    #
    # Quantity=1 is a prototype assumption indicating one shared available
    # unit for sequential scheduling. It is not a claim about actual TDMC
    # inventory.
    # ----------------------------------------------------------------------

    equipment_by_work_type: dict[str, set[str]] = {
        work_type: set()
        for work_type in APPROVED_WORK_TYPES
    }

    for _, row in resources.iterrows():
        work_type = str(row["work_type"]).strip().upper()

        if work_type not in equipment_by_work_type:
            continue

        for token in parse_equipment(row["required_equipment"]):
            equipment_by_work_type[work_type].add(token)

    team_equipment_rows = []

    for team in TEAM_DEFINITIONS:
        team_type = team["team_type"]

        for equipment_type in sorted(
            equipment_by_work_type.get(team_type, set())
        ):
            team_equipment_rows.append(
                {
                    "team_id": team["team_id"],
                    "equipment_type": equipment_type,
                    "quantity": 1,
                    "available": True,
                    "valid_from": "",
                    "valid_to": "",
                    "source": SYNTHETIC_TEAM_SOURCE,
                    "assumption_note": (
                        "Prototype quantity=1 for sequential scheduling. "
                        "Not verified municipal inventory."
                    ),
                }
            )

    team_equipment = pd.DataFrame(
        team_equipment_rows,
        columns=[
            "team_id",
            "equipment_type",
            "quantity",
            "available",
            "valid_from",
            "valid_to",
            "source",
            "assumption_note",
        ],
    )

    # ----------------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------------

    validations = []

    validations.append(
        validation_row(
            "TEAM_COUNT",
            "PASS" if len(team_master) == 4 else "FAIL",
            len(team_master),
            4,
            "Exactly one prototype team is configured per approved work type.",
        )
    )

    validations.append(
        validation_row(
            "TEAM_WORK_TYPE_SCOPE",
            "PASS"
            if set(team_master["team_type"]) == set(APPROVED_WORK_TYPES)
            else "FAIL",
            sorted(team_master["team_type"].tolist()),
            sorted(APPROVED_WORK_TYPES),
            "Team types must cover the four frozen Step 13 operational categories.",
        )
    )

    validations.append(
        validation_row(
            "TEAM_ID_UNIQUENESS",
            "PASS"
            if int(team_master["team_id"].duplicated().sum()) == 0
            else "FAIL",
            int(team_master["team_id"].duplicated().sum()),
            0,
            "Each team must have a unique ID.",
        )
    )

    validations.append(
        validation_row(
            "TEAM_CAPACITY_POSITIVE",
            "PASS"
            if bool(
                pd.to_numeric(
                    team_master["worker_capacity"],
                    errors="coerce",
                ).gt(0).all()
            )
            else "FAIL",
            int(
                (
                    ~pd.to_numeric(
                        team_master["worker_capacity"],
                        errors="coerce",
                    ).gt(0)
                ).sum()
            ),
            0,
            "Every prototype team must have positive worker capacity.",
        )
    )

    validations.append(
        validation_row(
            "WORKING_HOURS_VALID",
            "PASS"
            if bool(
                team_master["working_start"].eq("08:00").all()
                and team_master["working_end"].eq("17:00").all()
            )
            else "FAIL",
            sorted(
                set(
                    zip(
                        team_master["working_start"],
                        team_master["working_end"],
                    )
                )
            ),
            "08:00-17:00",
            "Prototype working window from the project methodology.",
        )
    )

    validations.append(
        validation_row(
            "TEAM_SOURCE_LABEL",
            "PASS"
            if bool(
                team_master["source"]
                .eq(SYNTHETIC_TEAM_SOURCE)
                .all()
            )
            else "FAIL",
            sorted(team_master["source"].unique().tolist()),
            SYNTHETIC_TEAM_SOURCE,
            "Prototype assumptions must be explicitly labeled.",
        )
    )

    validations.append(
        validation_row(
            "DEPOT_NOT_INVENTED",
            "PASS"
            if bool(
                team_master["depot_lat"].eq("")
                .all()
                and team_master["depot_lon"].eq("")
                .all()
                and team_master["depot_status"]
                .eq(DEPOT_STATUS)
                .all()
            )
            else "FAIL",
            "blank coordinates / TO_BE_CONFIGURED",
            "blank coordinates / TO_BE_CONFIGURED",
            (
                "No authoritative depot coordinate exists in current inputs; "
                "do not invent one."
            ),
        )
    )

    # Every required equipment token observed for a work type must be present
    # on that work type's prototype team.
    missing_capability_rows = []

    for work_type in APPROVED_WORK_TYPES:
        team_id = (
            team_master.loc[
                team_master["team_type"].eq(work_type),
                "team_id",
            ]
            .iloc[0]
        )

        observed = equipment_by_work_type[work_type]

        configured = set(
            team_equipment.loc[
                team_equipment["team_id"].eq(team_id),
                "equipment_type",
            ]
            .astype(str)
        )

        missing = sorted(observed - configured)

        if missing:
            missing_capability_rows.append(
                {
                    "work_type": work_type,
                    "team_id": team_id,
                    "missing_equipment": "|".join(missing),
                }
            )

    validations.append(
        validation_row(
            "TEAM_EQUIPMENT_COVERAGE",
            "PASS" if not missing_capability_rows else "FAIL",
            len(missing_capability_rows),
            0,
            "Every observed equipment requirement must be available to its work-type team.",
        )
    )

    # Team capacity should cover the maximum single-job worker requirement
    # for its work type. Sequential jobs do not require summed capacity.
    capacity_gaps = []

    for team in TEAM_DEFINITIONS:
        work_type = team["team_type"]

        work_rows = resources[
            resources["work_type"].eq(work_type)
        ]

        max_workers = (
            float(work_rows["workers_required"].max())
            if not work_rows.empty
            else 0.0
        )

        if float(team["worker_capacity"]) < max_workers:
            capacity_gaps.append(
                {
                    "team_id": team["team_id"],
                    "work_type": work_type,
                    "team_capacity": team["worker_capacity"],
                    "max_observed_workers": max_workers,
                }
            )

    validations.append(
        validation_row(
            "TEAM_CAPACITY_COVERS_SINGLE_JOB",
            "PASS" if not capacity_gaps else "FAIL",
            len(capacity_gaps),
            0,
            (
                "Capacity is checked against the maximum simultaneous workers "
                "needed for one sequential job, not the sum of sequential jobs."
            ),
        )
    )

    validation_df = pd.DataFrame(validations)

    overall_pass = bool(
        validation_df["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------

    max_workers_by_type = (
        resources.groupby("work_type")["workers_required"]
        .max()
        .to_dict()
    )

    equipment_counts = {
        work_type: len(
            equipment_by_work_type.get(work_type, set())
        )
        for work_type in APPROVED_WORK_TYPES
    }

    summary = {
        "step": "13.3_team_master",
        "project_root": str(PROJECT_ROOT),
        "read_only": True,
        "database_used": False,
        "approved_work_types": APPROVED_WORK_TYPES,
        "teams": {
            "count": int(len(team_master)),
            "ids": team_master["team_id"].tolist(),
            "source": SYNTHETIC_TEAM_SOURCE,
        },
        "working_window": {
            "start": "08:00",
            "end": "17:00",
        },
        "worker_capacity_by_work_type": {
            row["team_type"]: int(row["worker_capacity"])
            for _, row in team_master.iterrows()
        },
        "max_observed_single_job_workers": {
            key: float(value)
            for key, value in max_workers_by_type.items()
        },
        "equipment_requirements_by_work_type": {
            key: sorted(value)
            for key, value in equipment_by_work_type.items()
        },
        "equipment_count_by_work_type": equipment_counts,
        "depot_policy": (
            "Depot coordinates remain blank and TO_BE_CONFIGURED because "
            "no authoritative depot coordinate is present in the current "
            "Step 13 inputs. Routing must resolve this before OSRM/OR-Tools."
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
            "team_master": str(TEAM_MASTER_FILE),
            "team_equipment": str(TEAM_EQUIPMENT_FILE),
            "validation": str(VALIDATION_FILE),
        },
        "next_step": (
            "After reviewing team configuration, build feasible team "
            "assignments before operational clustering/scheduling."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    team_master.to_csv(
        TEAM_MASTER_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    team_equipment.to_csv(
        TEAM_EQUIPMENT_FILE,
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

    # ----------------------------------------------------------------------
    # Console output
    # ----------------------------------------------------------------------

    print()
    print("-" * 80)
    print("TEAM MASTER")
    print("-" * 80)

    print(
        team_master[
            [
                "team_id",
                "team_name",
                "team_type",
                "worker_capacity",
                "working_start",
                "working_end",
                "depot_status",
                "source",
            ]
        ].to_string(index=False)
    )

    print()
    print("-" * 80)
    print("TEAM EQUIPMENT")
    print("-" * 80)

    if team_equipment.empty:
        print("No equipment assignments generated.")
    else:
        print(team_equipment.to_string(index=False))

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validations:
        print(
            f"{row['check_id']:42} : "
            f"{row['status']:5} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13.3 TEAM MASTER GATE: "
        + ("PASS" if overall_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(f"Team master     : {TEAM_MASTER_FILE}")
    print(f"Team equipment  : {TEAM_EQUIPMENT_FILE}")
    print(f"Validation      : {VALIDATION_FILE}")
    print(f"Summary JSON    : {SUMMARY_FILE}")

    if not overall_pass:
        raise RuntimeError(
            "Step 13.3 team master validation failed. "
            "Review the validation CSV before continuing."
        )


if __name__ == "__main__":
    main()
