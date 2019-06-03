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
from datetime import datetime
from datetime import timedelta
import os
import sys
from crate.client import connect
from crate.client.exceptions import ProgrammingError
from psycopg2 import connect as pgconnect
from psycopg2 import IntegrityError
from psycopg2.extras import register_hstore

CRATE_HOST = 'localhost:4200'


def get_connection():
    connection = connect(CRATE_HOST, error_trace=True)
    return connection


def get_pgconnection():
    pgconnection = pgconnect(dbname='opentaps_seas')
    register_hstore(pgconnection)
    return pgconnection


def clean():
    conn = get_connection()
    cursor = conn.cursor()

    print('Deleting data ...')
    cursor.execute("DELETE FROM volttron.data where topic like 'demo_%';")
    cursor.execute("DELETE FROM volttron.topic where topic like 'demo_%';")

    cursor.close()
    conn.close()

    pgconnection = get_pgconnection()
    pgcursor = pgconnection.cursor()
    pgcursor.execute("DELETE FROM core_entity where entity_id = '_demo_site';")
    pgcursor.execute("DELETE FROM core_entity where entity_id like '_demo_equip%';")
    pgcursor.execute("DELETE FROM core_entity where entity_id like 'demo_%';")
    pgconnection.commit()
    pgcursor.close()
    pgconnection.close()


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


def ensure_topic(cursor, topic):
    try:
        cursor.execute("""INSERT INTO volttron.topic (topic) VALUES (?)""", (topic,))
        print('-- INSERT topic: ', topic)
    except ProgrammingError:
        print('-- Topic already exists: ', topic)
        pass


def import_entities(source_file_name):
    name = os.path.splitext(os.path.basename(source_file_name))[0]
    f = open(source_file_name, 'r')
    reader = csv.reader(f)

    conn = get_connection()
    cursor = conn.cursor()

    first_row = True
    header = None
    ts = None
    counter_insert = 0
    row_index = 0
    # topics are each column minus the first 2 (timestamp, systemID)
    # we'll prefix them as demo_"device name"/"topic" (device name being the basename of the file)
    # ignore columns like VAVID that are not data column and repeat the ID present in the following columns
    ignores = []
    # write CSVs for each timeseries so we can bulk import them rather than doing millions of inserts
    csv_writers = {}
    for row in reader:
        index = -1
        row_index = row_index + 1
        if first_row:
            header = row
            first_row = False
            for item in row:
                index = index + 1
                if index < 2:
                    continue
                if 'VAVID' == item:
                    ignores.append(index)
                    continue
                topic = 'demo_' + name + '/' + item
                csv_writers[item] = {}
                fname = '/tmp/' + name + '_' + item + '.csv'
                csv_writers[item]['started'] = False
                csv_writers[item]['filename'] = fname
                csv_writers[item]['topic'] = topic

        else:
            for item in row:
                index = index + 1
                if index == 0:
                    # reset timestamp, to alway generate timeseries starting at time of the import
                    # we start at now and go backward in time instead of reading the CSV time
                    ts = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                    # each row represents 1 minute
                    ts = ts - timedelta(0, row_index * 60)
                if index < 2 or not item or index in ignores:
                    continue

                topic_name = header[index]

                csv_writer = csv_writers[topic_name]
                if not csv_writer['started']:
                    ensure_topic(cursor, csv_writer['topic'])
                    fp = open(csv_writer['filename'], 'w', newline='')
                    csv_writer['fp'] = fp
                    csv_writer['writer'] = csv.writer(fp)
                    csv_writer['writer'].writerow(['ts', 'topic', 'string_value'])
                    csv_writer['started'] = True

                csv_writer['writer'].writerow([ts.strftime('%Y-%m-%dT%H:%M:%S.000Z'), csv_writer['topic'], item])
                print('-- PREPARE data {} row: {} topic {}'.format(name, row_index, csv_writer['topic']))

    print('---------------------')
    print('-- PREPARE data {} done.'.format(name))
    print('---------------------')
    pgconnection = get_pgconnection()
    pgcursor = pgconnection.cursor()

    try:
        tags = {
            'id': '_demo_site',
            'dis': 'Demo Site',
            'geoAddr': 'Richland, WA',
            'geoCity': 'Richland',
            'geoState': 'WA'
        }
        mtags = ['site']
        pgcursor.execute("""INSERT INTO core_entity (entity_id, kv_tags, m_tags)
            VALUES (%s, %s, %s)""", [tags['id'], tags, mtags])
        pgconnection.commit()
    except IntegrityError:
        pgconnection.rollback()

    try:
        tags = {
            'id': '_demo_equip' + name,
            'dis': 'Demo Equipment ' + name,
            'siteRef': '_demo_site',
        }
        mtags = ['equip']
        pgcursor.execute("""INSERT INTO core_entity (entity_id, kv_tags, m_tags)
            VALUES (%s, %s, %s)""", [tags['id'], tags, mtags])
        pgconnection.commit()
    except IntegrityError:
        pgconnection.rollback()

    for item, csv_writer in csv_writers.items():
        if csv_writer['started']:
            print('-- INSERT CSV data {} file: {}'.format(name, csv_writer['filename']))
            try:
                csv_writer['fp'].close()
                sql = "COPY volttron.data FROM '{}'".format(csv_writer['filename'])
                print('-- INSERT: ', sql)
                cursor.execute(sql)
                print('-- Cleanup CSV file: {}'.format(csv_writer['filename']))
                os.remove(csv_writer['filename'])
                counter_insert += 1
            except ProgrammingError:
                print('-- ERROR loading data: {}'.format(csv_writer['filename']))
                raise

            print('-- Create Demo Point with topic {}'.format(csv_writer['topic']))

            try:
                tags = {
                    'id': csv_writer['topic'],
                    'dis': 'Demo point for ' + csv_writer['topic'],
                    'kind': 'Number',
                    'siteRef': '_demo_site',
                    'equipRef': '_demo_equip' + name,
                }
                mtags = ['point', 'his']
                pgcursor.execute("""INSERT INTO core_entity (entity_id, topic, kv_tags, m_tags)
                    VALUES (%s, %s, %s, %s)""", [csv_writer['topic'], csv_writer['topic'], tags, mtags])
                pgconnection.commit()
            except IntegrityError:
                pgconnection.rollback()

    print('{0} timeseries have been successfully processed'.format(counter_insert))

    pgcursor.close()
    pgconnection.close()
    cursor.close()
    conn.close()


def print_help():
    print("Usage: python import_entities.py [all|seed|demo] [clean]")
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
