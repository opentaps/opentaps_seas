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

# script first argument should be one of ahu|entity|geo|tag|tagrule|timezone or all_data
# other arguments are what python script expected, i.e.
# [all|seed|demo] [clean] [run_rules] [ahu_no_point]

ARGS=$*

if [ "$1" == "all_data" ]; then
    echo "Import all data"
    python manage.py runscript import_tags --script-args $ARGS
    python manage.py runscript import_entities --script-args $ARGS
    python manage.py runscript import_data --script-args $ARGS
    python manage.py runscript import_timezones --script-args $ARGS
    python manage.py runscript import_geos --script-args $ARGS
    python manage.py runscript import_tagrules --script-args $ARGS
    python manage.py runscript import_weathers --script-args $ARGS
else
    if [ "$1" == "ahu" ]; then
        python manage.py runscript import_data --script-args $ARGS
    fi
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
    if [ "$1" == "weather" ]; then
        python manage.py runscript import_weathers --script-args $ARGS
    fi
fi

