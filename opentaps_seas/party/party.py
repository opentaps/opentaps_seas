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


class BaseParty:
    def __init__(self, party_external_id):
        self.party_external_id = party_external_id

    def get_name(self):
        pass

    def get_address(self):
        pass

    def get_email(self):
        pass

    def get_phone_number(self):
        pass


class DummyParty(BaseParty):
    def get_name(self):
        return "FirstName LastName " + self.party_external_id

    def get_address(self):
        return self.party_external_id + " Somewhere St"

    def get_email(self):
        return "email_" + self.party_external_id + "@example.org"

    def get_phone_number(self):
        return "310-11111111"
