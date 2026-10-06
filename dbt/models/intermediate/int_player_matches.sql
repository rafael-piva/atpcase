-- Unpivot each match into two rows: one from the winner's point of view and
-- one from the loser's. Everything downstream ("how did player X do?") becomes
-- a simple filter + group by.
with matches as (
    select * from {{ ref('stg_atp__matches') }}
),

players as (
    select player_id, date_of_birth from {{ ref('stg_atp__players') }}
),

levels as (
    select * from {{ ref('tourney_levels') }}
),

player_rows as (
    select
        match_id, tourney_id, tourney_name, tourney_date, surface, tourney_level,
        round_code, best_of, is_incomplete,
        winner_id   as player_id,
        loser_id    as opponent_id,
        winner_rank as player_rank,
        loser_rank  as opponent_rank,
        true        as is_win
    from matches
    union all
    select
        match_id, tourney_id, tourney_name, tourney_date, surface, tourney_level,
        round_code, best_of, is_incomplete,
        loser_id, winner_id, loser_rank, winner_rank,
        false
    from matches
)

select
    pr.match_id || '-' || pr.player_id                             as player_match_id,
    pr.*,
    coalesce(l.is_grand_slam, false)                               as is_grand_slam,
    l.level_name,
    p.date_of_birth,
    -- age in decimal years at the start of the tournament
    datediff('day', p.date_of_birth, pr.tourney_date) / 365.25     as age_at_match,
    pr.opponent_rank <= 10                                         as vs_top10,
    pr.round_code = 'F' and pr.is_win                              as is_title
from player_rows pr
left join players p on p.player_id = pr.player_id
left join levels  l on l.tourney_level = pr.tourney_level
