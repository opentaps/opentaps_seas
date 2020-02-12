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
    parties = {
        'dummy01': {'name': 'FirstName LastName 1',
                    'address': '1 Somewhere St',
                    'email': 'email_dummy01@example.org',
                    'phone_number': '310-11111111'
                    },
        'dummy02': {'name': 'FirstName LastName 2',
                    'address': '2 Somewhere St',
                    'email': 'email_dummy02@example.org',
                    'phone_number': '310-22222222'
                    },
    }

    def get_name(self):
        party = self.parties.get(self.party_external_id)
        if party:
            return party.get('name')
        return super().get_name()

    def get_address(self):
        party = self.parties.get(self.party_external_id)
        if party:
            return party.get('address')
        return super().get_address()

    def get_email(self):
        party = self.parties.get(self.party_external_id)
        if party:
            return party.get('email')
        return super().get_email()

    def get_phone_number(self):
        party = self.parties.get(self.party_external_id)
        if party:
            return party.get('phone_number')
        return super().get_phone_number()