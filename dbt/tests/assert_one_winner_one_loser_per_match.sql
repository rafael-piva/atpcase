-- Every match must unpivot into exactly one win row and one loss row.
select match_id
from {{ ref('int_player_matches') }}
group by match_id
having count(*) <> 2 or sum(case when is_win then 1 else 0 end) <> 1
