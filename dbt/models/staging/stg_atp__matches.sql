-- One row per match, typed and with a stable surrogate key.
with source as (
    select * from {{ source('raw', 'atp_matches') }}
),

typed as (
    select
        tourney_id || '-' || match_num                         as match_id,
        tourney_id,
        replace(tourney_name, 'Us Open', 'US Open')               as tourney_name,
        nullif(surface, '')                                    as surface,
        upper(tourney_level)                                   as tourney_level,
        strptime(tourney_date, '%Y%m%d')::date                 as tourney_date,
        try_cast(match_num as integer)                         as match_num,
        "round"                                                as round_code,
        try_cast(best_of as integer)                           as best_of,
        score,
        try_cast(minutes as integer)                           as minutes,
        try_cast(winner_id as bigint)                          as winner_id,
        try_cast(loser_id as bigint)                           as loser_id,
        try_cast(winner_rank as integer)                       as winner_rank,
        try_cast(loser_rank as integer)                        as loser_rank,
        try_cast(winner_rank_points as integer)                as winner_rank_points,
        try_cast(loser_rank_points as integer)                 as loser_rank_points,
        score ilike '%RET%' or score ilike '%W/O%' or score ilike '%DEF%' as is_incomplete,
        _source_file
    from source
    where winner_id is not null and loser_id is not null
)

select * from typed
