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
    meter = kwargs.get('meter')
    meter_id = kwargs.get('meter_id')
    frequency = kwargs.get('frequency')
    thru_date = kwargs.get('thru_date')
    description = kwargs.get('description')
    data = kwargs.get('read_meter_data')
    progress_observer = kwargs.get('progress_observer')

    logger.info('create_meter_model: %s', kwargs)
    logger.info('create_meter_model: for Meter %s', meter_id)

    if progress_observer:
        progress_observer.set_progress(1, 4, description='Gathering model data ...')

    # note we already got this in the validate method
    if not meter:
        meter = Meter.objects.get(meter_id=meter_id)
    if not data:
        data = utils.read_meter_data(meter, freq=frequency, blackout_start_date=thru_date)

    if progress_observer:
        progress_observer.add_progress(description='Building model ...')

    model = utils.get_model_for_freq(data, frequency)

    if not description:
        description = 'CalTrack {} for Meter {} Ending {}'.format(
            frequency, meter.description or meter.meter_id, data['end'])

    bm = utils.save_model(model,
                          meter_id=meter.meter_id,
                          data=data,
                          frequency=frequency,
                          description=description,
                          progress_observer=progress_observer,
                          from_datetime=data['start'],
                          thru_datetime=data['end'])
    return bm
