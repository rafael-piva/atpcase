"""Streamlit dashboard: are Alcaraz and Sinner on Big 3 pace?

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from dashboard.charts import GRID, METRICS, TEXT_SECONDARY, colour_map, load  # noqa: E402

DB = Path(os.environ.get("ATP_DB_PATH", Path(__file__).resolve().parents[1] / "data/warehouse.duckdb"))

st.set_page_config(page_title="Big 3 vs the new generation", layout="wide")


@st.cache_data
def get_data():
    return load(DB)


data = get_data()
curves, pace, slams = data["age_curves"], data["pace"], data["slams"]
era, h2h = data["era_slams"], data["h2h"]
colours = colour_map(curves)

st.title("Are Alcaraz and Sinner on Big 3 pace?")
big3_slams = int((slams["cohort"] == "Big 3").sum())
st.caption(
    f"Federer, Nadal and Djokovic won {big3_slams} Grand Slams between them in this dataset. This dashboard lines every career up "
    f"by age, so the new generation is compared with the Big 3 at the same point in life, not the same year. "
    f"Data to {data['as_of']:%d %b %Y}."
)

# --- Headline: same-age comparison ------------------------------------------------
cols = st.columns(pace["compared_at_age_of"].nunique())
for col, (ng, g) in zip(cols, pace.groupby("compared_at_age_of")):
    me = g[g["player_name"] == ng].iloc[0]
    big3 = g[g["cohort"] == "Big 3"].sort_values("slam_titles", ascending=False)
    best = big3.iloc[0]
    col.metric(f"{ng}: Grand Slams at {me['age']:.1f}", int(me["slam_titles"]),
               delta=f"{int(me['slam_titles'] - best['slam_titles']):+d} vs {best['player_name']} at the same age",
               delta_color="normal")
    col.dataframe(
        g[["player_name", "slam_titles", "titles", "match_wins", "win_pct", "weeks_at_no1"]]
        .rename(columns={"player_name": "Player", "slam_titles": "Slams", "titles": "Titles",
                         "match_wins": "Wins", "win_pct": "Win %", "weeks_at_no1": "Weeks at No. 1"}),
        hide_index=True, use_container_width=True,
    )

st.divider()

# --- Age curves -------------------------------------------------------------------
players = st.multiselect("Players", list(colours), default=list(colours))
metric = st.radio("Measure", list(METRICS), format_func=lambda m: METRICS[m][0], horizontal=True)
label, subtitle = METRICS[metric]

fig = go.Figure()
for name in players:
    g = curves[curves["display_name"] == name].dropna(subset=[metric])
    if metric.startswith("win_pct"):
        g = g[g["matches_vs_top10" if metric.endswith("top10") else "matches"] >= 5]
    fig.add_trace(
        go.Scatter(
            x=g["age_year"], y=g[metric], name=name, mode="lines+markers",
            line=dict(color=colours[name], width=2, shape="hv" if metric.startswith("cum_") else "linear"),
            marker=dict(size=8),
            customdata=g[["matches", "wins", "titles", "slam_titles"]],
            hovertemplate=(f"<b>{name}</b> at %{{x}}<br>{label}: %{{y}}<br>"
                           "Matches %{customdata[0]}, wins %{customdata[1]}<br>"
                           "Titles %{customdata[2]} (Slams %{customdata[3]})<extra></extra>"),
        )
    )
fig.update_layout(
    title=subtitle, xaxis_title="Age (years)", yaxis_title=label, hovermode="x unified",
    plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2),
    yaxis=dict(gridcolor=GRID, tickformat=".0%" if metric.startswith("win_pct") else None),
    xaxis=dict(gridcolor=GRID, dtick=1),
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Table view"):
    st.dataframe(curves[curves["display_name"].isin(players)], hide_index=True, use_container_width=True)

# --- The exceptions: Murray and Wawrinka ---------------------------------------------
st.divider()
others = era[era["champion_group"] != "Big 3"]
st.subheader(f"The {len(others)} majors the Big 3 didn't win (2005 onwards)")
st.caption(
    f"The Big 3 won {len(era) - len(others)} of {len(era)} Grand Slams in this period. "
    "Murray and Wawrinka are the only other players with three titles each. Wawrinka beat a Big 3 "
    "player on the way to every one of his, including three of his four Slam finals against them."
)
c1, c2 = st.columns(2)
summary = (others.assign(via=others["big3_wins_in_run"] > 0).groupby("champion")
           .agg(titles=("via", "size"), via_big3=("via", "sum")).sort_values("titles"))
bar = go.Figure()
bar.add_bar(y=summary.index, x=summary["via_big3"], orientation="h", name="Beat a Big 3 player en route",
            marker_color=[colours.get(n, "#8a8984") for n in summary.index])
bar.add_bar(y=summary.index, x=summary["titles"] - summary["via_big3"], orientation="h", name="Did not face one",
            marker_color=[colours.get(n, "#8a8984") for n in summary.index], marker_opacity=0.35)
bar.update_layout(barmode="stack", xaxis_title="Grand Slam titles", plot_bgcolor="rgba(0,0,0,0)",
                  legend=dict(orientation="h", y=-0.25), xaxis=dict(gridcolor=GRID, dtick=1))
c1.plotly_chart(bar, use_container_width=True)
c2.markdown("**Head-to-head against the Big 3** (tour level)")
c2.dataframe(
    h2h.sort_values(["cohort", "player", "opponent"]).rename(columns={
        "player": "Player", "opponent": "Opponent", "matches": "Matches", "wins": "Wins", "win_pct": "Win %",
        "slam_finals": "Slam finals", "slam_finals_won": "Slam finals won"})
    [["Player", "Opponent", "Matches", "Wins", "Win %", "Slam finals", "Slam finals won"]],
    hide_index=True, use_container_width=True,
)
with st.expander("Every non-Big 3 Grand Slam title since 2005"):
    st.dataframe(others[["season", "tourney_name", "champion", "final_opponent", "big3_beaten"]],
                 hide_index=True, use_container_width=True)

# --- Context: every Slam champion --------------------------------------------------
st.subheader("Every Grand Slam title in the dataset")
st.dataframe(
    slams.sort_values("tourney_date", ascending=False)
    .assign(tourney_date=lambda d: d["tourney_date"].dt.date, cohort=lambda d: d["cohort"].fillna("Other"))
    [["tourney_date", "tourney_name", "surface", "display_name", "cohort", "age_at_title"]]
    .rename(columns={"tourney_date": "Date", "tourney_name": "Tournament", "surface": "Surface",
                     "display_name": "Champion", "cohort": "Group", "age_at_title": "Age"}),
    hide_index=True, use_container_width=True,
)
st.caption("Source: Jeff Sackmann / Tennis Abstract ATP data, CC BY-NC-SA 4.0.", help=None)
st.markdown(f"<span style='color:{TEXT_SECONDARY}'>Built with DuckDB + dbt. See the README for the pipeline.</span>",
            unsafe_allow_html=True)
