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

logger = logging.getLogger(__name__)


def remove_dashboards():
    entities = Entity.objects.raw('''SELECT entity_id, topic, dashboard_uid FROM {0}
        WHERE 'point' = ANY (m_tags)
        AND topic is not null
        AND topic != ''
        AND (dashboard_uid is not null)
        AND (dashboard_uid != '') '''.format(Entity._meta.db_table), [])

    count = 0
    error_count = 0
    ok_count = 0
    not_found_ids = []
    for row in entities:
        count += 1
        logger.info("Delete dashboard, entity_id = %s, dashboard_uid = %s", row.entity_id, row.dashboard_uid)
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

    if count > 0:
        logger.info("%s dashboards of %s have been removed", ok_count, count)
        if error_count:
            logger.error("%s errors", error_count)
        if not_found_ids:
            logger.error("not found dashboards list %s", not_found_ids)
    else:
        logger.info("No dashboards to remove")


def run():
    remove_dashboards()
