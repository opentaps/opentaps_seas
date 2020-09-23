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
from datetime import date
from datetime import timedelta
from datetime import timezone
from calendar import monthrange
import logging
from math import isnan

from .common import WithBreadcrumbsMixin
from .. import utils
from .. import pysam_utils
from .. import emissions_utils
from ..forms.meter import MeterCreateForm
from ..forms.meter import MeterDataUploadForm
from ..forms.meter import MeterUpdateForm
from ..forms.meter import MeterDataSolarEdgeForm
from ..forms.meter import MeterRatePlanHistoryUpdateForm
from ..models import date_to_string
from ..models import datetime_to_string
from ..models import Entity
from ..models import EquipmentView
from ..models import Meter
from ..models import MeterFinancialValue
from ..models import MeterFinancialValueItem
from ..models import MeterRatePlan
from ..models import MeterRatePlanHistory
from ..models import SiteView
from ..models import UnitOfMeasure
from ..models import WeatherHistory

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django_tables2 import Column
from django_tables2 import Table
from django_tables2.config import RequestConfig
from opentaps_seas.eemeter.models import BaselineModel
from rest_framework.decorators import api_view

logger = logging.getLogger(__name__)


class MeterFinancialValueTable(Table):
    meter_value_id = Column(verbose_name='#', linkify=lambda record: record.get_absolute_url())
    amount = Column(attrs={'th': {'align': 'right'}, 'td': {'align': 'right'}})

    def render_amount(self, record):
        return "{} {}".format(record.uom.symbol, record.amount)

    class Meta:
        attrs = {"style": "font-size:small"}
        model = MeterFinancialValue
        fields = (
            'meter_value_id',
            'from_datetime',
            'thru_datetime',
            'source',
            'amount'
            )
        order_by = '-from_datetime'


@login_required()
def meter_financial_values_table(request, meter):
    s = get_object_or_404(Meter, meter_id=meter)
    rc = RequestConfig(request, paginate={"per_page": 10})
    table = rc.configure(MeterFinancialValueTable(s.financial_values()))
    return HttpResponse(table.as_html(request))


class MeterFinancialValueItemTable(Table):
    amount = Column(attrs={'th': {'align': 'right'}, 'td': {'align': 'right'}})

    def render_amount(self, record):
        return "{} {}".format(record.uom.symbol, record.amount)

    class Meta:
        attrs = {"style": "font-size:small"}
        model = MeterFinancialValueItem
        fields = (
            'from_datetime',
            'thru_datetime',
            'description',
            'amount'
            )
        order_by = '-from_datetime'


@login_required()
def meter_financial_value_items_table(request, meter_value_id):
    s = get_object_or_404(MeterFinancialValue, meter_value_id=meter_value_id)
    rc = RequestConfig(request, paginate={"per_page": 10})
    table = rc.configure(MeterFinancialValueItemTable(s.meterfinancialvalueitem_set))
    return HttpResponse(table.as_html(request))


class MeterFinancialValueDetailView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = MeterFinancialValue
    slug_field = "meter_value_id"
    slug_url_kwarg = "meter_value_id"

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if self.kwargs['meter']:
            b.append({
                'url': reverse('core:meter_detail', kwargs={"meter_id": self.kwargs['meter']}),
                'label': 'Meter {}'.format(self.kwargs['meter'])})
        b.append({'label': 'Meter Financial Value {}'.format(self.kwargs['meter_value_id'])})
        return b


meter_financial_value_detail = MeterFinancialValueDetailView.as_view()


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
            if not value or isnan(value):
                value = 0
            else:
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
            if not value or isnan(value):
                value = 0
            else:
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
            if not value or isnan(value):
                value = 0
            else:
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
            if not value or isnan(value):
                value = 0
            else:
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


@login_required()
def meter_solaredge_data_import(request, meter):

    m = Meter.objects.get(meter_id=meter)
    if not m:
        logger.warning('No Meter found with meter_id = %s', meter)
        return JsonResponse({'error': 'Meter data not found : {}'.format(meter)}, status=404)

    if request.method == 'POST':
        form = MeterDataSolarEdgeForm(request.POST, user=request.user)
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


class MeterRatePlanHistoryView(LoginRequiredMixin, WithBreadcrumbsMixin, ListView):
    model = MeterRatePlanHistory
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"

    def get_context_data(self, **kwargs):
        context = super(MeterRatePlanHistoryView, self).get_context_data(**kwargs)
        context["meter_id"] = self.kwargs['meter_id']
        try:
            meter = Meter.objects.get(meter_id=self.kwargs['meter_id'])
        except Meter.DoesNotExist:
            pass
        else:
            context["meter"] = meter

        return context

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)

        meter_id = self.kwargs['meter_id']
        return qs.filter(meter_id=meter_id)

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

        b.append({'label': 'Meter Rate Plan History'})
        return b


meter_rate_plan_history_view = MeterRatePlanHistoryView.as_view()


class MeterDetailView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Meter
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"

    def get_context_data(self, **kwargs):
        context = super(MeterDetailView, self).get_context_data(**kwargs)
        context['is_solaredge'] = False
        if context['object']:
            meter = context['object']
            if meter.weather_station:
                # Select last 24 records
                qs = WeatherHistory.objects.filter(weather_station=meter.weather_station)
                context['has_weather_data'] = qs.count()

            latest = meter.get_meter_data().last()
            if latest:
                context['latest_meter_date'] = latest.as_of_datetime.strftime("%Y-%m-%d %H:%M:%S")

            if meter.solaredgesetting_set:
                qs = meter.solaredgesetting_set
                context['has_equipments'] = qs.count()
                if context['has_equipments']:
                    equips = []
                    for v in qs.values('entity_id'):
                        equips.append(EquipmentView.objects.get(entity_id=v['entity_id']))
                        context['is_solaredge'] = True
                    context['equipments'] = equips

            history_items = MeterRatePlanHistory.objects.filter(meter_id=meter.meter_id).order_by("-from_datetime")
            if history_items:
                context['rate_plan_history'] = history_items[0]

            if meter.utility_id and meter.account_number:
                today = datetime.today()
                last_day = monthrange(today.year, today.month)[1]
                from_date = date(today.year, today.month, 1)
                thru_date = date(today.year, today.month, last_day)

                try:
                    emissions_data = emissions_utils.get_emissions_data(meter.utility_id, meter.account_number,
                                                                        from_date.strftime("%Y-%m-%d"),
                                                                        thru_date.strftime("%Y-%m-%d"))
                    if emissions_data:
                        context['emissions_data'] = emissions_data
                    else:
                        context['emissions_data_error'] = 'Cannot get emissions data'
                except NameError as e:
                    context['emissions_data_error'] = e

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
        context['newmeter'] = True

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


@login_required()
def utility_rates_json(request):
    on_date = request.GET.get('on_date')
    meter_id = request.GET.get('meter_id')
    country = None
    address = None
    if meter_id:
        try:
            meter = Meter.objects.get(meter_id=meter_id)
        except Meter.DoesNotExist:
            return JsonResponse({'error': 'Meter not found : {}'.format(meter_id)})
        else:
            try:
                site = SiteView.objects.get(entity_id=meter.site_id)
            except SiteView.DoesNotExist:
                return JsonResponse({'error': 'Site not found : {}'.format(meter.site_id)})
            else:
                # get address
                if 'geoCountry' in site.kv_tags:
                    country = site.kv_tags['geoCountry']
                address = ""
                if 'geoAddr' in site.kv_tags:
                    address = site.kv_tags['geoAddr']
                if 'geoCity' in site.kv_tags:
                    address += ' ' + site.kv_tags['geoCity']

                if 'geoState' in site.kv_tags:
                    address += ' ' + site.kv_tags['geoState']

                if 'geoStreet' in site.kv_tags:
                    address += ' ' + site.kv_tags['geoStreet']

    data = []

    if not country:
        return JsonResponse({'error': 'Site country not found for meter : {}'.format(meter_id)})

    if not address:
        return JsonResponse({'error': 'Site address not found for meter : {}'.format(meter_id)})

    on_date = on_date.strip()
    if len(on_date) > 10:
        date_object = datetime.strptime(on_date, '%Y-%m-%d %H:%M:%S')
    else:
        date_object = datetime.strptime(on_date, '%Y-%m-%d')

    try:
        util_rates = pysam_utils.get_openei_util_rates(date_object, country, address)
    except NameError as e:
        return JsonResponse({'error': '{}'.format(e)})

    for rate_item in util_rates:
        data_item = {'value': rate_item['label']}
        data_item['name'] = pysam_utils.get_openei_util_rate_name(rate_item)
        data.append(data_item)

    # add the rate plans from meter_rate_plan (ie Simple Rate Plan) as an option
    meter_rate_plans = MeterRatePlan.objects.filter(thru_datetime__isnull=True).order_by('from_datetime')
    if meter_rate_plans:
        data_item = {'value': '', 'name': '----------------------------------'}
        data.append(data_item)
        for meter_rate_plan in meter_rate_plans:
            data_item = {'value': 'mrp_' + str(meter_rate_plan.rate_plan_id)}
            name = meter_rate_plan.description
            if meter_rate_plan.from_datetime:
                name += ' (from ' + meter_rate_plan.from_datetime.strftime('%Y-%m-%d') + ')'
            data_item['name'] = name
            data.append(data_item)

    return JsonResponse({'items': data})


@login_required()
@api_view(['GET', 'POST', 'DELETE'])
def meter_rate_plan_history(request):
    if request.method == 'POST':
        data = request.data
        meter_id = data.get('meter_id')

        page_label = data.get('page_label')

        if page_label.startswith('mrp_'):
            rate_plan_id = page_label.replace('mrp_', '')
            try:
                meter_rate_plan = MeterRatePlan.objects.get(rate_plan_id=rate_plan_id)
            except MeterRatePlan.DoesNotExist:
                return JsonResponse({'error': 'MeterRatePlan not found : {}'.format(meter_id)})
            else:
                rph = MeterRatePlanHistory.objects.create(
                    description=meter_rate_plan.description,
                    from_datetime=meter_rate_plan.from_datetime,
                    thru_datetime=meter_rate_plan.thru_datetime,
                    params=meter_rate_plan.params,
                    meter_id=meter_id,
                    rate_plan_id=rate_plan_id,
                    created_by_user=request.user
                    )

                rph.save()

                return JsonResponse({'success': 1})
        else:
            try:
                util_rates = pysam_utils.get_openei_util_rates(page_label=page_label)
            except NameError as e:
                return JsonResponse({'error': '{}'.format(e)})

            if util_rates and len(util_rates) == 1:
                util_rate = util_rates[0]

                description = '{} - {}'.format(util_rate['utility'], util_rate['name'])
                enddate = None
                thru_datetime = None
                if 'enddate' in util_rate.keys():
                    enddate = util_rate['enddate']
                startdate = datetime.fromtimestamp(util_rate['startdate'])
                from_datetime = datetime(startdate.year, startdate.month, startdate.day, tzinfo=timezone.utc)

                if enddate:
                    enddate = datetime.fromtimestamp(enddate)
                    thru_datetime = datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59, tzinfo=timezone.utc)

                rph = MeterRatePlanHistory.objects.create(
                    description=description,
                    from_datetime=from_datetime,
                    thru_datetime=thru_datetime,
                    rate_details=util_rate,
                    meter_id=meter_id,
                    created_by_user=request.user
                    )

                rph.save()

                return JsonResponse({'success': 1})
            else:
                return JsonResponse({'error': 'Cannot get rate data for selected rate plan : {}'.format(page_label)})
    elif request.method == 'GET':
        meter_id = request.GET.get('meter_id')
        items = MeterRatePlanHistory.objects.filter(meter_id=meter_id).order_by("-from_datetime")
        history_items = []
        for item in items:
            history_item = {'rate_plan_history_id': item.rate_plan_history_id,
                            'description': item.description,
                            'from_datetime': item.from_datetime,
                            'thru_datetime': item.thru_datetime
                            }

            history_items.append(history_item)

        return JsonResponse({'items': history_items})

    elif request.method == 'DELETE':
        data = request.data
        rate_plan_history_id = data.get('rate_plan_history_id')
        if rate_plan_history_id:
            try:
                rph = MeterRatePlanHistory.objects.get(rate_plan_history_id=rate_plan_history_id)
                rph.delete()
                return JsonResponse({'success': 1})
            except MeterRatePlanHistory.DoesNotExist:
                return JsonResponse({'error': 'MeterRatePlanHistory not found: {}'.format(rate_plan_history_id)})
        else:
            return JsonResponse({'error': 'Rate Plan History ID required'})


class MeterRatePlanHistoryDetailView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = MeterRatePlanHistory
    slug_field = "rate_plan_history_id"
    slug_url_kwarg = "rate_plan_history_id"
    template_name = 'core/meter_rate_plan_history_detail.html'

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        b.append({'label': 'Meter Rate Plan History {}'.format(self.kwargs['rate_plan_history_id'])})
        return b


meter_rate_plan_history_detail = MeterRatePlanHistoryDetailView.as_view()


class MeterRatePlanHistoryEditView(LoginRequiredMixin, WithBreadcrumbsMixin, UpdateView):
    model = MeterRatePlanHistory
    slug_field = "rate_plan_history_id"
    slug_url_kwarg = "rate_plan_history_id"
    template_name = 'core/meter_rate_plan_history_edit.html'
    form_class = MeterRatePlanHistoryUpdateForm

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        b.append({'label': 'Meter Rate Plan History {}'.format(self.kwargs['rate_plan_history_id'])})
        return b

    def get_success_url(self):
        obj = self.get_object()
        mrph = MeterRatePlanHistory.objects.get(rate_plan_history_id=obj.rate_plan_history_id)
        return mrph.get_absolute_url()


meter_rate_plan_history_edit = MeterRatePlanHistoryEditView.as_view()
