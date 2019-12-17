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
import csv
import os
from crate.client.exceptions import ProgrammingError
from django.db import connections
from django.db.utils import IntegrityError
from datetime import datetime
from datetime import timedelta
from django.template.defaultfilters import slugify

GLB_OPTIONS = {
    'ahu_no_point': False
}


def clean():
    print('Deleting crate database data ...')
    with connections['crate'].cursor() as c:
        c.execute("DELETE FROM data where topic like 'demo_%';")
        c.execute("DELETE FROM topic where topic like 'demo_%';")
        c.close()

    print('Deleting entity data ...')
    with connections['default'].cursor() as c:
        c.execute("DELETE FROM core_entity where entity_id like 'demo-site%';")
        c.execute("DELETE FROM core_entity where topic like 'demo_%';")
        c.close()


def demo():
    import_files('demo')


def seed():
    import_files('seed')


def ensure_topic(topic):
    with connections['crate'].cursor() as c:
        sql = """INSERT INTO {0} (topic) VALUES (%s)""".format("topic")
        try:
            c.execute(sql, [topic])
            print('-- INSERT topic: ', topic)
        except Exception:
            print('-- Topic already exists: ', topic)
            pass


def import_files(which):
    print('Importing {} data...'.format(which))
    dirname = os.path.dirname(os.path.realpath(__file__))
    dirname = dirname.replace('scripts', 'data/ahu')
    mypath = os.path.join(dirname, which)
    print(mypath)
    if os.path.isdir(mypath):
        for f in os.listdir(mypath):
            filename = os.path.join(mypath, f)
            if os.path.isfile(filename):
                print('Importing {} data [{}]'.format(which, filename))
                if '.json' in filename:
                    import_json(filename)
                elif '.csv' in filename:
                    import_csv(filename)
        for f in os.listdir(mypath):
            filename = os.path.join(mypath, f)
            if os.path.isfile(filename):
                if filename.endswith('.sql'):
                    print('Running SQL {} [{}]'.format(which, filename))
                    import_sql(filename)

    else:
        print('No {} data to import.'.format(which))


def import_json(source_file_name):
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


def import_sql(source_file_name):
    with open(source_file_name) as f:
        sqlCommands = filter(None, f.read().split(';'))

        with connections['default'].cursor() as c:
            for sql in sqlCommands:
                if sql and sql.strip():
                    c.execute(sql)
                    print('-- SQL: ', sql)
            c.close()


def import_csv(source_file_name):
    name = os.path.splitext(os.path.basename(source_file_name))[0]
    f = open(source_file_name, 'r')
    reader = csv.reader(f)

    first_row = True
    header = None
    ts = None
    counter_insert = 0
    row_index = 0
    # topics are each column minus the first 2 (timestamp, systemID)
    # we'll prefix them as demo_site1/demo_"device name"/"topic" (device name being the basename of the file)
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
                topic = 'demo_site1/demo_' + name + '/' + item
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
                    ensure_topic(csv_writer['topic'])
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

    # note: for Site we use data/entities/demo_site.json
    for item, csv_writer in csv_writers.items():
        if csv_writer['started']:
            print('-- INSERT CSV data {} file: {}'.format(name, csv_writer['filename']))
            with connections['crate'].cursor() as c:
                try:
                    csv_writer['fp'].close()
                    sql = "COPY data FROM '{}'".format(csv_writer['filename'])
                    print('-- INSERT: ', sql)
                    c.execute(sql)
                    print('-- Cleanup CSV file: {}'.format(csv_writer['filename']))
                    os.remove(csv_writer['filename'])
                    counter_insert += 1
                except ProgrammingError:
                    print('-- ERROR loading data: {}'.format(csv_writer['filename']))
                    raise
                c.close()

            if not GLB_OPTIONS['ahu_no_point']:
                print('-- Create Demo Point with topic {}'.format(csv_writer['topic']))

                with connections['default'].cursor() as c:
                    try:
                        tags = {
                            'id': csv_writer['topic'],
                            'dis': 'Demo point for ' + csv_writer['topic'],
                            'kind': 'Number',
                            'siteRef': '@Demo-Site-1'
                        }
                        mtags = ['point', 'his', 'sensor']
                        c.execute("""INSERT INTO core_entity (entity_id, topic, kv_tags, m_tags, dashboard_uid)
                            VALUES (%s, %s, %s, %s, %s)""", [csv_writer['topic'], csv_writer['topic'], tags, mtags, ''])

                    except IntegrityError as e:
                        print('?? Error: ', e)
                    c.close()

    print('{0} timeseries have been successfully processed'.format(counter_insert))


def print_help():
    print("Usage: python manage.py runscript import_data --script-args [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")
    print("  ahu_no_point: optional, do not create the data point")


def run(*args):
    if len(args) > 0:
        GLB_OPTIONS['ahu_no_point'] = 'ahu_no_point' in args
        if 'clean' in args:
            clean()
        if 'all' in args or 'clean' in args or 'seed' in args:
            seed()
        if 'all' in args or 'demo' in args:
            demo()
    else:
        print_help()
