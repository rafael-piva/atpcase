-- Career by age for the focus players: one row per player per year of age.
-- This is the backbone of the "Big 3 vs new generation at the same age" story.
with pm as (
    select f.*, d.display_name, d.cohort, d.colour_slot
    from {{ ref('fct_player_matches') }} f
    join {{ ref('dim_players') }} d using (player_id)
    where d.is_focus_player
      and f.tourney_level in ('G', 'M', 'F', 'A', 'O')   -- tour level only
      and not f.is_incomplete
),

no1_weeks as (
    select player_id, floor(age_at_ranking)::int as age_year, count(*) as weeks_at_no1
    from {{ ref('mart_no1_weeks') }}
    group by 1, 2
),

by_age as (
    select
        player_id, display_name, cohort, colour_slot,
        floor(age_at_match)::int                                   as age_year,
        count(*)                                                   as matches,
        count(*) filter (where is_win)                             as wins,
        count(*) filter (where vs_top10)                           as matches_vs_top10,
        count(*) filter (where vs_top10 and is_win)                as wins_vs_top10,
        count(*) filter (where is_title)                           as titles,
        count(*) filter (where is_title and is_grand_slam)         as slam_titles
    from pm
    group by all
)

select
    b.*,
    round(b.wins / b.matches, 4)                                   as win_pct,
    round(b.wins_vs_top10 / nullif(b.matches_vs_top10, 0), 4)      as win_pct_vs_top10,
    coalesce(w.weeks_at_no1, 0)                                    as weeks_at_no1,
    sum(b.titles)      over career                                 as cum_titles,
    sum(b.slam_titles) over career                                 as cum_slam_titles,
    sum(coalesce(w.weeks_at_no1, 0)) over career                   as cum_weeks_at_no1
from by_age b
left join no1_weeks w using (player_id, age_year)
window career as (partition by b.player_id order by b.age_year
                  rows between unbounded preceding and current row)
