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
from datetime import timedelta
from opentaps_seas.core.models import Meter
from opentaps_seas.core.models import MeterProduction
from opentaps_seas.core.models import MeterFinancialValue
from django.db import models
from django.db.models import Q
from django.db.models import AutoField
from django.db.models import CharField
from django.db.models import TextField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import now
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
    description = CharField(_("Description"), blank=True, null=True, max_length=255)
    from_datetime = DateTimeField(_("From Date"), blank=True, null=True)
    thru_datetime = DateTimeField(_("Thru Date"), default=now)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    last_calc_saving_datetime = DateTimeField(_("Last Calculated Savings Date"), blank=True, null=True)
    plot_data = TextField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse("core:meter_model_detail", kwargs={"meter_id": self.meter_id, "id": self.id})

    def get_frequency_delta(self):
        if self.frequency == 'daily':
            return timedelta(hours=24)
        else:
            return timedelta(hours=1)

    def get_production(self):
        q = MeterProduction.objects
        q = q.filter(Q(**{'meter_production_reference__{}'.format('BaselineModel.id'): '{}'.format(self.id)}))
        return q.order_by('from_datetime')

    def get_financial_value(self):
        q = MeterFinancialValue.objects
        q = q.filter(Q(**{'meter_production_reference__{}'.format('BaselineModel.id'): '{}'.format(self.id)}))
        return q.order_by('from_datetime')
