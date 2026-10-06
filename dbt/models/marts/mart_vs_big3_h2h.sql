-- Head-to-head of every non-Big 3 focus player against each Big 3 member.
select
    me.display_name                                                 as player,
    me.cohort,
    opp.display_name                                                as opponent,
    count(*)                                                        as matches,
    count(*) filter (where f.is_win)                                as wins,
    round(count(*) filter (where f.is_win) / count(*), 3)           as win_pct,
    count(*) filter (where f.is_grand_slam)                         as slam_matches,
    count(*) filter (where f.is_grand_slam and f.is_win)            as slam_wins,
    count(*) filter (where f.is_grand_slam and f.round_code = 'F')  as slam_finals,
    count(*) filter (where f.is_grand_slam and f.round_code = 'F' and f.is_win) as slam_finals_won
from {{ ref('fct_player_matches') }} f
join {{ ref('dim_players') }} me  on me.player_id  = f.player_id
join {{ ref('dim_players') }} opp on opp.player_id = f.opponent_id
where me.is_focus_player and me.cohort <> 'Big 3'
  and opp.cohort = 'Big 3'
  and f.tourney_level in ('G', 'M', 'F', 'A', 'O')
  and not f.is_incomplete
group by all
