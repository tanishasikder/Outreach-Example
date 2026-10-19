{# Turns a list from dbt_project.yml vars into SQL: ['a', 'b'] -> 'a', 'b' #}
{% macro sql_list(values) -%}
    {%- for v in values -%}'{{ v }}'{{ ", " if not loop.last }}{%- endfor -%}
{%- endmacro %}
