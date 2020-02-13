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

import logging
from .party import DummyParty
from .party import BaseParty
from django.db import models
from django.db.models import AutoField
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class Party(models.Model):
    party_id = AutoField(_("Party ID"), primary_key=True, auto_created=True)
    party_external_id = CharField(max_length=255, blank=True, null=True)
    source = CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "{} ({})".format(self.get_name() or str(self.party_id), self.party_external_id)

    def get_external_party(self):
        ext_party = None
        if self.source == 'dummy':
            ext_party = DummyParty(self.party_external_id)
        else:
            ext_party = BaseParty(self.party_external_id)

        return ext_party

    def get_name(self):
        ext_party = self.get_external_party()
        if ext_party:
            return ext_party.get_name()
        else:
            return None

    def get_address(self):
        ext_party = self.get_external_party()
        if ext_party:
            return ext_party.get_address()
        else:
            return None

    def get_email(self):
        ext_party = self.get_external_party()
        if ext_party:
            return ext_party.get_email()
        else:
            return None

    def get_phone_number(self):
        ext_party = self.get_external_party()
        if ext_party:
            return ext_party.get_phone_number()
        else:
            return None
