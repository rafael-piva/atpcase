-- Incremental + unique_key: re-running reprocesses only the trailing year
-- (to pick up late corrections in the source) and upserts by key, so the
-- table never gets duplicate rows no matter how often the job runs.
{{
    config(
        materialized = 'incremental',
        unique_key = 'player_match_id',
        incremental_strategy = 'delete+insert'
    )
}}

select *
from {{ ref('int_player_matches') }}
{% if is_incremental() %}
where tourney_date >= (select max(tourney_date) - interval 365 day from {{ this }})
{% endif %}
