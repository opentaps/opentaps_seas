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

from django.db import migrations
from django.db import connections
from django.db import OperationalError


def check_schema(apps, schema_editor):
    try:
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
    except OperationalError:
        print('Crate database unavailable !!!')
    else:
        print("!!!!!!!!!!!!")
        print("This migration only updates the database schema.")
        print("To migrate the data use the following script:")
        print("")
        print("python manage.py runscript copy_crate_entity_tags_to_topics")
        print("")
        print("!!!!!!!!!!!!")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_auto_20191202_2228'),
    ]

    operations = [
        migrations.RunPython(check_schema),
    ]
