-- Headline numbers: for each new-generation player, what has he won so far,
-- and what had each Big 3 member won by exactly the same age?
with data_cutoff as (
    select max(tourney_date) as as_of from {{ ref('fct_player_matches') }}
),

next_gen as (
    select d.player_id, d.display_name,
           datediff('day', d.date_of_birth, c.as_of) / 365.25 as current_age
    from {{ ref('dim_players') }} d cross join data_cutoff c
    where d.cohort = 'New generation'
),

big3 as (
    select player_id, display_name from {{ ref('dim_players') }} where cohort = 'Big 3'
),

matches as (
    select * from {{ ref('fct_player_matches') }}
    where tourney_level in ('G', 'M', 'F', 'A', 'O') and not is_incomplete
),

no1 as (select * from {{ ref('mart_no1_weeks') }}),

pairs as (
    select ng.player_id as ng_id, ng.display_name as ng_name, ng.current_age,
           ng.player_id as player_id, ng.display_name as player_name, 'New generation' as cohort
    from next_gen ng
    union all
    select ng.player_id, ng.display_name, ng.current_age,
           b.player_id, b.display_name, 'Big 3'
    from next_gen ng cross join big3 b
),

results as (
    select
        p.ng_name, p.current_age, p.player_id, p.player_name, p.cohort,
        count(m.player_match_id) filter (where m.is_title and m.is_grand_slam)  as slam_titles,
        count(m.player_match_id) filter (where m.is_title)                      as titles,
        count(m.player_match_id) filter (where m.is_win)                        as match_wins,
        count(m.player_match_id)                                                as matches
    from pairs p
    left join matches m
           on m.player_id = p.player_id
          and m.age_at_match <= p.current_age
    group by all
),

weeks as (
    select p.ng_name, p.player_id, count(n.ranking_date) as weeks_at_no1
    from pairs p
    left join no1 n
           on n.player_id = p.player_id
          and n.age_at_ranking <= p.current_age
    group by all
)

select
    r.ng_name                                 as compared_at_age_of,
    round(r.current_age, 1)                   as age,
    r.player_name,
    r.cohort,
    r.slam_titles,
    r.titles,
    r.match_wins,
    round(r.match_wins / nullif(r.matches, 0), 3) as win_pct,
    w.weeks_at_no1
from results r
join weeks w using (ng_name, player_id)
order by compared_at_age_of, cohort desc, slam_titles desc
