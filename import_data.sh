#!/bin/bash
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

# script first argument should be one of
# entity|geo|tag|tagrule|timezone|unit_of_measure|weather_station|utility or all_data
# other arguments are what python script expected, i.e.
# [all|seed|demo] [clean] [run_rules] [ahu_no_point]
# [tsdemo] to import time series data demo from data/ahu/demo

set -e
ARGS=$*

DEMO=0
for a in "$@"
do
   if [ "$a" == "demo" ] || [ "$a" == "all" ]
   then
     DEMO=1
   fi
done
CLEAN=0
for a in "$@"
do
   if [ "$a" == "clean" ]
   then
     CLEAN=1
   fi
done

TSDEMO=0
for a in "$@"
do
   if [ "$a" == "tsdemo" ]
   then
     TSDEMO=1
   fi
done

if [ "$1" == "all_data" ]; then
    echo "Import all data"
    python manage.py runscript import_tags --script-args $ARGS
    python manage.py runscript import_statuses --script-args $ARGS
    python manage.py runscript import_unit_of_measure --script-args $ARGS
    python manage.py runscript import_weather_stations --script-args $ARGS
    python manage.py runscript import_entities --script-args $ARGS
    python manage.py runscript import_utilities --script-args $ARGS
    python manage.py runscript import_timezones --script-args $ARGS
    python manage.py runscript import_geos --script-args $ARGS
    python manage.py runscript import_tagrules --script-args $ARGS
    python manage.py runscript import_weather_histories --script-args $ARGS
    python manage.py runscript import_party --script-args $ARGS
    python manage.py runscript setup_sample_meter --script-args $ARGS
else
    if [ "$1" == "entity" ]; then
        python manage.py runscript import_entities --script-args $ARGS
    fi
    if [ "$1" == "geo" ]; then
        python manage.py runscript import_geos --script-args $ARGS
    fi
    if [ "$1" == "tag" ]; then
        python manage.py runscript import_tags --script-args $ARGS
    fi
    if [ "$1" == "tagrule" ]; then
        python manage.py runscript import_tagrules --script-args $ARGS
    fi
    if [ "$1" == "timezone" ]; then
        python manage.py runscript import_timezones --script-args $ARGS
    fi
    if [ "$1" == "status" ]; then
        python manage.py runscript import_statuses --script-args $ARGS
    fi
    if [ "$1" == "unit_of_measure" ]; then
        python manage.py runscript import_unit_of_measure --script-args $ARGS
    fi
    if [ "$1" == "weather_station" ]; then
        python manage.py runscript import_weather_stations --script-args $ARGS
    fi
    if [ "$1" == "weather_history" ]; then
        python manage.py runscript import_weather_histories --script-args $ARGS
    fi
    if [ "$1" == "utility" ]; then
        python manage.py runscript import_utilities --script-args $ARGS
    fi
    if [ "$1" == "sample_meter" ]; then
        python manage.py runscript setup_sample_meter --script-args $ARGS
    fi
    if [ "$1" == "party" ]; then
        python manage.py runscript import_party --script-args $ARGS
    fi
fi

if [ $TSDEMO -eq 1 ]
then
    python manage.py runscript import_data --script-args $ARGS
fi

# if loading demo data, also sensure we have a demo admin user
if [ $DEMO -eq 1 ]
then
    if [ $CLEAN -eq 1 ]
    then
        ./utility/create_user admin opentaps admin@example.com admin force
    else
        ./utility/create_user admin opentaps admin@example.com admin
    fi
fi
