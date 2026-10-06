-- Every Grand Slam title in the dataset, with the champion's age.
select
    f.tourney_date,
    year(f.tourney_date)            as season,
    f.tourney_name,
    f.surface,
    f.player_id,
    d.display_name,
    d.cohort,
    round(f.age_at_match, 2)        as age_at_title
from {{ ref('fct_player_matches') }} f
join {{ ref('dim_players') }} d using (player_id)
where f.is_title and f.is_grand_slam
