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
from opentaps_seas.core.models import ensure_opentapsease_crate_entity_table
from opentaps_seas.core.models import sync_tags_to_opentapsease_crate_entity


def sync_tags_to_crate():
    count = 0
    # first make sure the CrateDB Entity table already exists
    ensure_opentapsease_crate_entity_table()
    print("Added CrateDB opentaps_seas.entity table")

    entities = Entity.objects.raw('''SELECT entity_id, topic, m_tags, kv_tags FROM {0}
        WHERE 'point' = ANY (m_tags)
        AND topic is not null
        AND topic != '' '''.format(Entity._meta.db_table), [])

    # iterate the topic data points and copy the tags
    for row in entities:
        print(" --> {}".format(row.topic))
        sync_tags_to_opentapsease_crate_entity(row)

        count = count + 1

    print(count, "points have been processed")


def run():
    sync_tags_to_crate()
