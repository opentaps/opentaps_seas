update core_entity set m_tags = '{"point","his","sensor"}', kv_tags = kv_tags || hstore('dis', '') where lower(topic) like 'demo\_%';

update core_entity set m_tags = '{"point","his","sensor","air","temp"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where lower(topic) like 'demo\_%zonetemp%';
update core_entity set m_tags = '{"point","his","sensor","air","temp","return"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%RAT%';
update core_entity set m_tags = '{"point","his","sensor","air","temp","outside"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%OAT%';
update core_entity set m_tags = '{"point","his","sensor","air","outside"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%OA_%';
update core_entity set m_tags = '{"point","his","sensor","air","temp","discharge"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%DAT%';
update core_entity set m_tags = '{"point","his","sensor","air","discharge"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%DA_%';
update core_entity set m_tags = '{"point","his","sensor","air","temp","mixed"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '°F']) where topic like 'demo\_%MAT%';
update core_entity set m_tags = '{"point","his","sensor","air","discharge","pressure"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', 'psi']) where topic like 'demo\_%DA\_Static%';
update core_entity set m_tags = '{"point","his","sensor","cool","pressure"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', 'psi']) where topic like 'demo\_%Chilled\_Water%';

update core_entity set m_tags = '{"point","his","sensor","air","discharge"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '%']) where lower(topic) like 'demo\_%su\_fan%';
update core_entity set m_tags = '{"point","his","sensor","air","return"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '%']) where lower(topic) like 'demo\_%re\_fan%';

update core_entity set m_tags = '{"point","his","sensor","air"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '%']) where lower(topic) like 'demo\_%vavdamper%';
update core_entity set m_tags = '{"point","his","sensor","air","humidity"}', kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', '%RH']) where lower(topic) like 'demo\_%rhvalve%';

update core_entity set m_tags = array_append(m_tags, 'zone') where lower(topic) like 'demo\_%zone%';
update core_entity set m_tags = array_append(m_tags, 'avg') where lower(topic) like 'demo\_%avg_zonetemp%';
update core_entity set m_tags = array_append(m_tags, 'cmd') where lower(topic) like 'demo\_%_cmd%';
update core_entity set m_tags = array_append(m_tags, 'valve') where lower(topic) like 'demo\_%valve%';
update core_entity set m_tags = array_append(m_tags, 'damper') where lower(topic) like 'demo\_%damper%';
update core_entity set m_tags = array_append(m_tags, 'water') where lower(topic) like 'demo\_%water%';
update core_entity set m_tags = array_append(m_tags, 'sp') where lower(topic) like 'demo\_%_sp%';
update core_entity set m_tags = array_append(m_tags, 'fan') where lower(topic) like 'demo\_%_fan%';
update core_entity set m_tags = array_append(m_tags, 'cool') where lower(topic) like 'demo\_%cool%';
update core_entity set m_tags = array_append(m_tags, 'heat') where lower(topic) like 'demo\_%heat%';
update core_entity set m_tags = array_append(m_tags, 'speed') where lower(topic) like 'demo\_%_speed%';
update core_entity set m_tags = array_append(m_tags, 'exhaust'), kv_tags = kv_tags || hstore(ARRAY['kind', 'Number', 'unit', 'cfm']) where lower(topic) like 'demo\_%cfm%';
update core_entity set m_tags = array_append(m_tags, 'air') where lower(topic) like 'demo\_%cfm%';
update core_entity set m_tags = array_append(m_tags, 'flow') where lower(topic) like 'demo\_%cfm%';

update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Average')) where lower(topic) like 'demo\_%/avg\_%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Zone Temp')) where lower(topic) like 'demo\_%zonetemp%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Discharge Air Temp')) where lower(topic) like 'demo\_%/dat%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Mixed Air Temp')) where lower(topic) like 'demo\_%/mat%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Outside Air Temp')) where lower(topic) like 'demo\_%/oat%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Return Air Temp')) where lower(topic) like 'demo\_%/rat%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Outside Damper')) where lower(topic) like 'demo\_%/oa\_damper%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Discharge Air Static Pressure')) where lower(topic) like 'demo\_%/da\_static%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Relative Humidity')) where lower(topic) similar to 'demo\_%/(avg\_)?rh%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Supply Fan')) where lower(topic) like 'demo\_%/su\_fan%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Return Fan')) where lower(topic) like 'demo\_%/re\_fan%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Variable Air Volume')) where lower(topic) similar to 'demo\_%/(avg\_)?vav%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Zone Air Flow')) where lower(topic) similar to 'demo\_%/(avg\_)?zonecfm%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Cool')) where lower(topic) like 'demo\_%/cool%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Heat')) where lower(topic) like 'demo\_%/heat%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Stage')) where lower(topic) like 'demo\_%/%_stg%';
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Chilled Water')) where lower(topic) like 'demo\_%/chilled_water%';

update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Speed')) where 'speed' = ANY(m_tags);
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Set Point')) where 'sp' = ANY(m_tags);
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' Valve')) where 'valve' = ANY(m_tags);
update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' CMD')) where 'cmd' = ANY(m_tags);

update core_entity set kv_tags = kv_tags || hstore('dis', trim(kv_tags->'dis' || ' ' || regexp_replace(topic, '^.*?(?=[0-9]*$)', ''))) where lower(topic) like 'demo\_%';

update core_entity set kv_tags = kv_tags || hstore('dis', topic) where lower(topic) like 'demo\_%' and trim(kv_tags->'dis') = '';
