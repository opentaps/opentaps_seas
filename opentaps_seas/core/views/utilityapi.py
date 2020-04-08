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

from .common import WithBreadcrumbsMixin
from .. import utilityapi_utils
from ..models import Meter
from ..models import SiteView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import DetailView
from rest_framework.decorators import api_view

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
