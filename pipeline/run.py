"""Run the whole pipeline: ingest -> dbt build (models + tests) -> chart export.

Each step is idempotent, so the full run can be repeated safely.

    python -m pipeline.run --source-dir data/source
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from pipeline import ingest

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("run")


def dbt(*args: str, db: Path) -> None:
    env = {**os.environ, "ATP_DB_PATH": str(db.resolve())}
    cmd = ["dbt", *args, "--project-dir", str(ROOT / "dbt"), "--profiles-dir", str(ROOT / "dbt")]
    log.info("$ %s", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/source")
    parser.add_argument("--db", type=Path, default=ROOT / "data/warehouse.duckdb")
    parser.add_argument("--kaggle", nargs="?", const=ingest.KAGGLE_DATASET, metavar="OWNER/DATASET",
                        help="download the source data with the Kaggle API first")
    parser.add_argument("--min-year", type=int, default=1990)
    parser.add_argument("--full-refresh", action="store_true", help="rebuild incremental models")
    parser.add_argument("--skip-charts", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    ingest.run(args.source_dir, args.db, ROOT / "data/landing", args.min_year, kaggle_dataset=args.kaggle)

    build = ["build"] + (["--full-refresh"] if args.full_refresh else [])
    dbt("deps", db=args.db) if (ROOT / "dbt/packages.yml").exists() else None
    dbt(*build, db=args.db)

    if not args.skip_charts:
        from dashboard import export_charts

        export_charts.main(args.db, ROOT / "docs/img")


if __name__ == "__main__":
    sys.exit(main())
