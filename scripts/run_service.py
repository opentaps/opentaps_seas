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
import pprint

from opentaps_seas.core.services import run_service

pp = pprint.PrettyPrinter(indent=2, width=250)


def print_help():
    print("Usage: python manage.py runscript run_service --script-args service_name [parameters_json]]")


def run(*args):
    if len(args) > 0:
        service_name = args[0]
        parameters = None
        if len(args) > 1:
            parameters_json = args[1]
            parameters = json.loads(parameters_json)

        print('Running Service {} with parameters:'.format(service_name))
        pp.pprint(parameters)
        result = run_service(service_name, parameters)
        print('Service Results:')
        pp.pprint(result)
    else:
        print_help()
