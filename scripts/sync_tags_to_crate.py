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

from django.db import connections
from opentaps_seas.core.models import Entity
from opentaps_seas.core.models import Topic


def kv_tags_update_string(kv_tags, params_list):
    res = '{'
    first = True
    for k in kv_tags.keys():
        if not first:
            res += ', '
        res += "{} = %s".format(k, kv_tags[k])
        params_list.append(kv_tags[k])
        first = False
    res += '}'
    return res


def sync_tags_to_crate():
    count = 0
    # first make sure the CrateDB Topic table has the m_tags and kv_tags fields
    # note: ignore Error in case the column already exists
    with connections['crate'].cursor() as c:
        sql = """ALTER TABLE "volttron"."topic" ADD COLUMN "m_tags" array(string);"""
        try:
            c.execute(sql)
            print("Added CrateDB topic.m_tags column")
        except Exception:
            print("CrateDB topic.m_tags column already exists")
            pass

        sql = """ALTER TABLE "volttron"."topic" ADD COLUMN "kv_tags" object;"""
        try:
            c.execute(sql)
            print("Added CrateDB topic.kv_tas column")
        except Exception:
            print("CrateDB topic.kv_tas column already exists")
            pass

        entities = Entity.objects.raw('''SELECT entity_id, topic, m_tags, kv_tags FROM {0}
            WHERE 'point' = ANY (m_tags)
            AND topic is not null
            AND topic != '' '''.format(Entity._meta.db_table), [])

        # iterate the topic data points and copy the tags
        for row in entities:
            # make sure the topic is in CrateDB
            print(" --> {}".format(row.topic))
            Topic.ensure_topic_exists(row.topic)

            if row.m_tags or row.kv_tags:
                params_list = []
                sql = """ UPDATE "volttron"."topic" SET """
                if row.kv_tags:
                    sql += " kv_tags = {} ".format(kv_tags_update_string(row.kv_tags, params_list))
                if row.m_tags:
                    if row.kv_tags:
                        sql += ", "
                    sql += " m_tags = %s "
                    params_list.append(row.m_tags)
                sql += """ WHERE topic = %s;"""
                params_list.append(row.topic)
                c.execute(sql, params_list)

            count = count + 1

    print(count, "points have been processed")


def run():
    sync_tags_to_crate()
