"""End-to-end tests on a tiny fixture: ingestion is idempotent and dbt builds cleanly."""

import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

from pipeline import ingest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


@pytest.fixture()
def workdir(tmp_path):
    src = tmp_path / "source"
    shutil.copytree(FIXTURES, src)
    return tmp_path, src


def counts(db: Path) -> tuple:
    with duckdb.connect(str(db), read_only=True) as con:
        return con.execute(
            "select (select count(*) from raw.atp_matches), (select count(*) from raw.atp_players), "
            "(select count(*) from raw.atp_rankings)"
        ).fetchone()


def test_ingest_is_idempotent(workdir):
    tmp, src = workdir
    db = tmp / "w.duckdb"
    first = ingest.run(src, db, tmp / "landing", 1990)
    before = counts(db)
    second = ingest.run(src, db, tmp / "landing", 1990)
    assert first["loaded"] == 5
    assert second == {"skipped": 5, "loaded": 0, "reloaded": 0}
    assert counts(db) == before


def test_changed_file_replaces_its_partition(workdir):
    tmp, src = workdir
    db = tmp / "w.duckdb"
    ingest.run(src, db, tmp / "landing", 1990)
    before = counts(db)
    f = src / "atp_matches_2024.csv"
    f.write_text(f.read_text().replace("6-1 6-2 6-7 6-3", "6-1 6-2 6-7(5) 6-3"))
    stats = ingest.run(src, db, tmp / "landing", 1990)
    assert stats["reloaded"] == 1
    assert counts(db) == before  # replaced, not appended
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("select count(*) from raw.atp_matches where score = '6-1 6-2 6-7(5) 6-3'").fetchone()[0] == 1


def test_dbt_build_passes(workdir):
    tmp, src = workdir
    db = tmp / "w.duckdb"
    ingest.run(src, db, tmp / "landing", 1990)
    env = {**os.environ, "ATP_DB_PATH": str(db)}
    for _ in range(2):  # second run exercises the incremental path
        subprocess.run(
            ["dbt", "build", "--project-dir", str(ROOT / "dbt"), "--profiles-dir", str(ROOT / "dbt")],
            check=True, env=env,
        )
