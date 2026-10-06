-- Generic test: the given expression must be unique across the model.
{% test unique_combination(model, combination) %}
select {{ combination }} as key, count(*) as n
from {{ model }}
group by 1
having count(*) > 1
{% endtest %}
