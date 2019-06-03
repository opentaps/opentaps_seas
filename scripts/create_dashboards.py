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

from opentaps_seas.core.models import Entity
from opentaps_seas.core.utils import create_grafana_dashboard


def create_dashboards(file_name):
    entities = Entity.objects.raw('''SELECT entity_id, topic, dashboard_uid FROM {0}
        WHERE 'point' = ANY (m_tags)
        AND topic is not null
        AND topic != ''
        AND (dashboard_uid is null or dashboard_uid = '') '''.format(Entity._meta.db_table), [])

    count = 0
    for row in entities:
        r = create_grafana_dashboard(row.topic)

        if r:
            print("Status:", r.status_code)
            result = r.json()
            if (r.status_code != 200):
                print(r.json())
            else:
                print(row.topic + ", dashboard uid :", result["uid"])
                if (result["uid"]):
                    row.dashboard_uid = result["uid"]
                    row.save()

        count = count + 1

    print(count, "points have been processed")


def run():
    create_dashboards("")
