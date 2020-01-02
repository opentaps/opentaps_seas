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
from enum import Enum
from opentaps_seas.core.models import Meter
from django.db import models
from django.db.models import AutoField
from django.db.models import CharField
from django.db.models import ForeignKey
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

logger = logging.getLogger(__name__)


METER_MODEL_CHOICES = [
    ('hourly', 'Hourly'),
    ('daily', 'Daily')
]


class BaselineModel(models.Model):
    class FREQUENCY(Enum):
        hourly = ('hourly', 'Hourly')
        daily = ('daily', 'Daily')

        @classmethod
        def get_value(cls, member):
            return cls[member].value[0]

    id = AutoField(_("Baseline Model ID"), primary_key=True, auto_created=True)
    meter = ForeignKey(Meter, null=True, blank=True, on_delete=models.SET_NULL)
    model_class = CharField(_("Model Class"), blank=False, null=False, max_length=512)
    frequency = CharField(_("Frequency"), blank=False, null=False, max_length=255, choices=[x.value for x in FREQUENCY])
    data = JSONField(blank=True, null=True)

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse("core:meter_model_detail", kwargs={"meter_id": self.meter_id, "id": self.id})
