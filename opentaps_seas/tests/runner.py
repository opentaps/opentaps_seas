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
from django.test.utils import get_unique_databases_and_mirrors
from django_nose import NoseTestSuiteRunner


class SkipCrateDatabaseMixin(object):

    def setup_databases(self, **kwargs):
        """Create the test databases. Except those with BYPASS_CREATION."""
        return self._setup_databases(
            self.verbosity, self.interactive, self.keepdb, self.debug_sql,
            self.parallel, **kwargs
        )

    def _setup_databases(self, verbosity, interactive, keepdb=False, debug_sql=False, parallel=0, **kwargs):
        """Create the test databases. Except those with BYPASS_CREATION."""
        print('MyTestRunner: setup_databases ...')
        test_databases, mirrored_aliases = get_unique_databases_and_mirrors()

        old_names = []

        for signature, (db_name, aliases) in test_databases.items():
            first_alias = None
            for alias in aliases:
                connection = connections[alias]
                if connection.settings_dict.get('BYPASS_CREATION', 'no') == 'no':
                    print('MyTestRunner: call create DB ...', alias)
                    old_names.append((connection, db_name, first_alias is None))

                    # Actually create the database for the first connection
                    if first_alias is None:
                        first_alias = alias
                        connection.creation.create_test_db(
                            verbosity=verbosity,
                            autoclobber=not interactive,
                            keepdb=keepdb,
                            serialize=connection.settings_dict.get('TEST', {}).get('SERIALIZE', True),
                        )
                        if parallel > 1:
                            for index in range(parallel):
                                connection.creation.clone_test_db(
                                    suffix=str(index + 1),
                                    verbosity=verbosity,
                                    keepdb=keepdb,
                                )
                    # Configure all other connections as mirrors of the first one
                    else:
                        connections[alias].creation.set_as_test_mirror(connections[first_alias].settings_dict)
                else:
                    print('MyTestRunner: skipped create DB for', alias)

        # Configure the test mirrors.
        for alias, mirror_alias in mirrored_aliases.items():
            connections[alias].creation.set_as_test_mirror(
                connections[mirror_alias].settings_dict)

        if debug_sql:
            for alias in connections:
                connections[alias].force_debug_cursor = True

        return old_names

    def _teardown_databases(self, old_config, verbosity, parallel=0, keepdb=False):
        """Destroy all the non-mirror databases. Except those with BYPASS_CREATION."""
        for connection, old_name, destroy in old_config:
            if destroy:
                print('MyTestRunner: _teardown_databases: ', old_name)
                if parallel > 1:
                    for index in range(parallel):
                        connection.creation.destroy_test_db(
                            suffix=str(index + 1),
                            verbosity=verbosity,
                            keepdb=keepdb,
                        )
                connection.creation.destroy_test_db(old_name, verbosity, keepdb)

    def teardown_databases(self, old_config, **kwargs):
        """Destroy all the non-mirror databases. Except those with BYPASS_CREATION."""
        self._teardown_databases(
            old_config,
            verbosity=self.verbosity,
            parallel=self.parallel,
            keepdb=self.keepdb,
        )


class MyTestRunner(SkipCrateDatabaseMixin, NoseTestSuiteRunner):
    """Actual test runner sub-class to make use of the mixin."""
