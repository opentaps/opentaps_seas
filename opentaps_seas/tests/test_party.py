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

from .base import OpentapsSeasTestCase
from django.db import connections
from opentaps_seas.party.models import Party


class PartyTests(OpentapsSeasTestCase):

    def setUp(self):
        with connections['default'].cursor() as c:
            sql = """INSERT INTO {0} (party_id, party_external_id, source)
                VALUES (%s, %s, %s)""".format("party_party")
            c.execute(sql, [10000, 'test01', 'dummy'])
            c.execute(sql, [10001, 'test02', 'dummy'])

    def tearDown(self):
        self._cleanup_data()

    @staticmethod
    def _cleanup_data():
        # delete test data for CrateDB
        with connections['default'].cursor() as c:
            sql = """DELETE FROM {0} WHERE party_external_id like %s""".format("party_party")
            c.execute(sql, ['test%'])

    def test_dummy_party(self):
        party = Party.objects.get(party_id=10000)

        self.assertEqual(party.get_name(), 'FirstName LastName test01')
        self.assertEqual(party.get_email(), 'email_test01@example.org')
        self.assertEqual(party.get_address(), 'test01 Somewhere St')
        self.assertEqual(party.get_phone_number(), '310-11111111')

        party = Party.objects.get(party_id=10001)
        self.assertEqual(party.get_name(), 'FirstName LastName test02')
        self.assertEqual(party.get_email(), 'email_test02@example.org')
        self.assertEqual(party.get_address(), 'test02 Somewhere St')
        self.assertEqual(party.get_phone_number(), '310-11111111')
