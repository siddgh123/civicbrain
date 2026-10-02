from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_master_issue_validation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_master_issue_summary.csv"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_master_issue_config.json"
)


@dataclass
class Complaint:
    complaint_id: str
    decision: str
    matched_master_id: str | None
    expected_master_id: str | None
    expected_action: str
    note: str


class MasterIssueManager:
    """
    Deterministic prototype for validating Step 12 master-issue rules.

    Rules:
      1. DUPLICATE may attach to an existing master.
      2. UNCERTAIN never auto-merges; goes to review queue.
      3. NOT_DUPLICATE starts a new master issue.
      4. The original complaint record remains preserved.
      5. A duplicate attaches to the master directly associated with the
         verified matched complaint/master. No blind transitive chaining.
    """

    def __init__(self) -> None:
        self.masters: dict[str, list[str]] = {}
        self.complaint_to_master: dict[str, str] = {}
        self.review_queue: list[str] = []
        self.next_master_number = 1
        self.original_complaints: set[str] = set()

    def _new_master(self, complaint_id: str) -> str:
        master_id = f"M{self.next_master_number:03d}"
        self.next_master_number += 1

        self.masters[master_id] = [complaint_id]
        self.complaint_to_master[complaint_id] = master_id
        self.original_complaints.add(complaint_id)

        return master_id

    def create_initial_complaint(self, complaint_id: str) -> str:
        return self._new_master(complaint_id)

    def process_complaint(
        self,
        complaint_id: str,
        decision: str,
        matched_complaint_id: str | None = None,
    ) -> dict:
        if complaint_id in self.original_complaints:
            return {
                "action": "REJECT_DUPLICATE_COMPLAINT_ID",
                "master_id": self.complaint_to_master.get(
                    complaint_id
                ),
            }

        decision = decision.upper().strip()

        if decision == "NOT_DUPLICATE":
            master_id = self._new_master(complaint_id)

            return {
                "action": "CREATE_NEW_MASTER",
                "master_id": master_id,
            }

        if decision == "UNCERTAIN":
            self.original_complaints.add(complaint_id)
            self.review_queue.append(complaint_id)

            return {
                "action": "SEND_TO_REVIEW",
                "master_id": None,
            }

        if decision != "DUPLICATE":
            raise ValueError(
                f"Unsupported decision: {decision}"
            )

        if matched_complaint_id is None:
            self.original_complaints.add(complaint_id)
            self.review_queue.append(complaint_id)

            return {
                "action": "SEND_TO_REVIEW_MISSING_MATCH",
                "master_id": None,
            }

        matched_master_id = self.complaint_to_master.get(
            matched_complaint_id
        )

        # Critical chain-protection rule:
        # If the matched complaint itself is not attached to a verified
        # master, do not auto-merge.
        if matched_master_id is None:
            self.original_complaints.add(complaint_id)
            self.review_queue.append(complaint_id)

            return {
                "action": "SEND_TO_REVIEW_UNRESOLVED_MATCH",
                "master_id": None,
            }

        self.masters[
            matched_master_id
        ].append(complaint_id)

        self.complaint_to_master[
            complaint_id
        ] = matched_master_id

        self.original_complaints.add(complaint_id)

        return {
            "action": "ATTACH_EXISTING_MASTER",
            "master_id": matched_master_id,
        }


def run_scenario(
    name: str,
    manager: MasterIssueManager,
    complaint_id: str,
    decision: str,
    matched_complaint_id: str | None,
    expected_action: str,
    expected_master_id: str | None,
    note: str,
) -> dict:
    result = manager.process_complaint(
        complaint_id,
        decision,
        matched_complaint_id,
    )

    actual_master_id = result["master_id"]

    passed = (
        result["action"] == expected_action
        and actual_master_id == expected_master_id
        and complaint_id in manager.original_complaints
    )

    return {
        "scenario": name,
        "complaint_id": complaint_id,
        "decision": decision,
        "matched_complaint_id": matched_complaint_id or "",
        "expected_action": expected_action,
        "actual_action": result["action"],
        "expected_master_id": expected_master_id or "",
        "actual_master_id": actual_master_id or "",
        "original_complaint_preserved": (
            complaint_id in manager.original_complaints
        ),
        "passed": passed,
        "note": note,
    }


def main() -> None:
    print("=" * 80)
    print(
        "CIVICBRAIN STEP 12 — MASTER ISSUE ASSIGNMENT VALIDATION"
    )
    print("=" * 80)

    manager = MasterIssueManager()
    rows: list[dict] = []

    print()
    print("MASTER ISSUE RULES UNDER TEST")
    print("-" * 80)
    print("1. First independent issue -> create new Master")
    print("2. DUPLICATE + verified match -> attach existing Master")
    print("3. UNCERTAIN -> manual review, no auto-merge")
    print("4. NOT_DUPLICATE -> create separate Master")
    print("5. Original complaint records remain preserved")
    print("6. No blind transitive duplicate chaining")
    print("7. Missing/unresolved match -> manual review")

    # ------------------------------------------------------------
    # Scenario 1: first complaint creates M001
    # ------------------------------------------------------------
    m001 = manager.create_initial_complaint("C001")

    rows.append(
        {
            "scenario": "S01_FIRST_COMPLAINT",
            "complaint_id": "C001",
            "decision": "INITIAL",
            "matched_complaint_id": "",
            "expected_action": "CREATE_NEW_MASTER",
            "actual_action": "CREATE_NEW_MASTER",
            "expected_master_id": "M001",
            "actual_master_id": m001,
            "original_complaint_preserved": True,
            "passed": m001 == "M001",
            "note": "First complaint establishes the first master issue",
        }
    )

    # ------------------------------------------------------------
    # Scenario 2: direct duplicate attaches to M001
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S02_DIRECT_DUPLICATE",
            manager,
            "C018",
            "DUPLICATE",
            "C001",
            "ATTACH_EXISTING_MASTER",
            "M001",
            "C018 is a verified duplicate of C001",
        )
    )

    # ------------------------------------------------------------
    # Scenario 3: another duplicate attaches to same M001
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S03_SECOND_DUPLICATE",
            manager,
            "C031",
            "DUPLICATE",
            "C018",
            "ATTACH_EXISTING_MASTER",
            "M001",
            "C031 matches a complaint already linked to M001",
        )
    )

    # ------------------------------------------------------------
    # Scenario 4: independent complaint creates M002
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S04_SEPARATE_ISSUE",
            manager,
            "C044",
            "NOT_DUPLICATE",
            None,
            "CREATE_NEW_MASTER",
            "M002",
            "Distinct physical issue",
        )
    )

    # ------------------------------------------------------------
    # Scenario 5: duplicate of M002 complaint attaches to M002
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S05_DUPLICATE_OF_SECOND_MASTER",
            manager,
            "C052",
            "DUPLICATE",
            "C044",
            "ATTACH_EXISTING_MASTER",
            "M002",
            "Duplicate belongs to the second physical issue",
        )
    )

    # ------------------------------------------------------------
    # Scenario 6: uncertain does not auto-merge into M001
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S06_UNCERTAIN",
            manager,
            "C060",
            "UNCERTAIN",
            "C001",
            "SEND_TO_REVIEW",
            None,
            "Borderline case must not auto-merge",
        )
    )

    # ------------------------------------------------------------
    # Scenario 7: NOT_DUPLICATE creates M003
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S07_THIRD_SEPARATE_ISSUE",
            manager,
            "C071",
            "NOT_DUPLICATE",
            "C001",
            "CREATE_NEW_MASTER",
            "M003",
            "Near topic but distinct physical issue",
        )
    )

    # ------------------------------------------------------------
    # Scenario 8: missing match for DUPLICATE -> review
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S08_DUPLICATE_WITHOUT_MATCH",
            manager,
            "C080",
            "DUPLICATE",
            None,
            "SEND_TO_REVIEW_MISSING_MATCH",
            None,
            "System cannot auto-attach without a matched complaint/master",
        )
    )

    # ------------------------------------------------------------
    # Scenario 9: unresolved matched complaint -> review
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S09_UNRESOLVED_MATCH",
            manager,
            "C090",
            "DUPLICATE",
            "C999",
            "SEND_TO_REVIEW_UNRESOLVED_MATCH",
            None,
            "Unknown matched complaint must not create an unsafe merge",
        )
    )

    # ------------------------------------------------------------
    # Scenario 10: transitive-chain protection
    #
    # C100 will be attached to M003.
    # C101 claims duplicate of C100 -> still M003 because C100 has
    # a verified master association.
    # The system does not infer C001~C071 merely because another link
    # exists; it only follows the verified complaint -> master mapping.
    # ------------------------------------------------------------
    rows.append(
        run_scenario(
            "S10_VERIFIED_CHAIN_TO_EXISTING_MASTER",
            manager,
            "C100",
            "DUPLICATE",
            "C071",
            "ATTACH_EXISTING_MASTER",
            "M003",
            "Verified master association exists for the matched complaint",
        )
    )

    # ------------------------------------------------------------
    # Scenario 11: duplicate complaint IDs are never recreated
    # ------------------------------------------------------------
    duplicate_id_result = manager.process_complaint(
        "C018",
        "DUPLICATE",
        "C001",
    )

    rows.append(
        {
            "scenario": "S11_DUPLICATE_ID_PROTECTION",
            "complaint_id": "C018",
            "decision": "DUPLICATE",
            "matched_complaint_id": "C001",
            "expected_action": "REJECT_DUPLICATE_COMPLAINT_ID",
            "actual_action": duplicate_id_result["action"],
            "expected_master_id": "M001",
            "actual_master_id": duplicate_id_result["master_id"] or "",
            "original_complaint_preserved": (
                "C018" in manager.original_complaints
            ),
            "passed": (
                duplicate_id_result["action"]
                == "REJECT_DUPLICATE_COMPLAINT_ID"
                and duplicate_id_result["master_id"] == "M001"
            ),
            "note": "Existing complaint record must not be recreated",
        }
    )

    # ------------------------------------------------------------
    # Scenario 12: ensure the uncertain item is still only in review
    # ------------------------------------------------------------
    uncertain_still_review = (
        "C060" in manager.review_queue
        and "C060" not in manager.complaint_to_master
    )

    rows.append(
        {
            "scenario": "S12_UNCERTAIN_REVIEW_QUEUE",
            "complaint_id": "C060",
            "decision": "UNCERTAIN",
            "matched_complaint_id": "C001",
            "expected_action": "REMAIN_IN_REVIEW_QUEUE",
            "actual_action": (
                "REMAIN_IN_REVIEW_QUEUE"
                if uncertain_still_review
                else "NOT_IN_REVIEW_QUEUE"
            ),
            "expected_master_id": "",
            "actual_master_id": (
                manager.complaint_to_master.get("C060") or ""
            ),
            "original_complaint_preserved": (
                "C060" in manager.original_complaints
            ),
            "passed": uncertain_still_review,
            "note": "UNCERTAIN must never be auto-attached",
        }
    )

    results_df = __import__("pandas").DataFrame(rows)

    category = {
        "create_new_master": results_df[
            results_df["expected_action"] == "CREATE_NEW_MASTER"
        ],
        "duplicate_attachment": results_df[
            results_df["expected_action"]
            == "ATTACH_EXISTING_MASTER"
        ],
        "uncertain_safety": results_df[
            results_df["scenario"].isin(
                [
                    "S06_UNCERTAIN",
                    "S12_UNCERTAIN_REVIEW_QUEUE",
                ]
            )
        ],
        "invalid_match_safety": results_df[
            results_df["scenario"].isin(
                [
                    "S08_DUPLICATE_WITHOUT_MATCH",
                    "S09_UNRESOLVED_MATCH",
                ]
            )
        ],
        "duplicate_id_protection": results_df[
            results_df["scenario"] == "S11_DUPLICATE_ID_PROTECTION"
        ],
    }

    summary_rows = []

    for name, frame in category.items():
        summary_rows.append(
            {
                "category": name,
                "total_cases": len(frame),
                "passed": int(frame["passed"].sum()),
                "failed": int((~frame["passed"]).sum()),
            }
        )

    summary_df = __import__("pandas").DataFrame(summary_rows)

    total_cases = len(results_df)
    passed = int(results_df["passed"].sum())
    failed = int((~results_df["passed"]).sum())

    print()
    print("=" * 80)
    print("MASTER ISSUE VALIDATION SUMMARY")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    print()
    print(f"Total cases                 : {total_cases}")
    print(f"Passed                      : {passed}")
    print(f"Failed                      : {failed}")

    if failed:
        print()
        print("FAILED CASES")
        print("-" * 80)
        print(
            results_df.loc[
                ~results_df["passed"],
                [
                    "scenario",
                    "expected_action",
                    "actual_action",
                    "expected_master_id",
                    "actual_master_id",
                    "note",
                ],
            ].to_string(index=False)
        )

    print()
    print("=" * 80)
    print("MASTER STATE AFTER VALIDATION")
    print("=" * 80)

    for master_id, complaints in manager.masters.items():
        print(
            f"{master_id}: "
            + ", ".join(complaints)
        )

    print()
    print(
        "Review queue: "
        + (
            ", ".join(manager.review_queue)
            if manager.review_queue
            else "EMPTY"
        )
    )

    print()
    print(
        f"Original complaint records preserved: "
        f"{len(manager.original_complaints)}"
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    config = {
        "status": "experimental",
        "time_window_days": 7,
        "text_weight": 0.70,
        "distance_weight": 0.20,
        "recency_weight": 0.10,
        "duplicate_threshold": 0.59,
        "uncertain_lower_bound": 0.55,
        "master_rules": {
            "duplicate": "Attach to an existing verified master",
            "uncertain": "Manual review; no automatic merge",
            "not_duplicate": "Create a new master issue",
            "missing_or_unresolved_match": "Manual review",
            "original_complaints": "Always preserve",
            "transitive_chaining": (
                "Never infer blindly; require a verified complaint-to-master association"
            ),
        },
        "validation_cases": total_cases,
        "passed_cases": passed,
        "failed_cases": failed,
        "final_status": (
            "PASS"
            if failed == 0
            else "FAIL"
        ),
        "note": (
            "This validates deterministic master-issue assignment logic "
            "using constructed scenarios. It does not establish real TDMC "
            "duplicate-detection accuracy and does not freeze the production "
            "database/API workflow."
        ),
    }

    CONFIG_FILE.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("OUTPUT FILES")
    print("=" * 80)
    print(f"Case results                 : {OUTPUT_FILE}")
    print(f"Summary                      : {SUMMARY_FILE}")
    print(f"Master rules config          : {CONFIG_FILE}")

    print()
    if failed == 0:
        print("ALL MASTER ISSUE VALIDATION TESTS PASSED")
    else:
        print("MASTER ISSUE VALIDATION FOUND FAILURES — DO NOT FREEZE")

    print()
    print("=" * 80)
    print("MASTER ISSUE ASSIGNMENT VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
