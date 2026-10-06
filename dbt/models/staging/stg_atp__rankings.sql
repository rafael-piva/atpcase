-- Weekly rankings. The source files overlap at decade boundaries (exact
-- duplicates), and a few hundred player-weeks appear twice with different
-- ranks (mostly 2019-2023, low-ranked players). Keep the best rank per
-- player per week so every (ranking_date, player_id) is unique.
with source as (
    select * from {{ source('raw', 'atp_rankings') }}
),

typed as (
    select
        strptime(ranking_date, '%Y%m%d')::date                 as ranking_date,
        try_cast("rank" as integer)                            as ranking,
        try_cast(player as bigint)                             as player_id,
        try_cast(points as integer)                            as ranking_points
    from source
)

select *
from typed
where player_id is not null and ranking is not null
qualify row_number() over (partition by ranking_date, player_id order by ranking) = 1
