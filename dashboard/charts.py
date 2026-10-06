"""Shared chart definitions (used by the Streamlit app and the static export).

Colour follows the player, never the rank: each focus player owns one fixed
categorical slot (from dbt seed `players_of_interest.colour_slot`).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

# Validated categorical palette, light mode (slots 1-7, fixed order).
SLOT_COLOURS = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100", 5: "#e87ba4", 6: "#008300", 7: "#4a3aa7"}
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"
SURFACE = "#fcfcfb"

METRICS = {
    "cum_slam_titles": ("Grand Slam titles (cumulative)", "Grand Slam titles won by each age"),
    "win_pct": ("Match win rate", "Share of tour-level matches won, by age"),
    "win_pct_vs_top10": ("Win rate vs top-10", "Share of matches won against top-10 opponents, by age"),
    "cum_weeks_at_no1": ("Weeks at No. 1 (cumulative)", "Weekly ranking snapshots at world No. 1, by age"),
}


def load(db_path: Path) -> dict[str, pd.DataFrame]:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return {
            "age_curves": con.sql("select * from marts.mart_age_curves order by player_id, age_year").df(),
            "pace": con.sql("select * from marts.mart_pace_comparison").df(),
            "slams": con.sql("select * from marts.mart_slam_titles order by tourney_date").df(),
            "era_slams": con.sql("select * from marts.mart_big3_era_slams order by tourney_date").df(),
            "h2h": con.sql("select * from marts.mart_vs_big3_h2h").df(),
            "as_of": con.sql("select max(tourney_date) as d from marts.fct_player_matches").df()["d"][0],
        }


def colour_map(age_curves: pd.DataFrame) -> dict[str, str]:
    pairs = age_curves[["display_name", "colour_slot"]].drop_duplicates()
    return {r.display_name: SLOT_COLOURS[int(r.colour_slot)] for r in pairs.itertuples()}
