-- Who won the Grand Slams the Big 3 did not, and did they go through a
-- Big 3 member to do it? Era = 2005 onwards (Federer, Nadal and Djokovic all
-- on tour and winning majors).
with titles as (
    select * from {{ ref('fct_player_matches') }}
    where is_title and is_grand_slam and tourney_date >= date '2005-01-01'
),

big3_beaten as (
    select f.tourney_id, f.player_id,
           count(*)                                         as big3_wins_in_run,
           string_agg(d.display_name || ' (' || f.round_code || ')', ', ' order by f.tourney_date, f.round_code) as big3_beaten
    from {{ ref('fct_player_matches') }} f
    join {{ ref('dim_players') }} d on d.player_id = f.opponent_id
    where f.is_win and f.is_grand_slam and d.cohort = 'Big 3'
    group by 1, 2
)

select
    t.tourney_date,
    year(t.tourney_date)                                    as season,
    t.tourney_name,
    t.surface,
    t.player_id,
    champ.display_name                                      as champion,
    coalesce(champ.cohort, 'Other')                         as champion_group,
    opp.display_name                                        as final_opponent,
    coalesce(b.big3_wins_in_run, 0)                         as big3_wins_in_run,
    b.big3_beaten
from titles t
join {{ ref('dim_players') }} champ on champ.player_id = t.player_id
join {{ ref('dim_players') }} opp   on opp.player_id   = t.opponent_id
left join big3_beaten b on b.tourney_id = t.tourney_id and b.player_id = t.player_id
