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
from opentaps_seas.core.models import WeatherStation
from opentaps_seas.core.utils import get_weather_history_for_station

def clean():
    print('Deleting data ...')
    with connections['default'].cursor() as c:
        sql = """DELETE FROM core_weather_station;"""
        c.execute(sql)
        c.close()


def demo():
    return


def seed():
    import_data('seed')


def import_data(which):
    print('Importing {} data...'.format(which))
    is_demo = which == 'demo'

    for weather_station in WeatherStation.objects.all():
        print('Importing data for {}'.format(weather_station.station_name))
        get_weather_history_for_station(weather_station)

def print_help():
    print("Usage: python manage.py runscript import_weather_histories --script-args [all|seed|demo] [clean]")
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
