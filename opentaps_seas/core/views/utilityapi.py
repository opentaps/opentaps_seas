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
from datetime import timezone

from .common import WithBreadcrumbsMixin
from .. import utilityapi_utils
from ..models import Meter
from ..models import MeterHistory
from ..models import SiteView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import DetailView
from rest_framework.decorators import api_view
from greenbutton import resources
from greenbutton import enums


logger = logging.getLogger(__name__)


@login_required()
@api_view(['GET'])
def meters(request):
    if request.method == 'GET':
        customer_email = request.GET.get('customer_email')
        if customer_email:
            # get active authorizations for given customer_email
            customer_meters = []
            customer_authorizations = []
            authorizations = utilityapi_utils.get_authorizations()

            if authorizations:
                for auth in authorizations:
                    if auth['customer_email'] == customer_email:
                        if (not auth['is_declined'] and not auth['is_expired'] and
                                not auth['is_archived'] and not auth['is_revoked']):
                            customer_authorizations.append(auth)

            if customer_authorizations:
                auth_uids = ''
                for auth in customer_authorizations:
                    if len(auth_uids) > 0:
                        auth_uids += ','
                    auth_uids += auth['uid']
                customer_meters = utilityapi_utils.get_meters(auth_uids)

                meters = []
                if customer_meters:
                    for customer_meter in customer_meters:
                        meter = {'uid': customer_meter['uid']}
                        description = 'UID ' + customer_meter['uid']

                        if 'base' in customer_meter.keys():
                            base = customer_meter['base']
                            if 'service_address' in base.keys():
                                description += ' : ' + base['service_address']
                            elif 'billing_address' in base.keys():
                                description += ' : ' + base['billing_address']

                        meter['description'] = description
                        meters.append(meter)
                return JsonResponse({'meters': meters})

            else:
                return JsonResponse({'error': 'Cannot get UtilityAPI authorizations', 'error_code': 1})

        else:
            return JsonResponse({'error': 'Customer Email is required'})


@login_required()
@api_view(['POST'])
def meter_data_import(request, meter_id):
    if request.method == 'POST':
        data = request.data
        meter_uid = data.get('meter_uid')

        u_meter = utilityapi_utils.get_meter(meter_uid)

        if u_meter:
            authorization_uid = u_meter.get('authorization_uid')

            # 1. UsagePoint
            usage_point = utilityapi_utils.get_usage_point(authorization_uid, meter_uid)

            local_time_url = None
            for child in usage_point:
                if 'link' in child.tag and child.attrib['rel'] == 'related':
                    if 'LocalTimeParameters' in child.attrib['href']:
                        local_time_url = child.attrib['href']

            # 2. LocalTimeParameters
            tzOffset = 0
            if local_time_url:
                ltptree = utilityapi_utils.espi_get_by_url(local_time_url)
                if ltptree:
                    ltp = resources.LocalTimeParameters(ltptree, usagePoints=[])
                    if ltp:
                        tzOffset = ltp.tzOffset

            # 3. MeterReading
            meter_reading = utilityapi_utils.get_meter_reading(authorization_uid, meter_uid)

            reading_type_url = None
            interval_block_url = None
            if meter_reading:
                meter_reading_entry = meter_reading.find('atom:entry', resources.ns)
                if meter_reading_entry:
                    for child in meter_reading_entry:
                        if 'link' in child.tag and child.attrib['rel'] == 'related':
                            if 'ReadingType' in child.attrib['href']:
                                reading_type_url = child.attrib['href']
                            elif 'IntervalBlock' in child.attrib['href']:
                                interval_block_url = child.attrib['href']

            if not reading_type_url:
                return JsonResponse({'error': 'Cannot get meter reading type url'})
            if not interval_block_url:
                return JsonResponse({'error': 'Cannot get meter interval block url'})

            # 3.1. ReadingType
            reading_type = None
            rttree = utilityapi_utils.espi_get_by_url(reading_type_url)
            if rttree:
                reading_type = resources.ReadingType(rttree, meterReadings=[])

            if not reading_type:
                return JsonResponse({'error': 'Cannot get meter reading type'})

            reading_type_uom = enums.UOM_IDS[reading_type.uom]
            if not reading_type_uom:
                return JsonResponse({'error': 'Cannot get meter reading type uom'})

            # 3.2. IntervalBlock
            interval_blocks = []
            ibtree = utilityapi_utils.espi_get_by_url(interval_block_url)
            if ibtree:
                for entry in ibtree.findall('atom:entry/atom:content/espi:IntervalBlock/../..', resources.ns):
                    ib = resources.IntervalBlock(entry, meterReadings=[])
                    interval_blocks.append(ib)

            for interval_block in interval_blocks:
                for ir in interval_block.intervalReadings:
                    v = MeterHistory(meter_id=meter_id, uom_id=reading_type_uom)
                    v.source = 'utilityapi'
                    v.value = ir.value
                    v.duration = int(ir.timePeriod.duration.total_seconds())
                    v.as_of_datetime = ir.timePeriod.start
                    v.created_by_user = request.user

                    if tzOffset:
                        tz = timezone(timedelta(seconds=tzOffset))
                        v.as_of_datetime = v.as_of_datetime.replace(tzinfo=tz)

                    v.save()
            try:
                meter = Meter.objects.get(meter_id=meter_id)
            except Meter.DoesNotExist:
                logger.warning('Cannot get Meter {}'.format(meter_id))
            else:
                attributes = meter.attributes
                if not attributes:
                    attributes = {}

                attributes['utilityapi_meter_uid'] = meter_uid

                meter.attributes = attributes
                meter.save()

        else:
            return JsonResponse({'error': 'Cannot get UtilityAPI meter data'})

        response = JsonResponse({'success': 1})

        return response


class DataImport(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/utilityapi_data_import.html'

    def get_context_data(self, **kwargs):
        context = super(DataImport, self).get_context_data(**kwargs)
        context["meter_id"] = self.kwargs['meter_id']

        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        meter = None
        if self.kwargs['meter_id']:
            try:
                meter = Meter.objects.get(meter_id=self.kwargs['meter_id'])
            except Meter.DoesNotExist:
                pass
            else:
                try:
                    site = SiteView.objects.get(entity_id=meter.site_id)
                except SiteView.DoesNotExist:
                    pass
                else:
                    label = 'Site'
                    if site.description:
                        label = site.description
                    url = reverse("core:site_detail", kwargs={'site': meter.site_id})
                    b.append({'url': url, 'label': label})

        if meter:
            url = reverse("core:meter_detail", kwargs={'meter_id': meter.meter_id})
            label = 'Meter ' + meter.meter_id
            if meter.description:
                label = 'Meter ' + meter.description
            b.append({'url': url, 'label': label})

        b.append({'label': 'UtilityAPI Meter Data Import'})
        return b


data_import_view = DataImport.as_view()
