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

import logging
from opentaps_seas.core.models import Entity
from opentaps_seas.core.utils import delete_grafana_dashboard
from opentaps_seas.core.utils import delete_grafana_dashboard_snapshot

logger = logging.getLogger(__name__)


def remove_dashboards(run_type):
    count = 0
    error_count = 0
    ok_count = 0
    not_found_ids = []

    if run_type in ['all', 'points']:
        entities = Entity.objects.raw('''SELECT entity_id, topic, dashboard_uid, dashboard_snapshot_uid FROM {0}
            WHERE ('point' = ANY (m_tags))
            AND (dashboard_uid is not null)
            AND (dashboard_uid != '') '''.format(Entity._meta.db_table), [])

        for row in entities:
            count += 1
            logger.info("Delete point dashboard, entity_id = %s, dashboard_uid = %s", row.entity_id, row.dashboard_uid)
            result = delete_grafana_dashboard(row.dashboard_uid)
            if result is not None:
                if result.status_code == 200:
                    ok_count += 1
                    row.dashboard_uid = ''
                    row.save()
                if result.status_code == 404:
                    # Not found
                    not_found_ids.append({"entity_id": row.entity_id, "dashboard_uid": row.dashboard_uid})
                    error_count += 1
            else:
                error_count += 1

    if run_type in ['all', 'equipments']:
        entities = Entity.objects.raw('''SELECT entity_id, topic, dashboard_uid, dashboard_snapshot_uid FROM {0}
            WHERE ('equip' = ANY (m_tags))
            AND (dashboard_uid is not null)
            AND (dashboard_uid != '') '''.format(Entity._meta.db_table), [])

        for row in entities:
            count += 1
            logger.info("Delete equipment dashboard, entity_id = %s, dashboard_uid = %s", row.entity_id, row.dashboard_uid)
            result = delete_grafana_dashboard(row.dashboard_uid)
            if result is not None:
                if result.status_code == 200:
                    ok_count += 1
                    row.dashboard_uid = ''
                    if row.dashboard_snapshot_uid:
                        result_s = delete_grafana_dashboard_snapshot(row.dashboard_snapshot_uid)
                        if result_s.status_code == 200:
                            row.dashboard_snapshot_uid = ''
                    row.save()
                if result.status_code == 404:
                    # Not found
                    not_found_ids.append({"entity_id": row.entity_id, "dashboard_uid": row.dashboard_uid})
                    error_count += 1
            else:
                error_count += 1

    if count > 0:
        logger.info("%s dashboards of %s have been removed", ok_count, count)
        if error_count:
            logger.error("%s errors", error_count)
        if not_found_ids:
            logger.error("not found dashboards list %s", not_found_ids)
    else:
        logger.info("No dashboards to remove")


def print_help():
    print("Usage: python manage.py runscript remove_dashboards --script-args all|equipments|points")


def run(*args):
    if len(args) > 0:
        if args[0] in ['all', 'equipments', 'points']:
            remove_dashboards(args[0])
        else:
            print_help()
    else:
        print_help()
