"""CivicBrain | scripts/audit/export_db_complaints.py

Exports the complaints that are IN THE DATABASE to a CSV, so the research scripts of Steps 10, 11
and 13 can be re-run on exactly the rows the app uses (docs/09_BUILD_PLAN.md P1 step 4, "problem 1":
the stored step13_* results were built from a different CSV version of the complaints).

Run with the AI-service venv (psycopg is installed there), from the repo root:
    ai-service\\.venv\\Scripts\\python scripts\\audit\\export_db_complaints.py
    ai-service\\.venv\\Scripts\\python scripts\\audit\\export_db_complaints.py `
        --like data\\complaints\\verified\\complaints_verified.csv --out data\\complaints\\exports\\db_complaints_like_step8.csv
    (PowerShell: the backtick ` continues the line; or write it on one line)

--like <csv>  writes exactly the columns (names and order) of an existing input CSV, so a Step script
              can read the export unchanged. Common name variants are matched automatically
              (lat/latitude, lon/lng/longitude, ward/ward_no/ward_number, category/category_name, ...).
              Columns that cannot be matched stop the export and are listed; map them with
              --map <csv_column>=<export_column> (repeatable) after checking what they mean.
Connection: reads DB_HOST, DB_PORT, DB_NAME, DB_AI_USER, DB_AI_PASSWORD from the environment or from
.env in the repo root (read-only use; the civicbrain_ai role can SELECT every table).
By default only the research rows (is_synthetic = true) are exported; --all adds real complaints and
then writes to storage/exports/ (git-ignored) because real complaints are personal data.
The script never prints the password and never writes to the database.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_QUOTED = re.compile(r"""^(["'])(.*?)\1(?:\s+#.*)?$""")

SQL = """
SELECT c.complaint_id,
       c.public_ref,
       c.title,
       c.description,
       c.category_id,
       cc.category_name,
       cc.work_type_code,
       c.status,
       round(ST_Y(c.location)::numeric, 7)  AS latitude,
       round(ST_X(c.location)::numeric, 7)  AS longitude,
       c.ward_id,
       w.ward_number,
       w.ward_name,
       c.road_id,
       c.poi_id,
       c.is_outside_boundary,
       c.submitted_at,
       c.duplicate_status,
       c.master_complaint_id,
       c.matched_complaint_id,
       c.current_priority_score,
       c.current_priority_level,
       c.landmark,
       c.address_text,
       c.is_synthetic
  FROM complaints c
  JOIN complaint_categories cc ON cc.category_id = c.category_id
  LEFT JOIN wards w ON w.ward_id = c.ward_id
 WHERE (%(all)s OR c.is_synthetic)
 ORDER BY c.complaint_id
"""

# export column -> accepted names in an existing CSV header (compared case-insensitively)
ALIASES: dict[str, list[str]] = {
    "complaint_id": ["complaint_id", "id", "complaintid"],
    "public_ref": ["public_ref", "ref", "reference"],
    "title": ["title", "complaint_title", "subject"],
    "description": ["description", "text", "complaint_text", "details", "complaint_description"],
    "category_id": ["category_id"],
    "category_name": ["category_name", "category", "complaint_category", "issue_type", "complaint_type"],
    "work_type_code": ["work_type_code", "work_type"],
    "status": ["status", "complaint_status"],
    "latitude": ["latitude", "lat", "gps_lat"],
    "longitude": ["longitude", "lon", "lng", "long", "gps_lon", "gps_lng"],
    "ward_id": ["ward_id"],
    "ward_number": ["ward_number", "ward", "ward_no", "ward_num"],
    "ward_name": ["ward_name"],
    "road_id": ["road_id"],
    "poi_id": ["poi_id"],
    "is_outside_boundary": ["is_outside_boundary", "outside_boundary"],
    "submitted_at": ["submitted_at", "created_at", "timestamp", "reported_at", "date_time", "datetime", "complaint_time"],
    "duplicate_status": ["duplicate_status"],
    "master_complaint_id": ["master_complaint_id", "master_id"],
    "matched_complaint_id": ["matched_complaint_id"],
    "current_priority_score": ["current_priority_score", "priority_score"],
    "current_priority_level": ["current_priority_level", "priority_level", "priority"],
    "landmark": ["landmark"],
    "address_text": ["address_text", "address"],
    "is_synthetic": ["is_synthetic", "synthetic"],
}


def load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE, # comments, optional quotes. Existing env vars win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        m = _QUOTED.match(val)
        if m:
            val = m.group(2)
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, val)


def build_mapping(header: list[str], extra: dict[str, str]) -> tuple[list[tuple[str, str]], list[str]]:
    """Returns ([(csv_column, export_column)], [unmatched csv columns])."""
    lookup: dict[str, str] = {}
    for export_col, names in ALIASES.items():
        for name in names:
            lookup.setdefault(name.lower(), export_col)
    pairs: list[tuple[str, str]] = []
    unmatched: list[str] = []
    for col in header:
        if col in extra:
            pairs.append((col, extra[col]))
        elif col.strip().lower() in lookup:
            pairs.append((col, lookup[col.strip().lower()]))
        else:
            unmatched.append(col)
    return pairs, unmatched


NAIVE_TIMES = False


def fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        if NAIVE_TIMES:
            value = value.replace(tzinfo=None)
        return value.isoformat(sep=" ")
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None, help="output CSV (default data/complaints/exports/db_complaints_<date>.csv)")
    ap.add_argument("--like", type=Path, default=None, help="copy the column names/order of this CSV")
    ap.add_argument("--map", action="append", default=[], metavar="CSV_COL=EXPORT_COL", help="manual column mapping for --like")
    ap.add_argument("--all", action="store_true", help="include real (non-synthetic) complaints")
    ap.add_argument("--timezone", default="Asia/Kolkata", help="time zone for submitted_at (default Asia/Kolkata)")
    ap.add_argument("--naive-times", action="store_true", help="write times without the +05:30 offset")
    args = ap.parse_args(argv)

    export_cols = list(ALIASES.keys())
    extra: dict[str, str] = {}
    for item in args.map:
        if "=" not in item:
            ap.error(f"--map expects CSV_COL=EXPORT_COL, got {item!r}")
        left, right = (s.strip() for s in item.split("=", 1))
        if right not in export_cols:
            ap.error(f"--map target {right!r} is not an export column: {', '.join(export_cols)}")
        extra[left] = right

    pairs: list[tuple[str, str]] | None = None
    if args.like:
        with args.like.open(newline="", encoding="utf-8-sig") as fh:
            header = next(csv.reader(fh), [])
        if not header:
            print(f"ERROR: {args.like} has no header row", file=sys.stderr)
            return 2
        pairs, unmatched = build_mapping(header, extra)
        if unmatched:
            print("ERROR: these columns of the --like CSV have no match in the database export:", file=sys.stderr)
            for col in unmatched:
                print(f"   {col}", file=sys.stderr)
            print("Check what each one means in the Step script, then add --map <column>=<export column>.", file=sys.stderr)
            print(f"Export columns: {', '.join(export_cols)}", file=sys.stderr)
            return 2

    load_dotenv(REPO_ROOT / ".env")
    missing = [k for k in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_AI_USER", "DB_AI_PASSWORD") if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing settings {', '.join(missing)} (set them in .env)", file=sys.stderr)
        return 2

    try:
        import psycopg  # installed in ai-service/.venv
        from psycopg.conninfo import make_conninfo
    except ImportError:
        print("ERROR: psycopg not found - run with ai-service\\.venv\\Scripts\\python", file=sys.stderr)
        return 2

    default_dir = REPO_ROOT / ("storage/exports" if args.all else "data/complaints/exports")
    stamp = f"{dt.datetime.now().astimezone():%Y%m%d}"
    out = args.out or default_dir / f"db_complaints{'_all' if args.all else ''}_{stamp}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    conninfo = make_conninfo(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_AI_USER"], password=os.environ["DB_AI_PASSWORD"], connect_timeout=10,
        application_name="civicbrain-export")
    global NAIVE_TIMES
    NAIVE_TIMES = args.naive_times
    with psycopg.connect(conninfo) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('TimeZone', %s, false)", (args.timezone,))
            cur.execute(SQL, {"all": args.all})
            names = [d.name for d in cur.description]
            rows = cur.fetchall()

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if pairs is None:
            writer.writerow(names)
            for row in rows:
                writer.writerow([fmt(v) for v in row])
        else:
            idx = {n: i for i, n in enumerate(names)}
            writer.writerow([csv_col for csv_col, _ in pairs])
            for row in rows:
                writer.writerow([fmt(row[idx[export_col]]) for _, export_col in pairs])

    by_type: dict[str, int] = {}
    for row in rows:
        wt = row[names.index("work_type_code")]
        by_type[wt] = by_type.get(wt, 0) + 1
    print(f"Wrote {len(rows)} complaints to {out}")
    print("By work type: " + ", ".join(f"{k}={v}" for k, v in sorted(by_type.items())))
    if pairs is not None:
        print("Column mapping: " + ", ".join(f"{c}<-{e}" for c, e in pairs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
