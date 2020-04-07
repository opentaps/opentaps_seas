INSERT INTO public.core_meter_rate_plan (
  description,
  from_datetime,
  billing_day,
  created_datetime,
  billing_frequency_uom_id,
  params,
  source
)
select 
  'Simple Rate Plan' as description,
  now() as from_datetime,
  1 as billing_day,
  now() as created_datetime,
  'time_interval_monthly' as billing_frequency_uom_id,
  'flat_rate => "0.2",
   energy_uom_id => "energy_kWh",
   currency_uom_id => "currency_USD"' as params,
   ''
where not exists (
  select 1 from public.core_meter_rate_plan where description = 'Simple Rate Plan'
);

