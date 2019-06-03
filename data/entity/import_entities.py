#!/usr/bin/env python
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

import csv
import os
import sys
from psycopg2 import connect
from psycopg2 import IntegrityError
from psycopg2.extras import register_hstore
from django.template.defaultfilters import slugify


def get_connection():
    connection = connect(dbname='opentaps_seas')
    register_hstore(connection)
    return connection


def clean():
    conn = get_connection()
    cursor = conn.cursor()

    print('Deleting data ...')
    cursor.execute('DELETE FROM core_entity;')

    cursor.close()
    conn.commit()
    conn.close()


def demo():
    import_files('demo')


def seed():
    import_files('seed')


def import_files(which):
    print('Importing {} data...'.format(which))
    mypath = os.path.join(os.path.dirname(os.path.realpath(__file__)), which)
    if os.path.isdir(mypath):
        for f in os.listdir(mypath):
            filename = os.path.join(mypath, f)
            if os.path.isfile(filename):
                print('Importing {} data [{}]'.format(which, filename))
                import_entities(filename)
    else:
        print('No {} data to import.'.format(which))


def import_entities(source_file_name):
    f = open(source_file_name, 'r')
    reader = csv.reader(f)

    conn = get_connection()
    cursor = conn.cursor()

    first_row = True
    header = None
    id_index = 0
    topic_index = 0
    counter_insert = 0
    counter_update = 0
    for row in reader:
        if first_row:
            header = row
            index = 0
            first_row = False
            for item in row:
                if item == "id":
                    id_index = index
                if item == "topicRef":
                    topic_index = index
                index = index + 1
        else:
            entity_id = slugify(row[id_index])
            topic = row[topic_index]
            kv_tags = {}
            m_tags = []
            index = 0
            for item in row:
                # for no do not store topic as a tag as this goes directly in the topic field
                if index == topic_index:
                    index = index + 1
                    continue
                if item == "M":
                    m_tags.append(header[index])
                elif item is not None and item != "":
                    kv_tags[header[index]] = item
                index = index + 1

            try:
                cursor.execute("""INSERT INTO core_entity (entity_id, topic, kv_tags, m_tags, dashboard_uid)
                    VALUES (%s, %s, %s, %s, %s)""", [entity_id, topic, kv_tags, m_tags, ''])
                counter_insert += 1
                print('-- INSERT entity: ', entity_id)
                conn.commit()
            except IntegrityError:
                conn.rollback()
                cursor.execute("""UPDATE core_entity SET topic = %s, kv_tags = %s, m_tags = %s
                    WHERE entity_id = %s""", [topic, kv_tags, m_tags, entity_id])
                counter_update += 1
                print('-- UPDATE entity: ', entity_id)
                conn.commit()

    print('{0} rows have been successfully processed {1} '
          'inserted {2} updated.'.format(counter_insert+counter_update, counter_insert, counter_update))

    cursor.close()
    conn.commit()
    conn.close()


def print_help():
    print("Usage: python import_entities.py [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print_help()
    if 'clean' in sys.argv:
        clean()
    if 'all' in sys.argv or 'clean' in sys.argv or 'seed' in sys.argv:
        seed()
    if 'all' in sys.argv or 'demo' in sys.argv:
        demo()
