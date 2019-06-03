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


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20190424_0745'),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_machine_view;
            DROP VIEW IF EXISTS core_model_view;
            CREATE OR REPLACE VIEW core_model_view AS
                SELECT entity_id,
                kv_tags->'dis' as description
                FROM core_entity
                WHERE 'model' = ANY(m_tags);

            UPDATE core_entity
            SET m_tags = array_append(m_tags, 'model')
            WHERE 'machine' = ANY(m_tags) AND 'model' != ANY(m_tags);

            UPDATE core_entity
            SET kv_tags = (kv_tags || (CONCAT('modelRef=>"', kv_tags->'machineRef', '"'))::hstore) - 'machineRef'::text
            WHERE kv_tags?'machineRef';

            UPDATE core_entity
            SET kv_tags = (kv_tags || (CONCAT('modelName=>"', kv_tags->'model', '"'))::hstore) - 'model'::text
            WHERE kv_tags?'model';

            UPDATE core_entity
            SET m_tags = array_remove(m_tags, 'machine')
            WHERE 'model' = ANY(m_tags);
            """,
            reverse_sql='DROP VIEW IF EXISTS core_model_view;'
        ),
    ]
