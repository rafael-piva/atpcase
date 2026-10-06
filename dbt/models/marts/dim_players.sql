select
    p.player_id,
    p.player_name,
    coalesce(poi.display_name, p.player_name)  as display_name,
    poi.cohort,
    poi.colour_slot,
    poi.player_id is not null                  as is_focus_player,
    p.hand,
    p.date_of_birth,
    p.country_code,
    p.height_cm
from {{ ref('stg_atp__players') }} p
left join {{ ref('players_of_interest') }} poi on poi.player_id = p.player_id
