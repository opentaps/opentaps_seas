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
from . import utils
from ..core.models import Meter
from .models import BaselineModel
from django import forms

logger = logging.getLogger(__name__)


class MeterInput(forms.TextInput):
    template_name = 'eemeter/forms/meterinput.html'


class MeterField(forms.CharField):
    widget = MeterInput


class MeterModelCreateForm(forms.ModelForm):
    meter_id = MeterField(label='Meter', max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super(MeterModelCreateForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            logger.error('MeterModelCreateForm: super not valid')
            return False
        logger.info('MeterModelCreateForm: check is_valid')

        meter_id = self.cleaned_data['meter_id']
        if meter_id:
            # check meter exists
            try:
                Meter.objects.get(meter_id=meter_id)
            except Meter.DoesNotExist:
                logger.error('MeterModelCreateForm: Meter not found with id = %s', meter_id)
                self.add_error('meter_id', 'Meter {} does not exist.'.format(meter_id))
                return False
        return True

    def save(self, commit=True):
        meter_id = self.cleaned_data['meter_id']
        frequency = self.cleaned_data['frequency']
        logger.info('MeterModelCreateForm: for Meter %s', meter_id)

        meter = Meter.objects.get(meter_id=meter_id)

        data = utils.read_meter_data(meter, freq=frequency)
        model = utils.get_model_for_freq(data, frequency)

        if commit:
            bm = utils.save_model(model)
            bm.meter_id = meter.meter_id
            bm.save()
            self.instance = bm
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = BaselineModel
        fields = ["meter_id", "frequency"]
