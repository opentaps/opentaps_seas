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

import json
import os
from django.db import connections
from django.db.utils import IntegrityError
from django.template.defaultfilters import slugify

def clean():
    print('Deleting entity data ...')
    with connections['default'].cursor() as c:
        c.execute("DELETE FROM core_meter_history;")
        c.execute("DELETE FROM core_meter;")
        c.execute("DELETE FROM core_entity;")
        c.close()

    print('Deleting crate database entity data ...')
    with connections['crate'].cursor() as c:
        c.execute("DELETE FROM topic;")
        c.close()


def demo(filters):
    import_files('demo', filters)


def seed():
    import_files('seed')


def import_files(which, filters=[]):
    print('Importing {} data...'.format(which))
    dirname = os.path.dirname(os.path.realpath(__file__))
    dirname = dirname.replace('scripts', 'data/entity')
    mypath = os.path.join(dirname, which)
    print(mypath)
    if os.path.isdir(mypath):
        for f in os.listdir(mypath):
            filename = os.path.join(mypath, f)
            if os.path.isfile(filename):
                print('Importing {} data [{}]'.format(which, filename))
                import_entities(filename, filters)

    else:
        print('No {} data to import.'.format(which))


def import_entities(source_file_name, filters):
    reader = None
    with open(source_file_name) as f:
        reader = json.loads(f.read())

    counter_insert = 0
    counter_update = 0
    with connections['default'].cursor() as c:
        for row in reader['entities']:
            entity_id = slugify(row['entity_id'])
            topic = row.get('topic')
            kv_tags = row.get('kv_tags', {})
            m_tags = row.get('m_tags', [])

            if filters:
                skip = True
                # check the entity matches all the filters
                for f in filters:
                    if f.startswith('~'):
                        f = f[1:]
                        if f not in m_tags:
                            skip = False
                            break
                    elif f in m_tags:
                        skip = False
                        break
                if skip:
                    print('-- SKIP entity: {}, tags {} not matching any filter {}'.format(entity_id, m_tags, filters))
                    continue
            try:
                c.execute("""INSERT INTO core_entity (entity_id, topic, kv_tags, m_tags, dashboard_uid)
                    VALUES (%s, %s, %s, %s, %s)""", [entity_id, topic, kv_tags, m_tags, ''])
                counter_insert += 1
                print('-- INSERT entity: ', entity_id)
            except IntegrityError:
                c.execute("""UPDATE core_entity SET topic = %s, kv_tags = %s, m_tags = %s
                    WHERE entity_id = %s""", [topic, kv_tags, m_tags, entity_id])
                counter_update += 1
                print('-- UPDATE entity: ', entity_id)

    print('{0} rows have been successfully processed {1} '
          'inserted {2} updated.'.format(counter_insert+counter_update, counter_insert, counter_update))


def print_help():
    print("Usage: python manage.py runscript import_entities --script-args [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")
    print("  entity_mtag=[m_tag]: optional, only import demo entities matching any of the given m_tag, eg: site")
    print("    can provide multiple filters, eg: site,equip")
    print("    can prefix a tag with ~ to negate eg: ~point matches all those that are not point")


def run(*args):
    if len(args) > 0:
        filters = []
        for a in args:
            if a.startswith('entity_mtag='):
                filters = a[len('entity_mtag='):].split(',')
                print("Filtering entities matching m_tag = {}".format(filters))
        if 'clean' in args:
            clean()
        if 'all' in args or 'clean' in args or 'seed' in args:
            seed()
        if 'all' in args or 'demo' in args:
            demo(filters)
    else:
        print_help()
