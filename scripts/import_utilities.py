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
from django.db import connections
from django.db.utils import IntegrityError


def clean():
    print('Deleting data ...')
    with connections['default'].cursor() as c:
        c.execute("DELETE FROM eemeter_baselinemodel;")
        c.execute("DELETE FROM core_financial_transaction_history;")
        c.execute("DELETE FROM core_financial_transaction;")
        c.execute("DELETE FROM core_meter_financial_value;")
        c.execute("DELETE FROM core_meter_production;")
        c.execute("DELETE FROM core_meter_history;")
        c.execute("DELETE FROM core_solaredgesetting;")
        c.execute("DELETE FROM core_meter_rate_plan_history;")
        c.execute("DELETE FROM core_meter;")
        c.execute("DELETE FROM core_utility;")
        c.close()


def demo():
    import_files('demo')


def seed():
    import_files('seed')


def import_files(which):
    print('Importing {} data...'.format(which))
    dirname = os.path.dirname(os.path.realpath(__file__))
    dirname = dirname.replace('scripts', 'data/utility')
    mypath = os.path.join(dirname, which)
    print(mypath)
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

    first_row = True
    counter_insert = 0
    counter_update = 0
    with connections['default'].cursor() as c:
        for row in reader:
            if first_row:
                first_row = False
            else:
                utility_id = row[0]
                utility_name = row[1]
                state = row[2]
                country = row[3]
                division_type = row[4]
                division_id = row[5]

                try:
                    c.execute("""INSERT INTO core_utility
                        (utility_id, utility_name, state, country, division_type, division_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """, [utility_id, utility_name, state, country, division_type, division_id])
                    counter_insert += 1
                    print('-- INSERT utility: ', utility_id)

                except IntegrityError:
                    c.execute("""UPDATE core_utility
                        SET utility_name = %s, state = %s, country = %s, division_type = %s, division_id = %s
                        WHERE utility_id = %s
                        """, [utility_name, state, country, division_type, division_id, utility_id])
                    counter_update += 1
                    print('-- UPDATE utility: ', utility_id)

    print('{0} rows have been successfully processed {1} '
          'inserted {2} updated.'.format(counter_insert+counter_update, counter_insert, counter_update))


def print_help():
    print("Usage: python manage.py runscript import_utilities --script-args [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")


def run(*args):
    if len(args) > 0:
        if 'clean' in args:
            clean()
        if 'all' in args or 'clean' in args or 'seed' in args:
            seed()
        if 'all' in args or 'demo' in args:
            demo()
    else:
        print_help()
