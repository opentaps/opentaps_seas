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

from datetime import datetime
from datetime import timedelta
import logging
from math import isnan

from .common import WithBreadcrumbsMixin
from .. import utils
from ..forms.meter import MeterCreateForm
from ..forms.meter import MeterDataUploadForm
from ..forms.meter import MeterUpdateForm
from ..models import date_to_string
from ..models import datetime_to_string
from ..models import Entity
from ..models import Meter
from ..models import MeterRatePlan
from ..models import SiteView
from ..models import UnitOfMeasure
from ..models import WeatherHistory

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from opentaps_seas.eemeter.models import BaselineModel

logger = logging.getLogger(__name__)


class MeterListJsonView(LoginRequiredMixin, ListView):
    model = Meter

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        qs = qs.order_by(Lower('description'), Lower('meter_id'))
        return qs

    def render_to_response(self, context, **response_kwargs):
        data = list(context['object_list'].values('meter_id', 'description'))
        return JsonResponse({'items': data})


meter_list_json_view = MeterListJsonView.as_view()


def meter_production_data_json(request, meter):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    m = Meter.objects.get(meter_id=meter)
    if not m:
        logger.warning('No Meter found with meter_id = %s', meter)
        return JsonResponse({'error': 'Meter not found : {}'.format(meter)}, status=404)

    # Select last <trange> records
    # not do a query per "source"
    meter_data_map = {}
    qs0 = m.meterproduction_set

    model_id = request.GET.get('model_id')
    if model_id:
        logger.info('Filtering for model = %s', model_id)
        qs0 = qs0.filter(Q(**{'meter_production_reference__{}'.format('BaselineModel.id'): model_id}))

    # to simplify visualization we want to start at the latest production point
    from_datetime = None
    last_record = qs0.order_by('-from_datetime').values('from_datetime').first()
    if last_record:
        from_datetime = last_record['from_datetime']
    start, end = utils.get_start_date_from_range(request.GET.get('range'), from_datetime=from_datetime)
    if start:
        qs0 = qs0.filter(from_datetime__gte=start)
    if end:
        qs0 = qs0.filter(from_datetime__lt=end)

    # convert values to the same UOM
    uom = None

    for ref in qs0.distinct('meter_production_reference').values('meter_production_reference'):
        ref = ref.get('meter_production_reference')
        qs = qs0.filter(meter_production_reference=ref)
        logging.info('meter_production_data_json: for meter %s ref %s has %s', m, ref, qs.count())
        data_ref = None
        if ref and ref.get('BaselineModel.id'):
            try:
                bm = BaselineModel.objects.get(id=ref.get('BaselineModel.id'))
                data_ref = '{}:{}'.format(bm.id, bm.model_class)
            except BaselineModel.DoesNotExist:
                pass
        for data in qs.order_by('-from_datetime'):
            # use the first UOM found
            if not uom:
                uom = data.uom
            data_key = data_ref or data.source
            meter_data = meter_data_map.get(data_key)
            if not meter_data:
                meter_data = []
                meter_data_map[data_key] = meter_data
            # Prevent adding duplicates
            datetime = datetime_to_string(data.from_datetime)
            if meter_data and datetime == meter_data[-1]['datetime']:
                continue
            value = data.net_value
            if value and not isnan(value):
                # logging.info('meter_production_data_json: value %s', value)

                # convert to our chosen uom
                value = data.uom.convert_amount_to(value, uom)

                meter_data.append({
                    'datetime': datetime,
                    'value': value
                })

    for k in meter_data_map.keys():
        meter_data_map[k] = list(reversed(meter_data_map[k]))

    uom_d = None
    if uom:
        uom_d = {
            'id': uom.uom_id,
            'unit': uom.unit
        }

    return JsonResponse({'uom': uom_d, 'values': meter_data_map})


def meter_financial_value_data_json(request, meter):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    m = Meter.objects.get(meter_id=meter)
    if not m:
        logger.warning('No Meter found with meter_id = %s', meter)
        return JsonResponse({'error': 'Meter not found : {}'.format(meter)}, status=404)

    # Select last <trange> records
    # not do a query per "source"
    meter_data_map = {}
    qs0 = m.meterfinancialvalue_set

    # convert values to kWh
    uom = UnitOfMeasure.objects.get(uom_id='currency_USD')

    model_id = request.GET.get('model_id')
    if model_id:
        logger.info('Filtering for model = %s', model_id)
        qs0 = qs0.filter(Q(**{'meter_production_reference__{}'.format('BaselineModel.id'): model_id}))

    for ref in qs0.distinct('meter_production_reference').values('meter_production_reference'):
        ref = ref.get('meter_production_reference')
        qs = qs0.filter(meter_production_reference=ref)
        logging.info('meter_financial_value_data_json: for meter %s ref %s has %s', m, ref, qs.count())
        data_ref = None
        if ref and ref.get('BaselineModel.id'):
            try:
                bm = BaselineModel.objects.get(id=ref.get('BaselineModel.id'))
                data_ref = '{}:{}'.format(bm.id, bm.model_class)
            except BaselineModel.DoesNotExist:
                pass
        for data in qs.order_by('-from_datetime'):
            data_key = data_ref or data.source
            meter_data = meter_data_map.get(data_key)
            if not meter_data:
                meter_data = []
                meter_data_map[data_key] = meter_data
            # Prevent adding duplicates
            datetime = date_to_string(data.from_datetime)
            # Offset the thru_datetime by one minute so the range is inclusive
            thru_datetime = date_to_string(data.thru_datetime - timedelta(seconds=1))
            if meter_data and datetime == meter_data[-1]['datetime']:
                continue
            value = data.amount
            if value and not isnan(value):
                # logging.info('meter_production_data_json: value %s', value)

                # convert to our chosen uom
                value = data.uom.convert_amount_to(value, uom)

                meter_data.append({
                    'datetime': datetime,
                    'thru_datetime': thru_datetime,
                    'amount': value,
                    'unit': uom.code,
                    'symbol': uom.symbol,
                })

    for k in meter_data_map.keys():
        meter_data_map[k] = list(reversed(meter_data_map[k]))

    return JsonResponse({'values': meter_data_map})


def meter_data_json(request, meter):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    m = Meter.objects.get(meter_id=meter)
    if not m:
        logger.warning('No Meter found with meter_id = %s', meter)
        return JsonResponse({'error': 'Meter data not found : {}'.format(meter)}, status=404)

    get_all = False
    trange = 24
    srange = request.GET.get('range')
    if srange:
        if srange != 'all':
            try:
                trange = int(srange)
                if trange < 0:
                    trange = -trange
            except Exception:
                trange = 24
        else:
            get_all = True

    # Select last <trange> records
    meter_data = []
    qs = m.meterhistory_set
    uom = None
    data_list = []

    if get_all:
        data_list = qs.order_by("as_of_datetime")
        for data in data_list:
            datetime = datetime_to_string(data.as_of_datetime)
            if not uom:
                uom = data.uom
            value = data.value
            if value and not isnan(value):
                value = data.uom.convert_amount_to(value, uom)

                meter_data.append({
                    'datetime': datetime,
                    'value': value
                })
    else:
        data_list = qs.order_by("-as_of_datetime")[:trange]
        for data in data_list:
            # Prevent adding duplicates
            datetime = datetime_to_string(data.as_of_datetime)
            if meter_data and datetime == meter_data[-1]['datetime']:
                continue
            if not uom:
                uom = data.uom
            value = data.value
            if value and not isnan(value):
                value = data.uom.convert_amount_to(value, uom)

                meter_data.append({
                    'datetime': datetime,
                    'value': value
                })

        meter_data = list(reversed(meter_data))

    uom_d = None
    if uom:
        uom_d = {
            'id': uom.uom_id,
            'unit': uom.unit
        }

    return JsonResponse({'uom': uom_d, 'values': meter_data})


@login_required()
def meter_data_import(request, meter):

    m = Meter.objects.get(meter_id=meter)
    if not m:
        logger.warning('No Meter found with meter_id = %s', meter)
        return JsonResponse({'error': 'Meter data not found : {}'.format(meter)}, status=404)

    if request.method == 'POST':
        form = MeterDataUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form_results = form.save()

            # an error message
            import_errors = form_results.get('import_errors')

            if import_errors:
                return JsonResponse({'errors': import_errors})

            return JsonResponse({'success': 1})
        else:
            return JsonResponse({'errors': form.errors})
    else:
        return JsonResponse({'error': 'Only POST methods are supported'})


class MeterRatePlanDetailView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = MeterRatePlan
    slug_field = "rate_plan_id"
    slug_url_kwarg = "rate_plan_id"

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        b.append({'label': 'Meter Rate Plan {}'.format(self.kwargs['rate_plan_id'])})
        return b


meter_rate_plan_detail_view = MeterRatePlanDetailView.as_view()


class MeterDetailView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"

    def get_context_data(self, **kwargs):
        context = super(MeterDetailView, self).get_context_data(**kwargs)
        if context['object'] and context['object'].weather_station:
            # Select last 24 records
            qs = WeatherHistory.objects.filter(weather_station=context['object'].weather_station)
            context['has_weather_data'] = qs.count()

        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})

        site = None
        if context['object'] and context['object'].site_id:
            try:
                site = SiteView.objects.get(entity_id=context['object'].site_id)
                label = 'Site'
                if site.description:
                    label = site.description
                url = reverse("core:site_detail", kwargs={'site': context['object'].site_id})
                b.append({'url': url, 'label': label})
            except Entity.DoesNotExist:
                pass

        b.append({'label': 'Meter {}'.format(self.kwargs['meter_id'])})
        return b


meter_detail_view = MeterDetailView.as_view()


class MeterCreateView(LoginRequiredMixin, WithBreadcrumbsMixin, CreateView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/meter_edit.html'
    form_class = MeterCreateForm

    def get_form_kwargs(self, *args, **kwargs):
        form_data = super(MeterCreateView, self).get_form_kwargs(*args, **kwargs)

        try:
            if not self.request.POST:
                initial_values = {}
                site = Entity.objects.get(entity_id=self.kwargs['site_id'])
                initial_values['site'] = site
                initial_values['weather_station'] = utils.get_default_weather_station_for_site(site)

                form_data['initial'] = initial_values
        except Exception as e:
            logging.error(e)

        return form_data

    def get_context_data(self, **kwargs):
        context = super(MeterCreateView, self).get_context_data(**kwargs)
        # add the parent Site Id
        context['site_id'] = self.kwargs['site_id']

        return context


meter_create_view = MeterCreateView.as_view()


class MeterEditView(LoginRequiredMixin, WithBreadcrumbsMixin, UpdateView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/meter_edit.html'
    form_class = MeterUpdateForm

    def get_success_url(self):
        obj = self.get_object()
        logging.info('MeterEditView::get_success_url = %s', obj.get_absolute_url())
        return obj.get_absolute_url()


meter_edit_view = MeterEditView.as_view()


class MeterDeactivateView(LoginRequiredMixin, WithBreadcrumbsMixin, DeleteView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'core/meter_deactivate.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = reverse("core:site_detail", kwargs={"site": self.object.site})

        self.object.thru_datetime = datetime.now()
        self.object.save()

        return HttpResponseRedirect(success_url)


meter_deactivate_view = MeterDeactivateView.as_view()
