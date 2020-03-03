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
import requests
import tempfile
import time
import solaredge
from celery import shared_task
from django.core.files import File
from django.urls import reverse
from easy_thumbnails.files import get_thumbnailer
from filer.models import Image as FilerFile
from ..core.models import Meter
from ..core.models import SolarEdgeSetting
from ..core.celery import ProgressRecorder
from . import utils

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def test_task(self, kwargs):
    steps = kwargs.get('steps', 100)
    duration = kwargs.get('duration', 1)
    obs = ProgressRecorder(
        self,
        name="A test task")

    obs.set_progress(0, steps, description='Sleeping for the test task ...')
    for i in range(0, steps):
        time.sleep(duration)
        obs.add_progress()

    return {
        'result': 'Done',
        'extra': obs.extra
        }


@shared_task(bind=True)
def fetch_solaredge_for_equipment_task(self, kwargs):
    entity_id = kwargs.get('entity_id')
    site_id = kwargs.get('site_id')
    obs = ProgressRecorder(
        self,
        name="Fetching SolarEdge data",
        success_label='View Equipment',
        skip_url=reverse("core:equipment_detail", kwargs={'equip': entity_id}),
        skip_label='View Equipment',
        back_url=reverse("core:equipment_create", kwargs={'site': site_id}))
    kwargs['progress_observer'] = obs
    ses = fetch_solaredge_for_equipment(kwargs)

    obs.extra.update({'success_url': reverse("core:equipment_detail", kwargs={'equip': entity_id})})
    return {
        'result': ses.entity_id,
        'extra': obs.extra
        }


def fetch_solaredge_for_equipment(kwargs):
    progress_observer = kwargs.pop('progress_observer', None)
    entity_id = kwargs.get('entity_id')
    user = kwargs.get('user')
    description = kwargs.get('description')

    if progress_observer:
        progress_observer.set_progress(1, 5, description='Connecting to SolarEdge ...')

    se = solaredge.Solaredge(kwargs['solaredge_api_key'])
    se_details = se.get_details(kwargs['solaredge_site_id']).get('details')
    if not description:
        description = se_details.get('name')
    # extract some fields we will need to display later
    se_uris = se_details.get('uris')
    if se_uris:
        se_img = se_uris.get('SITE_IMAGE')
        if se_img:
            # avoid cryptic errors on misconfiguration
            utils.check_boto_config()
            # note the image will require the api_key parameter
            img_url = 'https://monitoringapi.solaredge.com' + se_img
            url = img_url + '?api_key=' + kwargs['solaredge_api_key']
            try:
                logger.info('Downloading image %s', url)
                if progress_observer:
                    progress_observer.set_progress(2, 5, description='Downloading data from SolarEdge ...')
                r = requests.get(url)
                with tempfile.TemporaryFile() as temp, tempfile.TemporaryFile() as temp2:
                    progress_observer.set_progress(3, 5, description='Processing data from SolarEdge ...')
                    ses = SolarEdgeSetting.objects.get(entity_id=entity_id)
                    meter = Meter.objects.get(meter_id=entity_id)
                    file_name = se_img.split('/')[-1]
                    logger.info('Saving image %s', file_name)
                    n = temp.write(r.content)
                    logger.info('Saved temp %s', n)
                    n = temp2.write(r.content)
                    logger.info('Saving temp2 %s', n)
                    file_obj = File(temp, name=file_name)
                    site_image = FilerFile.objects.create(owner=user,
                                                          original_filename=file_name,
                                                          file=file_obj)
                    # note: auto thumbnail would take twice as long to generate so do it here
                    progress_observer.set_progress(4, 5, description='Generating thumbnail from SolarEdge ...')
                    th = get_thumbnailer(temp2, relative_name=file_name)
                    th_img = th.get_thumbnail({'size': (250, 250), 'crop': True})
                    file_obj2 = File(th_img, name=file_name)
                    site_thumbnail = FilerFile.objects.create(owner=user,
                                                              original_filename=file_name,
                                                              file=file_obj2)

                    ses.site_details = se_details
                    ses.site_image = site_image
                    ses.site_thumbnail = site_thumbnail
                    ses.save()

                    meter.description = 'SolarEdge: {}'.format(se_details.get('name'))
                    meter.save()
                    progress_observer.set_progress(5, 5, description='Done.')

            except Exception as e:
                logger.exception(e)
                raise e
    return ses
