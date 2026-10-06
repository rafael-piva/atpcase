with source as (
    select * from {{ source('raw', 'atp_players') }}
)

select
    try_cast(player_id as bigint)                              as player_id,
    trim(coalesce(name_first, '') || ' ' || coalesce(name_last, '')) as player_name,
    nullif(hand, '')                                           as hand,
    try_strptime(nullif(dob, ''), '%Y%m%d')::date              as date_of_birth,
    nullif(ioc, '')                                            as country_code,
    try_cast(height as integer)                                as height_cm
from source
where try_cast(player_id as bigint) is not null
-- Data quality: the source re-uses a few IDs for two different (lower-tier)
-- players. Keep one row per ID deterministically; see README "Data quality".
qualify row_number() over (partition by player_id order by player_name) = 1
