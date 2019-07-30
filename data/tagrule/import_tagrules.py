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

import os
import sys
from psycopg2 import connect
from psycopg2.extras import register_hstore
from django.core.management import execute_from_command_line


def get_connection():
    connection = connect(dbname='opentaps_seas')
    register_hstore(connection)
    return connection


def clean():
    conn = get_connection()
    cursor = conn.cursor()

    print('Deleting data ...')
    cursor.execute('DELETE FROM core_topictagrule;')
    cursor.execute('DELETE FROM core_topictagruleset;')
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
    # note: we import the rules using the Django service
    execute_from_command_line('manage.py runscript import_tagruleset --script-args {}'.format(source_file_name).split())


def print_help():
    print("Usage: python import_tagrules.py [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")


if __name__ == '__main__':
    # setup for the django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    # important: add the root dir where manage.py is, and our main app dir
    current_path = os.path.split(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])[0]
    sys.path.append(os.path.join(current_path, "opentaps_seas"))
    sys.path.append(current_path)
    if len(sys.argv) == 1:
        print_help()
    if 'clean' in sys.argv:
        clean()
    if 'all' in sys.argv or 'clean' in sys.argv or 'seed' in sys.argv:
        seed()
    if 'all' in sys.argv or 'demo' in sys.argv:
        demo()
