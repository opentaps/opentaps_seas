# This file is part of opentaps Smart Energy Applications Suite (SEAS).

# opentaps Smart Energy Applications Suite (SEAS) is free software:
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# opentaps Smart Energy Applications Suite (SEAS) is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with opentaps Smart Energy Applications Suite (SEAS).
# If not, see <https://www.gnu.org/licenses/>.

from django.urls import path

from .views import common
from .views import entity
from .views import equipment
from .views import meter
from .views import model
from .views import point
from .views import site
from .views import tag
from .views import topic
from .views import transaction
from .views import weather
from .views import utilityapi

from ..eemeter.views import meter_model_calc_saving_view
from ..eemeter.views import meter_model_create_view
from ..eemeter.views import meter_model_delete_view
from ..eemeter.views import meter_model_detail_view
from ..eemeter.views import meter_model_extra_detail_view
from ..eemeter.views import meter_model_production_delete_view

app_name = "core"
urlpatterns = [
    path("task_progress/json/<str:task_id>", view=common.get_task_progress_json, name="get_task_progress_json"),
    path("task_progress/<str:task_id>", view=common.get_task_progress, name="get_task_progress"),
    path("transaction/", view=transaction.transaction_list_view, name="transaction_list"),
    path("transaction/<str:financial_transaction_id>/",
         view=transaction.transaction_detail_view, name="transaction_detail"),
    path("transaction/edit/<path:financial_transaction_id>",
         view=transaction.transaction_edit_view, name="transaction_edit"),
    path("transaction/delete/<path:financial_transaction_id>",
         view=transaction.transaction_delete_view, name="transaction_delete"),
    path("file/transaction/<path:financial_transaction_id>",
         view=transaction.transaction_file_upload, name="transaction_file_upload"),
    path("note/transaction/<path:financial_transaction_id>",
         view=transaction.transaction_note, name="transaction_note"),
    path("link/transaction/<path:financial_transaction_id>",
         view=transaction.transaction_link, name="transaction_link"),
    path("topic/", view=topic.topic_list_view, name="topic_list"),
    path("topic_tag_rulesets/", view=topic.topictagruleset_list_view, name="topictagruleset_list"),
    path("topic_tag_rulesets/<str:id>", view=topic.topictagruleset_detail_view, name="topictagruleset_detail"),
    path("topic_tag_rulesets/op/run", view=topic.topictagruleset_run_view, name="topictagruleset_runform"),
    path("topic_tag_rulesets/op/run/<str:id>", view=topic.topictagruleset_run_view, name="topictagruleset_run"),
    path("topic_tag_rulesets/op/export", view=topic.topictagruleset_export_view, name="topictagruleset_export"),
    path("topic_tag_rulesets/op/import", view=topic.topictagruleset_import_view, name="topictagruleset_import"),
    path("newtopic_tag_ruleset/", view=topic.topictagruleset_create_view, name="topictagruleset_create"),
    path("topic_tag_rule/<str:id>", view=topic.topic_list_view, name="topictagrule_detail"),
    path("topic_tag_rule/op/run/<str:id>", view=topic.topictagrule_run_view, name="topictagrule_run"),
    path("newtopic_tag_rule/<str:id>", view=topic.topictagrule_create_view, name="topictagrule_forset_create"),
    path("newtopic_tag_rule/", view=topic.topictagrule_create_view, name="topictagrule_create"),
    path("tag_topics/", view=topic.tag_topics, name="tag_topics"),
    path("topic_table/", view=topic.topic_list_table, name="topic_table"),
    path("topic_table_fields/", view=topic.topic_list_table_fields, name="topic_table_fields"),
    path("topic_json/", view=topic.topic_list_json, name="topic_json"),
    path("topic_rules/", view=topic.topic_rules, name="topic_rules"),
    path("topic/import", view=topic.topic_import_view, name="topic_import"),
    path("topic/export", view=topic.topic_export_view, name="topic_export0"),
    path("topic/export/<str:site>", view=topic.topic_export_view, name="topic_export"),
    path("topic/setup/<path:topic>", view=topic.topic_setup_view, name="topic_setup"),
    path("topic/assoc/<path:topic>", view=topic.topic_assoc, name="topic_assoc"),
    path("topic/csv/report_tags", view=topic.topic_report_tags_csv, name="topic_report_tags_csv"),
    path("entity/", view=entity.entity_list_view, name="entity_list"),
    path("entity/<path:entity_id>", view=entity.entity_detail_view, name="entity_detail"),
    path("file/entity/<path:entity_id>", view=entity.entity_file_upload, name="entity_file_upload"),
    path("link/entity/<path:entity_id>", view=entity.entity_link, name="entity_link"),
    path("note/entity/<path:entity_id>", view=entity.entity_note, name="entity_note"),
    path("tag/entity/<path:entity_id>", view=entity.entity_tag, name="entity_tag"),
    path("tag/", view=tag.tag_list_view, name="tag_list"),
    path("tag.json", view=tag.tag_list_json_view, name="tag_list_json"),
    path("newtag/", view=tag.tag_create_view, name="tag_create"),
    path("tag/edit/<path:tag>", view=tag.tag_edit_view, name="tag_edit"),
    path("tag/delete/<path:tag>", view=tag.tag_delete_view, name="tag_delete"),
    path("tag/view/<path:tag>", view=tag.tag_detail_view, name="tag_detail"),
    path("tag/import", view=tag.tag_import_view, name="tag_import"),
    path("model/", view=model.model_list_view, name="model_list"),
    path("model.json", view=model.model_list_json_view, name="model_list_json"),
    path("meter.json", view=meter.meter_list_json_view, name="meter_list_json"),
    path("newmeter/<str:site_id>", view=meter.meter_create_view, name="meter_create"),
    path("meter_rate_plan/<str:rate_plan_id>", view=meter.meter_rate_plan_detail_view, name="meter_rate_plan_detail"),
    path("meter_rate_plan_history/<path:meter_id>", view=meter.meter_rate_plan_history_view,
         name="meter_rate_plan_history"),
    path("meter/edit/<path:meter_id>", view=meter.meter_edit_view, name="meter_edit"),
    path("meter/deactivate/<path:meter_id>", view=meter.meter_deactivate_view, name="meter_deactivate"),
    path("meter/view/<path:meter_id>", view=meter.meter_detail_view, name="meter_detail"),
    path("meter/json/<str:meter>", view=meter.meter_data_json, name="meter_data_json"),
    path("meter/<str:meter>/transactions_table",
         view=transaction.meter_transactions_table, name="meter_transactions_table"),
    path("meter/<str:meter_id>/model/<str:id>", view=meter_model_detail_view, name="meter_model_detail"),
    path("meter/<str:meter_id>/model/<str:id>/details",
         view=meter_model_extra_detail_view, name="meter_model_extra_detail"),
    path("meter/<str:meter_id>/create/model", view=meter_model_create_view, name="meter_model_create"),
    path("meter/<str:meter_id>/model/<str:id>/delete", view=meter_model_delete_view, name="meter_model_delete"),
    path("meter/<str:meter_id>/model/<str:id>/delete_production",
         view=meter_model_production_delete_view, name="meter_model_production_delete"),
    path("meter/<str:meter_id>/model/<str:id>/calc_saving",
         view=meter_model_calc_saving_view, name="meter_model_calc_saving"),
    path("newmodel/", view=model.model_create_view, name="model_create"),
    path("newmodel/<path:entity_id>", view=model.model_create_view, name="model_create_for"),
    path("dupmodel/<path:entity_id>", view=model.model_duplicate_view, name="model_duplicate"),
    path("newsite/", view=site.site_create_view, name="site_create"),
    path("model/edit/<path:entity_id>", view=model.model_edit_view, name="model_edit"),
    path("model/delete/<path:entity_id>", view=model.model_delete_view, name="model_delete"),
    path("model/view/<path:entity_id>", view=model.model_detail_view, name="model_detail"),
    path("equipment.json", view=equipment.equipment_list_json_view, name="equipment_list_json"),
    path("equipment/", view=equipment.equipment_list_view, name="equipment_list"),
    path("equipment/<path:equip>", view=equipment.equipment_detail_view, name="equipment_detail"),
    path("equipment_dashboard/<path:equip>", view=equipment.equipment_dashboard, name="equipment_dashboard"),
    path("equipment_fetch_solaredge_details/<path:equip>",
         view=equipment.equipment_fetch_solaredge_details, name="equipment_fetch_solaredge_details"),
    path("equipment_solaredge_edit/<path:equip>",
         view=equipment.equipment_solaredge_edit_view, name="equipment_solaredge_edit_view"),
    path("equipment_points_table/<path:equip>",
         view=equipment.equipment_data_points_table, name="equipment_data_points_table"),
    path("site/<str:site>/newequipment/", view=equipment.equipment_create_view, name="equipment_create"),
    path("", view=site.site_list_view, name="site_list_default"),
    path("site/", view=site.site_list_view, name="site_list"),
    path("site.json", view=site.site_list_json_view, name="site_list_json"),
    path("site/<str:site>/", view=site.site_detail_view, name="site_detail"),
    path("site/<str:site>/pie_chart.json", view=site.site_pie_chart_data_json, name="site_pie_chart_data_json"),
    path("site/<str:site>/ahu_summary.json", view=site.site_ahu_summary_json, name="site_ahu_summary_json"),
    path("site/<str:site>/transactions_table",
         view=transaction.site_transactions_table, name="site_transactions_table"),
    path("site/<str:site>/equipment/<str:equip>/",
         view=equipment.equipment_site_detail_view, name="site_equipment_detail"),
    path("site/<str:site>/equipment/<str:equip>/csv/<path:point>",
         view=point.point_data_csv, name="site_equipment_point_data_csv"),
    path("site/<str:site>/equipment/<str:equip>/json/<path:point>",
         view=point.point_data_json, name="site_equipment_point_data_json"),
    path("site/<str:site>/equipment/<str:equip>/<path:point>",
         view=equipment.equipment_point_detail_view, name="site_equipment_point_detail"),
    path("point/csv/<path:point>", view=point.point_data_csv, name="point_data_csv"),
    path("point/json/<path:point>", view=point.point_data_json, name="point_data_json"),
    path("point/<path:entity_id>", view=point.point_detail_view, name="point_detail"),
    path("state.json/<str:country>", view=common.state_list_json_view, name="state_list_json"),
    path("timezone.json/<str:geo_id>", view=common.timezone_list_json_view, name="timezone_list_json"),
    path("bacnet_prefix.json/<str:site>", view=point.bacnet_prefix_list_json_view, name="bacnet_prefix_list_json"),
    path("report/preview/csv", view=topic.report_preview_csv_view, name="report_preview_csv"),
    path("meter/production/json/<path:meter>",
         view=meter.meter_production_data_json, name="meter_production_data_json"),
    path("meter/financial_value/json/<path:meter>",
         view=meter.meter_financial_value_data_json, name="meter_financial_value_data_json"),
    path("meter/json/<path:meter>", view=meter.meter_data_json, name="meter_data_json"),
    path("meter/import/<path:meter>", view=meter.meter_data_import, name="meter_data_import"),
    path("meter/solaredge_import/<path:meter>", view=meter.meter_solaredge_data_import,
         name="meter_solaredge_data_import"),
    path("weather_station/json/<path:weather_station_id>", view=weather.weather_data_json, name="weather_data_json"),
    path("weather_station/view/<path:weather_station_id>",
         view=weather.weather_station_detail, name="weather_station_detail"),
    path("weather_station/fetch/<path:weather_station_id>",
         view=weather.weather_station_fetch_data, name="weather_station_fetch_data"),
    path("weather_station.json", view=weather.weather_stations_json, name="weather_stations_json"),
    path("utility_rates.json", view=meter.utility_rates_json, name="utility_rates_json"),
    path("meter_rate_plan_history/", view=meter.meter_rate_plan_history, name="meter_rate_plan_history"),
    path("meter_rate_plan_history_detail/<str:rate_plan_history_id>", view=meter.meter_rate_plan_history_detail,
         name="meter_rate_plan_history_detail"),
    path("meter_rate_plan_history_edit/<str:rate_plan_history_id>", view=meter.meter_rate_plan_history_edit,
         name="meter_rate_plan_history_edit"),
    path("utilityapi/data_import/<path:meter_id>", view=utilityapi.data_import_view,
         name="utilityapi_data_import"),
    path("utilityapi/meters_import/<path:site_id>", view=utilityapi.meters_import_view,
         name="utilityapi_meters_import"),
    path("utilityapi/meters.json", view=utilityapi.meters, name="utilityapi_meters_json"),
    path("utilityapi/meter_data_import/<path:meter_id>", view=utilityapi.meter_data_import,
         name="utilityapi_meter_data_import"),
    path("utilityapi/meter_bills_import/<path:meter_id>", view=utilityapi.meter_bills_import,
         name="utilityapi_meter_bills_import"),
    path("utilityapi/meters_data_import/<path:site_id>", view=utilityapi.meters_data_import,
         name="utilityapi_meters_data_import"),
    path("uom.json", view=common.uom_list_json_view, name="uom_list_json"),
]
