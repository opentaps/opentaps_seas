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
from datetime import timedelta
from . import utils
from ..core.models import Meter
from ..core.models import MeterProduction
from .models import BaselineModel
from django import forms
from django.forms.widgets import HiddenInput

logger = logging.getLogger(__name__)


class MeterInput(forms.TextInput):
    template_name = 'eemeter/forms/meterinput.html'


class MeterField(forms.CharField):
    widget = MeterInput


class MeterModelCreateForm(forms.ModelForm):
    meter_id = MeterField(label='Meter', max_length=255, required=False)
    blackout_start_date = forms.DateTimeField(label='Blackout Start Date', required=False)
    blackout_end_date = forms.DateTimeField(label='Blackout End Date', required=False)

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
        bsd = self.cleaned_data['blackout_start_date']
        bed = self.cleaned_data['blackout_end_date']
        logger.info('MeterModelCreateForm: for Meter %s', meter_id)

        meter = Meter.objects.get(meter_id=meter_id)

        data = utils.read_meter_data(meter, freq=frequency, blackout_start_date=bsd, blackout_end_date=bed)
        model = utils.get_model_for_freq(data, frequency)

        if commit:
            bm = utils.save_model(model, meter_id=meter.meter_id, frequency=frequency)
            self.instance = bm
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = BaselineModel
        fields = ["meter_id", "frequency"]


class CalcMeterSavingsForm(forms.Form):
    meter_id = MeterField(label='Meter', max_length=255, required=True)
    model_id = forms.CharField(label='Model', max_length=255, required=True)
    from_datetime = forms.DateTimeField(label='From', required=True)
    to_datetime = forms.DateTimeField(label='To', required=True)
    blackout_start_date = forms.DateTimeField(label='Blackout Start Date', required=False)
    blackout_end_date = forms.DateTimeField(label='Blackout End Date', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get('meter_id'):
            self.fields['meter_id'].widget = HiddenInput()
        if self.initial.get('model_id'):
            self.fields['model_id'].widget = HiddenInput()

    def is_valid(self):
        if not super().is_valid():
            logger.error('CalcMeterSavingsForm: super not valid')
            return False
        logger.info('CalcMeterSavingsForm: check is_valid')

        meter_id = self.cleaned_data['meter_id']
        meter = None
        if meter_id:
            # check meter exists
            try:
                meter = Meter.objects.get(meter_id=meter_id)
            except Meter.DoesNotExist:
                logger.error('CalcMeterSavingsForm: Meter not found with id = %s', meter_id)
                self.add_error('meter_id', 'Meter {} does not exist.'.format(meter_id))
                return False

        model_id = self.cleaned_data['model_id']
        if model_id:
            # check meter exists
            try:
                BaselineModel.objects.get(id=model_id)
            except BaselineModel.DoesNotExist:
                logger.error('CalcMeterSavingsForm: BaselineModel not found with id = %s', model_id)
                self.add_error('model_id', 'BaselineModel {} does not exist.'.format(model_id))
                return False

        if meter:
            start = self.cleaned_data['from_datetime']
            end = self.cleaned_data['to_datetime']
            # check there is actually data for the range
            if not meter.get_meter_data(start=start, end=end).count():
                logger.error('CalcMeterSavingsForm: No Meter data found for %s from %s to %s', model_id, start, end)
                self.add_error('from_datetime', 'No Meter data found between {} and {}'.format(start, end))
                self.add_error('to_datetime', 'No Meter data found between {} and {}'.format(start, end))
                return False

        return True

    def save(self, commit=True):
        meter_id = self.cleaned_data['meter_id']
        model_id = self.cleaned_data['model_id']
        start = self.cleaned_data['from_datetime']
        end = self.cleaned_data['to_datetime']
        bsd = self.cleaned_data['blackout_start_date']
        bed = self.cleaned_data['blackout_end_date']
        logger.info('CalcMeterSavingsForm: for Meter %s, from %s to %s', meter_id, start, end)

        meter = Meter.objects.get(meter_id=meter_id)
        model = BaselineModel.objects.get(id=model_id)

        m = utils.load_model(model)
        data = utils.read_meter_data(meter,
                                     freq=model.frequency,
                                     start=start,
                                     end=end,
                                     blackout_start_date=bsd,
                                     blackout_end_date=bed)
        savings = utils.get_savings(data, m)
        logger.info('CalcMeterSavingsForm: got saving = {}'.format(savings))
        metered_savings = savings.get('metered_savings')
        error_bands = savings.get('error_bands')
        source = "{}:{}".format(model.id, model.model_class)
        if not metered_savings.empty:
            # save the metered savings inot MeterProduction
            logger.info('CalcMeterSavingsForm: got metered_savings = {}'.format(metered_savings))
            for d, v in metered_savings.iterrows():
                logger.info('CalcMeterSavingsForm: -> {} = {}'.format(d, v.metered_savings))
                MeterProduction.objects.create(
                    meter=meter,
                    from_datetime=d,
                    thru_datetime=d + timedelta(hours=1),
                    meter_production_type='EEMeter Savings',
                    meter_production_reference={'BaselineModel.id': model.id},
                    error_bands=error_bands,
                    amount=v.metered_savings,
                    uom_id='energy_kWh',
                    source=source)
        self.model = model
        return savings
