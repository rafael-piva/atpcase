-- Every weekly ranking snapshot where a player was world No. 1.
select
    r.ranking_date,
    r.player_id,
    d.display_name,
    datediff('day', d.date_of_birth, r.ranking_date) / 365.25 as age_at_ranking
from {{ ref('stg_atp__rankings') }} r
join {{ ref('dim_players') }} d using (player_id)
where r.ranking = 1
