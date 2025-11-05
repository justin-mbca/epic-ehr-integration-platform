-- Simple dbt model to expose patients table
select * from {{ source('public', 'patients') }}
