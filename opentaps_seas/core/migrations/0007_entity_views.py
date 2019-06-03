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
        ('core', '0006_entity_postgres'),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_entity_view;
            CREATE OR REPLACE VIEW core_entity_view AS
                SELECT entity_id,
                kv_tags->'dis' as description
                FROM core_entity;
            """,
            reverse_sql='DROP VIEW IF EXISTS core_entity_view;'
        ),
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_site_view;
            CREATE OR REPLACE VIEW core_site_view AS
                SELECT entity_id,
                kv_tags->'dis' as description,
                kv_tags->'geoState' as state,
                kv_tags->'geoCity' as city,
                kv_tags->'area' as area
                FROM core_entity
                WHERE 'site' = ANY(m_tags);
            """,
            reverse_sql='DROP VIEW IF EXISTS core_site_view;'
        ),
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_equipment_view;
            CREATE OR REPLACE VIEW core_equipment_view AS
                SELECT entity_id,
                kv_tags->'dis' as description,
                kv_tags->'siteRef' as site_id
                FROM core_entity
                WHERE 'equip' = ANY(m_tags);
            """,
            reverse_sql='DROP VIEW IF EXISTS core_equipment_view;'
        ),
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_machine_view;
            CREATE OR REPLACE VIEW core_machine_view AS
                SELECT entity_id,
                kv_tags->'dis' as description,
                kv_tags->'manufacturer' as manufacturer,
                kv_tags->'model' as model,
                kv_tags->'yearBuilt' as year
                FROM core_entity
                WHERE 'machine' = ANY(m_tags);
            """,
            reverse_sql='DROP VIEW IF EXISTS core_machine_view;'
        ),
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS core_point_view;
            CREATE OR REPLACE VIEW core_point_view AS
                SELECT entity_id,
                topic,
                'N/A' as current_value,
                kv_tags->'dis' as description,
                kv_tags->'kind' as kind,
                kv_tags->'unit' as unit,
                kv_tags->'siteRef' as site_id,
                kv_tags->'equipRef' as equipment_id
                FROM core_entity
                WHERE 'point' = ANY(m_tags);
            """,
            reverse_sql='DROP VIEW IF EXISTS core_point_view;'
        ),
    ]
