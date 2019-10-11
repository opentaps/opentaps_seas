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
from django.core.management import execute_from_command_line
from django.db import connections


def clean():
    print('Deleting data ...')
    with connections['default'].cursor() as c:
        c.execute('DELETE FROM core_topictagrule;')
        c.execute('DELETE FROM core_topictagruleset;')
        c.close()


def demo(run_rules):
    import_files('demo', run_rules)


def seed(run_rules):
    import_files('seed', run_rules)


def import_files(which, run_rules):
    print('Importing {} data...'.format(which))
    dirname = os.path.dirname(os.path.realpath(__file__))
    dirname = dirname.replace('scripts', 'data/tagrule')
    mypath = os.path.join(dirname, which)
    print(mypath)
    if os.path.isdir(mypath):
        for f in os.listdir(mypath):
            filename = os.path.join(mypath, f)
            if os.path.isfile(filename):
                print('Importing {} data [{}]'.format(which, filename))
                import_entities(filename, run_rules)
    else:
        print('No {} data to import.'.format(which))


def import_entities(source_file_name, run_rules):
    # note: we import the rules using the Django service
    script = 'manage.py runscript import_tagruleset --script-args {}'.format(source_file_name)
    if run_rules:
        script += ' run'
    execute_from_command_line(script.split())


def print_help():
    print("Usage: python manage.py runscript import_tagrules --script-args [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")


def run(*args):
    if len(args) > 0:
        # setup for the django environment
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
        # important: add the root dir where manage.py is, and our main app dir
        current_path = os.path.split(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])[0]
        sys.path.append(os.path.join(current_path, "opentaps_seas"))
        sys.path.append(current_path)
        run_rules = False
        if 'run_rules' in args:
            run_rules = True
        if 'clean' in args:
            clean()
        if 'all' in args or 'clean' in args or 'seed' in args:
            seed(run_rules)
        if 'all' in args or 'demo' in args:
            demo(run_rules)
    else:
        print_help()
