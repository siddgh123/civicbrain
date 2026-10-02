import csv
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

COMPLAINT_FILE = (
    BASE_DIR
    / "data"
    / "complaints"
    / "verified"
    / "complaints_verified.csv"
)

ASSUMPTION_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "raw"
    / "resource_assumptions.csv"
)

EQUIPMENT_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "raw"
    / "equipment_master.csv"
)

MATERIAL_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "raw"
    / "material_master.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
)

OUTPUT_FILE = OUTPUT_DIR / "resource_dataset.csv"


# ============================================================
# LABOUR RATES
# Maharashtra PWD SSR 2022-23 reference
# ============================================================

HEAVY_MAZDOOR_DAY = 614
LIGHT_MAZDOOR_DAY = 568

WORKING_HOURS_PER_DAY = 8

HEAVY_MAZDOOR_HOUR = (
    HEAVY_MAZDOOR_DAY / WORKING_HOURS_PER_DAY
)

LIGHT_MAZDOOR_HOUR = (
    LIGHT_MAZDOOR_DAY / WORKING_HOURS_PER_DAY
)


# ============================================================
# PROJECT ASSUMPTIONS
# ============================================================

TRANSPORT_COST = 500

# 75 mm repair depth for pothole / road-damage
WORK_DEPTH_M = 0.075

# Engineering assumption for converting road-work volume
# into approximate bituminous mix mass.
MIX_DENSITY_TONNES_PER_M3 = 2.35

# Approximate binder proportion used only for this
# synthetic project estimation.
BITUMEN_CONTENT_RATIO = 0.05


# Municipal Council adjustment from applicable SSR provision.
# It is documented here but NOT blindly applied to every rate.
MUNICIPAL_COUNCIL_FACTOR = 1.04


def load_csv(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def calculate_labour_cost(workers, duration_hours):

    if workers == 2:

        labour_cost = (
            workers
            * duration_hours
            * LIGHT_MAZDOOR_HOUR
        )

    elif workers == 3:

        labour_cost = (
            2
            * duration_hours
            * LIGHT_MAZDOOR_HOUR
            + duration_hours
            * HEAVY_MAZDOOR_HOUR
        )

    else:

        labour_cost = (
            2
            * duration_hours
            * LIGHT_MAZDOOR_HOUR
            + (workers - 2)
            * duration_hours
            * HEAVY_MAZDOOR_HOUR
        )

    return round(labour_cost, 2)


def calculate_material_cost(
    issue_type,
    estimated_area,
    material_map
):

    material_cost = 0.0

    # Area-based work volume
    work_volume_m3 = (
        estimated_area * WORK_DEPTH_M
    )

    # Approximate total bituminous mix quantity
    mix_quantity_mt = (
        work_volume_m3
        * MIX_DENSITY_TONNES_PER_M3
    )

    # Approximate bitumen quantity
    bitumen_quantity_mt = (
        mix_quantity_mt
        * BITUMEN_CONTENT_RATIO
    )

    for material in material_map.get(
        issue_type,
        []
    ):

        unit = material["unit"].strip().lower()
        quantity_basis = material.get(
            "quantity_basis",
            ""
        ).strip().lower()

        unit_cost = float(
            material["cost"]
        )

        # Bitumen / MT based material
        if (
            unit == "mt"
            and quantity_basis == "per_m3_work"
        ):

            quantity_mt = bitumen_quantity_mt

            material_cost += (
                quantity_mt
                * unit_cost
            )

        # m2 based material
        elif unit == "m2":

            material_cost += (
                estimated_area
                * unit_cost
            )

        # meter based material
        elif unit == "meter":

            material_cost += (
                estimated_area
                * unit_cost
            )

        # Unit-based material
        elif unit == "unit":

            material_cost += unit_cost

        # Unsupported unit is ignored
        else:
            continue

    return round(material_cost, 2)


def main():

    complaints = load_csv(
        COMPLAINT_FILE
    )

    assumptions = load_csv(
        ASSUMPTION_FILE
    )

    equipment = load_csv(
        EQUIPMENT_FILE
    )

    materials = load_csv(
        MATERIAL_FILE
    )

    # ========================================================
    # ASSUMPTION LOOKUP
    # ========================================================

    assumption_map = {}

    for row in assumptions:

        key = (
            row["issue_type"],
            row["severity"]
        )

        assumption_map[key] = (
            float(row["min_area_m2"]),
            float(row["max_area_m2"])
        )

    # ========================================================
    # EQUIPMENT LOOKUP
    # ========================================================

    equipment_map = {}

    for row in equipment:

        issue = row["issue_type"]

        if issue not in equipment_map:
            equipment_map[issue] = []

        equipment_map[issue].append(
            {
                "name": row["equipment_name"],
                "cost": float(row["unit_cost"])
            }
        )

    # ========================================================
    # MATERIAL LOOKUP
    # ========================================================

    material_map = {}

    for row in materials:

        issue = row["issue_type"]

        if issue not in material_map:
            material_map[issue] = []

        material_map[issue].append(
            {
                "name": row["material_name"],
                "cost": float(row["unit_cost"]),
                "unit": row["unit"],
                "quantity_basis": row.get(
                    "quantity_basis",
                    ""
                )
            }
        )

    output_rows = []

    # ========================================================
    # PROCESS ALL 500 COMPLAINTS
    # ========================================================

    for complaint in complaints:

        issue_type = complaint["category"]

        complaint_id = complaint["complaint_id"]

        numeric_id = int(
            complaint_id
        )

        # ----------------------------------------------------
        # Synthetic severity
        # ----------------------------------------------------

        severity_values = [
            "Low",
            "Medium",
            "High"
        ]

        severity = severity_values[
            (numeric_id - 1) % 3
        ]

        # ----------------------------------------------------
        # Estimated area
        # ----------------------------------------------------

        min_area, max_area = (
            assumption_map[
                (issue_type, severity)
            ]
        )

        rng = random.Random(
            numeric_id
        )

        estimated_area = round(
            rng.uniform(
                min_area,
                max_area
            ),
            2
        )

        # ----------------------------------------------------
        # Workers
        # ----------------------------------------------------

        workers = {
            "Low": 2,
            "Medium": 3,
            "High": 4
        }[severity]

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        severity_extra_hours = {
            "Low": 1,
            "Medium": 2,
            "High": 3
        }[severity]

        duration_hours = round(
            max(
                2,
                (estimated_area / 2)
                + severity_extra_hours
            ),
            1
        )

        # ----------------------------------------------------
        # Labour cost
        # ----------------------------------------------------

        labour_cost = calculate_labour_cost(
            workers,
            duration_hours
        )

        # ----------------------------------------------------
        # Material cost
        # ----------------------------------------------------

        material_cost = calculate_material_cost(
            issue_type,
            estimated_area,
            material_map
        )

        # ----------------------------------------------------
        # Equipment
        # ----------------------------------------------------

        required_equipment = (
            equipment_map.get(
                issue_type,
                []
            )
        )

        equipment_cost = round(
            sum(
                item["cost"]
                for item in required_equipment
            ),
            2
        )

        equipment_names = "; ".join(
            item["name"]
            for item in required_equipment
        )

        # ----------------------------------------------------
        # Total cost
        # ----------------------------------------------------

        total_cost = round(
            labour_cost
            + material_cost
            + equipment_cost
            + TRANSPORT_COST,
            2
        )

        # ----------------------------------------------------
        # Output row
        # ----------------------------------------------------

        output_rows.append(
            {
                "complaint_id":
                    complaint_id,

                "issue_type":
                    issue_type,

                "latitude":
                    complaint["latitude"],

                "longitude":
                    complaint["longitude"],

                "created_at":
                    complaint["created_at"],

                "status":
                    complaint["status"],

                "is_synthetic":
                    complaint["is_synthetic"],

                "severity":
                    severity,

                "estimated_area":
                    estimated_area,

                "estimated_workers":
                    workers,

                "estimated_duration_hours":
                    duration_hours,

                "labour_cost":
                    labour_cost,

                "material_cost":
                    material_cost,

                "equipment_cost":
                    equipment_cost,

                "transport_cost":
                    TRANSPORT_COST,

                "total_cost":
                    total_cost,

                "required_equipment":
                    equipment_names,

                "severity_source":
                    "synthetic_assumption",

                "area_source":
                    "synthetic_assumption"
            }
        )

    # ========================================================
    # WRITE OUTPUT
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "complaint_id",
        "issue_type",
        "latitude",
        "longitude",
        "created_at",
        "status",
        "is_synthetic",
        "severity",
        "estimated_area",
        "estimated_workers",
        "estimated_duration_hours",
        "labour_cost",
        "material_cost",
        "equipment_cost",
        "transport_cost",
        "total_cost",
        "required_equipment",
        "severity_source",
        "area_source"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(output_rows)

    print(
        "RESOURCE DATASET CREATED"
    )

    print(
        f"Input complaints: "
        f"{len(complaints)}"
    )

    print(
        f"Complaints processed: "
        f"{len(output_rows)}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()