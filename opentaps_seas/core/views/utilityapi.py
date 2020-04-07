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

                return JsonResponse({'customer_meters': customer_meters})
            else:
                return JsonResponse({'error': 'Cannot get authorizations'})
        else:
            return JsonResponse({'error': 'Customer Email is required'})


class MeterDataImport(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/utilityapi_meter_data_import.html'

    def get_context_data(self, **kwargs):
        context = super(MeterDataImport, self).get_context_data(**kwargs)

        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        return b


meter_data_import = MeterDataImport.as_view()
