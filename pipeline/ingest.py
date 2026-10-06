"""Ingestion: land raw ATP CSVs and load them into DuckDB, idempotently.

Source files follow Jeff Sackmann's ATP schema:
  atp_matches_YYYY.csv, atp_players.csv, atp_rankings_*.csv

Design choices
--------------
* Each source file is one *partition*. A manifest table stores the SHA-256 of
  every file already loaded.
* Re-running the job is safe: unchanged files are skipped, changed files have
  their partition deleted and re-inserted inside one transaction
  (delete-then-insert by `_source_file`). Running it twice never duplicates rows.
* Raw tables keep every column as text (`all_varchar`), plus lineage columns
  (`_source_file`, `_file_hash`, `_loaded_at`). Typing happens in dbt staging,
  so a bad value in the source never breaks the load.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import duckdb

log = logging.getLogger("ingest")

ENTITIES = {
    "matches": re.compile(r"^atp_matches_(\d{4})\.csv$"),
    "players": re.compile(r"^atp_players\.csv$"),
    "rankings": re.compile(r"^atp_rankings_(\d{2}s|current)\.csv$"),
}

KAGGLE_DATASET = "warcoder/atp-tennis-rankings-results-and-stats1968-2023"
# Optional remote mirror: any base URL serving the files by name.
DEFAULT_YEARS = range(1990, 2026)


@dataclass(frozen=True)
class SourceFile:
    entity: str
    path: Path

    @property
    def name(self) -> str:
        return self.path.name


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: Path) -> str | None:
    for entity, pattern in ENTITIES.items():
        if pattern.match(path.name):
            return entity
    return None


def download(base_url: str, landing: Path, years) -> None:
    """Fetch files from a mirror into the landing zone (skips files already there)."""
    names = [f"atp_matches_{y}.csv" for y in years] + ["atp_players.csv"]
    names += [f"atp_rankings_{d}.csv" for d in ("90s", "00s", "10s", "20s", "current")]
    for name in names:
        target = landing / name
        if target.exists():
            continue
        url = f"{base_url.rstrip('/')}/{name}"
        try:
            urllib.request.urlretrieve(url, target)
            log.info("downloaded %s", name)
        except Exception as exc:  # a missing year is not fatal
            log.warning("could not fetch %s (%s)", url, exc)


def download_kaggle(dataset: str) -> Path:
    """Pull a dataset with the Kaggle API (kagglehub caches it locally).

    Auth comes from the environment (KAGGLE_API_TOKEN, or ~/.kaggle/kaggle.json):
    credentials never live in this repo.
    """
    import kagglehub

    path = Path(kagglehub.dataset_download(dataset))
    log.info("kaggle dataset %s available at %s", dataset, path)
    return path


def land(source_dir: Path, landing: Path, min_year: int) -> list[SourceFile]:
    """Copy recognised files from a source folder into the landing zone."""
    landing.mkdir(parents=True, exist_ok=True)
    files: list[SourceFile] = []
    for path in sorted(source_dir.rglob("*.csv")):
        entity = classify(path)
        if entity is None:
            continue
        if entity == "matches" and int(ENTITIES["matches"].match(path.name).group(1)) < min_year:
            continue
        target = landing / path.name
        if not target.exists() or sha256(target) != sha256(path):
            shutil.copy2(path, target)
        files.append(SourceFile(entity, target))
    return files


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("create schema if not exists raw")
    con.execute(
        """
        create table if not exists raw._manifest (
            source_file varchar primary key,
            entity      varchar,
            file_hash   varchar,
            row_count   bigint,
            loaded_at   timestamp
        )
        """
    )


def load_file(con: duckdb.DuckDBPyConnection, src: SourceFile) -> str:
    """Load one partition. Returns 'skipped', 'loaded' or 'reloaded'."""
    file_hash = sha256(src.path)
    previous = con.execute(
        "select file_hash from raw._manifest where source_file = ?", [src.name]
    ).fetchone()
    if previous and previous[0] == file_hash:
        return "skipped"

    table = f"raw.atp_{src.entity}"
    read = (
        f"select *, ? as _source_file, ? as _file_hash, now() as _loaded_at "
        f"from read_csv('{src.path.as_posix()}', all_varchar = true, header = true)"
    )
    con.execute("begin transaction")
    try:
        exists = con.execute(
            "select count(*) from information_schema.tables "
            "where table_schema = 'raw' and table_name = ?",
            [f"atp_{src.entity}"],
        ).fetchone()[0]
        if not exists:
            con.execute(f"create table {table} as {read}", [src.name, file_hash])
        else:
            con.execute(f"delete from {table} where _source_file = ?", [src.name])
            con.execute(f"insert into {table} by name {read}", [src.name, file_hash])
        rows = con.execute(
            f"select count(*) from {table} where _source_file = ?", [src.name]
        ).fetchone()[0]
        con.execute(
            "insert or replace into raw._manifest values (?, ?, ?, ?, now())",
            [src.name, src.entity, file_hash, rows],
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return "reloaded" if previous else "loaded"


def run(
    source_dir: Path,
    db_path: Path,
    landing: Path,
    min_year: int,
    base_url: str | None = None,
    kaggle_dataset: str | None = None,
) -> dict:
    if kaggle_dataset:
        source_dir = download_kaggle(kaggle_dataset)
    elif base_url:
        landing.mkdir(parents=True, exist_ok=True)
        download(base_url, landing, DEFAULT_YEARS)
        source_dir = landing
    files = land(source_dir, landing, min_year)
    if not files:
        raise SystemExit(f"No ATP files found in {source_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {"skipped": 0, "loaded": 0, "reloaded": 0}
    with duckdb.connect(str(db_path)) as con:
        ensure_schema(con)
        for src in files:
            outcome = load_file(con, src)
            stats[outcome] += 1
            log.info("%-28s %s", src.name, outcome)
    log.info("ingest done: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-dir", type=Path, default=Path("data/source"))
    parser.add_argument("--landing", type=Path, default=Path("data/landing"))
    parser.add_argument("--db", type=Path, default=Path("data/warehouse.duckdb"))
    parser.add_argument("--min-year", type=int, default=1990)
    parser.add_argument("--kaggle", nargs="?", const=KAGGLE_DATASET, metavar="OWNER/DATASET",
                        help=f"download from Kaggle first (default dataset: {KAGGLE_DATASET})")
    parser.add_argument("--base-url", help="optional mirror to download the CSVs from")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.source_dir, args.db, args.landing, args.min_year, args.base_url, args.kaggle)


if __name__ == "__main__":
    main()
