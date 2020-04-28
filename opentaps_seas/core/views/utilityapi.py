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
from datetime import datetime

from .common import WithBreadcrumbsMixin
from .. import utilityapi_utils
from .. import utils
from ..models import Meter
from ..models import MeterHistory
from ..models import Entity

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
                msg = '''No UtilityAPI authorization found for this email address.
                          Please try another email or create an authorization form.'''
                return JsonResponse({'error_code': 1, 'error': msg})

        else:
            return JsonResponse({'error': 'Customer Email is required'})


@login_required()
@api_view(['POST'])
def meter_data_import(request, meter_id):
    if request.method == 'POST':
        count = 0
        count_existing = 0
        from_datetime = None
        thru_datetime = None
        data = request.data
        meter_uid = data.get('meter_uid')

        u_meter = utilityapi_utils.get_meter(meter_uid)

        if u_meter:
            try:
                count, count_existing, from_datetime, thru_datetime = utilityapi_utils.import_meter_readings(u_meter, meter_uid, meter_id, request.user)
            except ValueError as e:
                return JsonResponse({'error': e})
            else:
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

                success_message = ''
                if count > 0:
                    success_message = 'Sucessfully imported {} Meter Readings'.format(count)
                else:
                    success_message = 'No new Meter Readings imported'

                if from_datetime:
                    success_message += ' in period from {}'.format(from_datetime)
                if thru_datetime:
                    if not from_datetime:
                        success_message += ' in period'
                    success_message += ' to {}'.format(thru_datetime)

                if count_existing > 0:
                    tmp = 'Readings'
                    if count_existing == 1:
                        tmp = 'Reading'
                    success_message += ', {} Meter {} already exists'.format(count_existing, tmp)

                response = JsonResponse({'success': 1, 'message': success_message})

                return response
        else:
            return JsonResponse({'error': 'Cannot get UtilityAPI meter data'})


@login_required()
@api_view(['POST'])
def meter_bills_import(request, meter_id):
    if request.method == 'POST':
        try:
            meter = Meter.objects.get(meter_id=meter_id)
        except Meter.DoesNotExist:
            return JsonResponse({'error': 'Meter not found : {}'.format(meter_id)}, status=404)

        meter_uid = meter.attributes.get('utilityapi_meter_uid')
        if not meter_uid:
            return JsonResponse({'error': 'Meter {} does not have a utilityapi_meter_uid'.format(meter_id)}, status=400)

        u_bills = utilityapi_utils.get_bills(meter_uid)

        if u_bills:
            try:
                results, count_existing, from_datetime, thru_datetime = utilityapi_utils.import_meter_bills(u_bills, meter_uid, meter_id, request.user)
            except ValueError as e:
                return JsonResponse({'error': e})
            else:
                success_message = ''
                count = len(results)
                if count > 0:
                    success_message = 'Sucessfully imported {} Meter Bill Entries'.format(count)
                else:
                    success_message = 'No new Meter Bill Entries imported'

                if from_datetime:
                    success_message += ' in period from {}'.format(from_datetime)
                if thru_datetime:
                    if not from_datetime:
                        success_message += ' in period'
                    success_message += ' to {}'.format(thru_datetime)

                if count_existing > 0:
                    tmp = 'Bill Entries'
                    if count_existing == 1:
                        tmp = 'Bill Entriy'
                    success_message += ', {} Meter {} already exists'.format(count_existing, tmp)

                response = JsonResponse({'success': 1, 'message': success_message})

                return response
        else:
            return JsonResponse({'error': 'Cannot get UtilityAPI meter bills data'})


@login_required()
@api_view(['POST'])
def meters_data_import(request, site_id):
    if request.method == 'POST':
        data = request.data
        meter_uids = data.get('meter_uids')
        weather_station_id = data.get('weather_station_id')

        new_meter_uids = []
        for meter_uid in meter_uids:
            # check if meter with utilityapi uids already exists
            meter = Meter.objects.filter(site_id=site_id, attributes__utilityapi_meter_uid=meter_uid)
            if not meter:
                new_meter_uids.append(meter_uid)

        if not new_meter_uids:
            return JsonResponse({'error': 'All UtilityAPI meters already imported'})

        count_total = 0
        count_meters = 0
        for meter_uid in new_meter_uids:
            u_meter = utilityapi_utils.get_meter(meter_uid)

            if u_meter:
                meter_id = site_id + '-uid-' + meter_uid
                meter = Meter(meter_id=meter_id, site_id=site_id)
                meter.description = 'UtilityAPI meter ' + meter_uid
                meter.from_datetime = datetime.now()
                meter.attributes = {'utilityapi_meter_uid': meter_uid}
                if weather_station_id:
                    meter.weather_station_id = weather_station_id

                meter.save()
                try:
                    count, _, _, _ = utilityapi_utils.import_meter_readings(u_meter, meter_uid,
                                                                            meter_id, request.user)
                    count_total += count
                    count_meters += 1
                except ValueError as e:
                    logger.error(e)

        success_message = ''
        if count_meters > 0:
            tmp = 'Meters'
            if count_meters == 1:
                tmp = 'Meter'
            success_message = 'Sucessfully imported {} {}'.format(count_meters, tmp)
            if count_meters > 0:
                tmp = 'Readings'
                if count == 1:
                    tmp = 'Reading'
                success_message += ' and {} {}'.format(count, tmp)
        else:
            success_message = 'No new Meters imported'

        response = JsonResponse({'success': 1, 'message': success_message})

        return response


class DataImport(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/utilityapi_data_import.html'

    def get_context_data(self, **kwargs):
        context = super(DataImport, self).get_context_data(**kwargs)
        context["meter_id"] = self.kwargs['meter_id']
        last_timestamp = 'N/A'
        try:
            meter = Meter.objects.get(meter_id=self.kwargs['meter_id'])
        except Meter.DoesNotExist:
            pass
        else:
            if meter.attributes and 'utilityapi_meter_uid' in meter.attributes.keys():
                context["meter_uid"] = meter.attributes['utilityapi_meter_uid']
                mh = MeterHistory.objects.filter(meter_id=meter.meter_id,
                                                 source='utilityapi').order_by("-as_of_datetime").first()
                if mh:
                    last_timestamp = mh.as_of_datetime.strftime("%Y-%m-%d %H:%M:%S")

        context["last_timestamp"] = last_timestamp

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

        b.append({'label': 'Import Data from UtilityAPI Meter'})
        return b


data_import_view = DataImport.as_view()


class MetersImport(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = SiteView
    slug_field = "entity_id"
    slug_url_kwarg = "site_id"
    template_name = 'core/utilityapi_data_import.html'

    def get_context_data(self, **kwargs):
        context = super(MetersImport, self).get_context_data(**kwargs)
        context["site_id"] = self.kwargs['site_id']

        try:
            site = Entity.objects.get(entity_id=self.kwargs['site_id'])
        except SiteView.DoesNotExist:
            pass
        else:
            weather_station = utils.get_default_weather_station_for_site(site)
            if weather_station:
                context['weather_station_id'] = weather_station.weather_station_id

        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if self.kwargs['site_id']:
            try:
                site = SiteView.objects.get(entity_id=self.kwargs['site_id'])
            except SiteView.DoesNotExist:
                pass
            else:
                label = 'Site'
                if site.description:
                    label = site.description
                url = reverse("core:site_detail", kwargs={'site': self.kwargs['site_id']})
                b.append({'url': url, 'label': label})

        b.append({'label': 'Add Meter from UtilityAPI'})
        return b


meters_import_view = MetersImport.as_view()


@login_required()
@api_view(['POST'])
def create_form(request):
    if request.method == 'POST':
        data = request.data
        customer_email = data.get('customer_email')

        authorization_form = utilityapi_utils.create_form(customer_email)

        if authorization_form:
            auth_form = {}
            if not authorization_form.get('error'):
                if authorization_form.get('uid') and authorization_form.get('url'):
                    auth_form['uid'] = authorization_form.get('uid')
                    auth_form['url'] = authorization_form.get('url')

                    return JsonResponse({'success': 1, 'auth_form': auth_form})
                else:
                    return JsonResponse({'error': 'Cannot get UtilityAPI authorization form url'})
            else:
                return JsonResponse({'error': 'Cannot create UtilityAPI authorization form'})
        else:
            return JsonResponse({'error': 'Cannot create UtilityAPI authorization form'})
