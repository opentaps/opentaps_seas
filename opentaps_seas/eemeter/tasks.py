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
from celery import shared_task
from django.urls import reverse
from ..core.models import Meter
from ..core.celery import ProgressRecorder
from . import utils

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def create_meter_model_task(self, kwargs):
    mid = kwargs.get('meter_id')
    obs = ProgressRecorder(
        self,
        name="Creating Meter Model",
        success_label='View Model',
        skip_url=reverse("core:meter_detail", kwargs={'meter_id': mid}),
        skip_label='View Meter',
        back_url=reverse("core:meter_model_create", kwargs={'meter_id': mid}))
    kwargs['progress_observer'] = obs
    bm = create_meter_model(kwargs)
    obs.extra.update({'success_url': reverse("core:meter_model_detail", kwargs={'meter_id': mid, 'id': bm.id})})
    return {
        'result': bm.id,
        'extra': obs.extra
        }


def create_meter_model(kwargs):
    logger.info('create_meter_model: %s', kwargs)
    kwargs.pop('use_async', None)
    progress_observer = kwargs.pop('progress_observer', None)
    meter = kwargs.pop('meter', None)
    meter_id = kwargs.pop('meter_id', None)
    logger.info('create_meter_model: for Meter %s', meter_id)
    frequency = kwargs.pop('frequency', None)
    thru_date = kwargs.pop('thru_date', None)
    description = kwargs.pop('description', None)
    data = kwargs.pop('read_meter_data', None)

    if progress_observer:
        progress_observer.set_progress(1, 4, description='Gathering model data ...')

    # note we already got this in the validate method
    if not meter:
        meter = Meter.objects.get(meter_id=meter_id)
    if not data:
        data = utils.read_meter_data(meter, freq=frequency, blackout_start_date=thru_date)

    if progress_observer:
        progress_observer.add_progress(description='Building model ...')

    model = utils.get_model_for_freq(data, frequency, **kwargs)

    if not description:
        description = 'CalTrack {} for Meter {} Ending {}'.format(
            frequency, meter.description or meter.meter_id, data['end'])

    try:
        bm = utils.save_model(model,
                              meter_id=meter.meter_id,
                              data=data,
                              model_params=kwargs,
                              frequency=frequency,
                              description=description,
                              progress_observer=progress_observer,
                              from_datetime=data['start'],
                              thru_datetime=data['end'])
        return bm
    except Exception as e:
        if progress_observer:
            progress_observer.set_failure(e)
        else:
            logger.exception(e)
            raise e


@shared_task(bind=True)
def calc_meter_savings_task(self, kwargs):
    meter_id = kwargs.get('meter_id')
    model_id = kwargs.get('model_id')
    start = kwargs.get('from_datetime')
    end = kwargs.get('to_datetime')
    obs = ProgressRecorder(
        self,
        name="Calculate Meter Production",
        success_label='View Model',
        skip_url=reverse("core:meter_detail", kwargs={'meter_id': meter_id}),
        skip_label='View Meter',
        back_url=reverse("core:meter_model_detail", kwargs={'meter_id': meter_id, 'id': model_id})
        )
    kwargs['progress_observer'] = obs
    model, savings = utils.calc_meter_savings(meter_id, model_id, start, end, progress_observer=obs)

    obs.extra.update({'success_url': reverse("core:meter_model_detail", kwargs={'meter_id': meter_id, 'id': model_id})})
    return {
        'result': model_id,
        'extra': obs.extra
        }
