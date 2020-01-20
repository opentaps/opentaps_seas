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

from django.db import connections
from opentaps_seas.eemeter import utils


def clean():
    print('Deleting data ...')
    with connections['default'].cursor() as c:
        c.execute("""DELETE FROM core_weather_history WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_weather_history WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_meter_history WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_meter_production WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_site_weather_stations WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_meter_production WHERE meter_id IN
                     (SELECT meter_id FROM core_meter WHERE weather_station_id = 'eemeter_ws');""")
        c.execute("""DELETE FROM eemeter_baselinemodel WHERE meter_id IN
                     (SELECT meter_id FROM core_meter WHERE weather_station_id = 'eemeter_ws');""")
        c.execute("""DELETE FROM core_meter WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_weather_station WHERE weather_station_id = 'eemeter_ws';""")
        c.close()


def demo():
    import_data('demo')


def seed():
    import_data('seed')


def import_data(which):
    print('Importing {} data...'.format(which))
    is_demo = which == 'demo'

    if is_demo:
        utils.setup_demo_sample_models('demo-site-1', calc_savings=True)


def print_help():
    print("Usage: python manage.py runscript setup_sample_meter --script-args [all|seed|demo] [clean]")
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
