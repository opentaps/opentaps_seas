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
from django.db import models
from django.db.models import CharField
from cratedb.fields import HStoreField as CrateHStoreField
from cratedb.fields import ArrayField as CrateArrayField
from opentaps_seas.core.models import ensure_crate_entity_table
from opentaps_seas.core.models import sync_tags_to_crate_entity


# Redefine the old CrateEntity class for usage in this script
class CrateEntity(models.Model):
    topic = CharField("Topic", max_length=255, primary_key=True)
    kv_tags = CrateHStoreField(blank=True, null=True)
    m_tags = CrateArrayField(CharField(max_length=255, blank=True, null=True))

    tried_related_point = False
    related_point = None

    class Meta:
        app_label = "core"
        managed = False
        db_table = 'entity'

    class Db:
        cratedb = True


def check_schema():
    print('Creating missing column if needed ...')
    with connections['crate'].cursor() as c:
        try:
            c.execute("""ALTER TABLE "volttron"."topic"
                         ADD COLUMN "kv_tags" OBJECT (DYNAMIC) AS (
                          "dis" STRING,
                          "id" STRING
                         );""")
        except Exception as e:
            print(e)

        try:
            c.execute("""ALTER TABLE "volttron"."topic" ADD COLUMN "m_tags" ARRAY(STRING);""")
        except Exception as e:
            print(e)

        c.close()


def copy_crate_entity_tags_to_topics():
    count = 0
    # first make sure the CrateDB table already exists
    ensure_crate_entity_table()

    # iterate the topic data points and copy the tags
    for row in CrateEntity.objects.all():
        print(" --> {} with {} and {}".format(row.topic, row.m_tags, row.kv_tags))
        sync_tags_to_crate_entity(row)
        count = count + 1

    print(count, "topics have been processed")


def run():
    check_schema()
    copy_crate_entity_tags_to_topics()
