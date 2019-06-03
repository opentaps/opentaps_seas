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


def get_connection():
    connection = connect(dbname='opentaps_seas')
    return connection


def clean():
    conn = get_connection()
    cursor = conn.cursor()

    print('Deleting data ...')
    cursor.execute('DELETE FROM core_timezone;')
    conn.commit()

    cursor.close()
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
    counter_insert = 0
    counter_update = 0
    for row in reader:
        if first_row:
            first_row = False
        else:
            id = row[0]
            time_zone = row[1]
            tzoffset = row[2]
            tzoffset_dst = row[3]
            gids = row[4]
            geo_ids = []
            if gids:
                for gid in [x.strip() for x in gids.split(',')]:
                    geo_ids.append(gid)

            try:
                cursor.execute("""INSERT INTO core_timezone (id, time_zone, tzoffset, tzoffset_dst, geo_ids)
                    VALUES (%s, %s, %s, %s, %s)""", [id, time_zone, tzoffset, tzoffset_dst, geo_ids])
                counter_insert += 1
                print('-- INSERT time zone: ', time_zone)
                conn.commit()
            except IntegrityError:
                conn.rollback()
                cursor.execute("""UPDATE core_timezone SET time_zone = %s, tzoffset = %s, tzoffset_dst = %s,
                    geo_ids = %s WHERE id = %s""", [time_zone, tzoffset, tzoffset_dst, geo_ids, id])
                counter_update += 1
                print('-- UPDATE time zone: ', time_zone)
                conn.commit()

    print('{0} rows have been successfully processed {1} '
          'inserted {2} updated.'.format(counter_insert+counter_update, counter_insert, counter_update))

    cursor.close()
    conn.commit()
    conn.close()


def print_help():
    print("Usage: python import_timezones.py [all|seed|demo] [clean]")
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
