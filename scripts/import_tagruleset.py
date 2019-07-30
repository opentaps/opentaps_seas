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
from django.core.files.uploadedfile import SimpleUploadedFile
from opentaps_seas.core.forms import TopicTagRuleSetImportForm


def import_tagruleset(file_name, run_rule=False):
    (abs_dir_path, filename) = os.path.split(file_name)

    with open(file_name, 'rb') as infile:
        f = SimpleUploadedFile(filename, infile.read())
        form = TopicTagRuleSetImportForm({}, {'json_file': f})
        if form.is_valid():
            form_results = form.save(run_rule=run_rule)

            # an error message
            import_errors = form_results.get('import_errors')
            # the imported rule sets
            success_rule_sets = form_results.get('success_rule_sets')
            # if the rulesets are run, count how many topics were affected
            runner_count = form_results.get('runner_count')

            if import_errors:
                print("ERROR: " + import_errors)
            elif success_rule_sets:
                print('Successfully imported {} rule sets.'.format(", ".join(success_rule_sets)))
                if run_rule:
                    print('Successfully Ran rules on {} topics.'.format(runner_count))
            else:
                print("ERROR: Rule sets list to import is empty.")
        else:
            print("ERROR: Data provided invalid")
            if form.errors:
                print(" {}".format(form.errors.as_data()))


def print_help():
    print("Usage: python manage.py runscript import_tagruleset --script-args json_file [run]")
    print(" json_file: path to the JSON file to import")
    print(" [run]: optional flag to indicate the imported rules should also be run")


def run(*args):
    if len(args) > 0:
        run_rule = False
        if len(args) > 1 and args[1] == 'run':
            run_rule = True
        import_tagruleset(args[0], run_rule)
    else:
        print_help()
