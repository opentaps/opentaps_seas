INSERT INTO public.core_meter_rate_plan (
  description,
  from_datetime,
  billing_day,
  source,
  created_datetime,
  billing_frequency_uom_id
)
select 
  'Get rates from OpenEI' as description,
  now() as from_datetime,
  1 as billing_day,
  'openei.org' as source,
  now() as created_datetime,
  'time_interval_monthly' as billing_frequency_uom_id
where not exists (
  select 1 from public.core_meter_rate_plan where description = 'Get rates from OpenEI'
);

