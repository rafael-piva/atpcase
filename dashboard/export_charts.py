"""Export the story charts as PNGs for the README (no server needed)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

from dashboard.charts import GRID, METRICS, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, colour_map, load  # noqa: E402

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_SECONDARY,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
    }
)


def dodge(labels: list[tuple[float, float, str, str]], min_gap: float) -> list[tuple[float, float, str, str]]:
    """Nudge end-of-line labels apart vertically so they never overlap."""
    labels = sorted(labels, key=lambda t: t[1])
    for i in range(1, len(labels)):
        x, y, name, c = labels[i]
        if y - labels[i - 1][1] < min_gap:
            labels[i] = (x, labels[i - 1][1] + min_gap, name, c)
    return labels


def age_curve(df, metric: str, colours: dict, out: Path, as_of) -> None:
    label, title = METRICS[metric]
    is_rate = metric.startswith("win_pct")
    if is_rate:  # rates get noisy with seven lines: keep the headline comparison
        df = df[df["cohort"] != "Big 3 era challengers"]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.set_axisbelow(True)
    ends = []
    for name, g in df.groupby("display_name", sort=False):
        g = g.dropna(subset=[metric])
        if is_rate:
            g = g[g["matches_vs_top10" if metric.endswith("top10") else "matches"] >= 10]
        if g.empty:
            continue
        step = "post" if metric.startswith("cum_") else None
        if step:
            ax.step(g["age_year"], g[metric], where="post", color=colours[name], lw=2)
        else:
            ax.plot(g["age_year"], g[metric], color=colours[name], lw=2, marker="o", ms=4)
        last = g.iloc[-1]
        ends.append((last["age_year"], last[metric], name, colours[name]))
    span = ax.get_ylim()[1] - ax.get_ylim()[0]
    for x, y, name, _ in dodge(ends, span * 0.045):
        ax.annotate(name, (x, y), xytext=(6, 0), textcoords="offset points",
                    va="center", color=TEXT_PRIMARY, fontsize=9)
    ax.set_xlabel("Age (years)")
    ax.set_ylabel(label)
    if is_rate:
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_title(title, loc="left", color=TEXT_PRIMARY, fontsize=12, fontweight="bold")
    note = " Ages with fewer than 10 matches are hidden." if is_rate else ""
    fig.text(0.01, 0.01, f"Tour-level singles matches.{note} Data to {as_of:%d %b %Y}. Source: Jeff Sackmann / Tennis Abstract (CC BY-NC-SA 4.0).",
             color=TEXT_SECONDARY, fontsize=7)
    shown = list(dict.fromkeys(df["display_name"]))
    handles = [plt.Line2D([], [], color=colours[n], lw=2) for n in shown]
    ax.xaxis.set_major_locator(plt.MultipleLocator(5))
    ax.legend(handles, shown, frameon=False, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.12), fontsize=8)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def pace_bars(pace, colours: dict, out: Path) -> None:
    groups = sorted(pace["compared_at_age_of"].unique())
    fig, axes = plt.subplots(1, len(groups), figsize=(8, 3.6), dpi=150, sharex=True)
    [a.set_axisbelow(True) for a in (axes if len(groups) > 1 else [axes])]
    axes = axes if len(groups) > 1 else [axes]
    for ax, ng in zip(axes, groups):
        g = pace[pace["compared_at_age_of"] == ng].sort_values("slam_titles")
        bars = ax.barh(g["player_name"], g["slam_titles"], color=[colours[n] for n in g["player_name"]], height=0.6)
        ax.bar_label(bars, padding=3, color=TEXT_PRIMARY, fontsize=9)
        ax.set_title(f"At {ng}'s age ({g['age'].iloc[0]:.1f})", loc="left", color=TEXT_PRIMARY, fontsize=11)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Grand Slam titles")
    fig.suptitle("Grand Slam titles won by the same age", x=0.01, ha="left", fontweight="bold", color=TEXT_PRIMARY)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def era_slams(era, colours: dict, out: Path, as_of) -> None:
    """Grand Slams since 2005 won by players outside the Big 3."""
    others = era[era["champion_group"] != "Big 3"]
    summary = (
        others.assign(beat=others["big3_wins_in_run"] > 0)
        .groupby("champion")
        .agg(titles=("beat", "size"), via_big3=("beat", "sum"))
        .sort_values(["titles", "via_big3"])
    )
    big3_total = int((era["champion_group"] == "Big 3").sum())
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.set_axisbelow(True)
    grey = "#b9b8b3"
    for i, (name, r) in enumerate(summary.iterrows()):
        c = colours.get(name, grey)
        ax.barh(i, r["via_big3"], color=c, height=0.6)
        ax.barh(i, r["titles"] - r["via_big3"], left=r["via_big3"], color=c, alpha=0.35, height=0.6)
        ax.text(r["titles"] + 0.05, i, f"{int(r['titles'])}  ({int(r['via_big3'])} beating a Big 3 player)",
                va="center", fontsize=8, color=TEXT_PRIMARY)
    ax.set_yticks(range(len(summary)), summary.index)
    ax.set_xlim(0, summary["titles"].max() + 2.2)
    ax.set_xlabel("Grand Slam titles")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        f"The other {len(others)} majors: the Big 3 won {big3_total} of {len(era)} Grand Slams from 2005",
        loc="left", fontsize=12, fontweight="bold", color=TEXT_PRIMARY,
    )
    fig.text(0.01, 0.01, f"Solid = title run included a win over Federer, Nadal or Djokovic. Data to {as_of:%d %b %Y}.",
             color=TEXT_SECONDARY, fontsize=7)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def slam_finals_vs_big3(h2h, colours: dict, out: Path) -> None:
    """Murray vs Wawrinka: Grand Slam finals against the Big 3."""
    g = h2h[h2h["cohort"] == "Big 3 era challengers"].groupby("player")[["slam_finals", "slam_finals_won"]].sum()
    fig, ax = plt.subplots(figsize=(8, 2.8), dpi=150)
    ax.set_axisbelow(True)
    for i, (name, r) in enumerate(g.sort_values("slam_finals").iterrows()):
        c = colours[name]
        ax.barh(i, r["slam_finals_won"], color=c, height=0.55)
        ax.barh(i, r["slam_finals"] - r["slam_finals_won"], left=r["slam_finals_won"], color=c, alpha=0.3, height=0.55)
        ax.text(r["slam_finals"] + 0.1, i, f"won {int(r['slam_finals_won'])} of {int(r['slam_finals'])}",
                va="center", fontsize=9, color=TEXT_PRIMARY)
    ax.set_yticks(range(len(g)), g.sort_values("slam_finals").index)
    ax.set_xlim(0, g["slam_finals"].max() + 2)
    ax.set_xlabel("Grand Slam finals against Federer, Nadal or Djokovic")
    ax.grid(axis="y", visible=False)
    ax.set_title("Wawrinka won 3 of his 4 Slam finals against the Big 3", loc="left",
                 fontsize=12, fontweight="bold", color=TEXT_PRIMARY)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def main(db_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load(db_path)
    colours = colour_map(data["age_curves"])
    pace_bars(data["pace"], colours, out_dir / "01_pace_slams.png")
    for i, metric in enumerate(METRICS, start=2):
        age_curve(data["age_curves"], metric, colours, out_dir / f"0{i}_{metric}.png", data["as_of"])
    era_slams(data["era_slams"], colours, out_dir / "06_big3_era_slams.png", data["as_of"])
    slam_finals_vs_big3(data["h2h"], colours, out_dir / "07_slam_finals_vs_big3.png")
    print(f"charts written to {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/warehouse.duckdb"), Path("docs/img"))
