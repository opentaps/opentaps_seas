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

from .common import GoogleApiMixin
from .common import WithBreadcrumbsMixin
from .common import WithFilesAndNotesAndTagsMixin
from .. import utils
from ..forms.site import SiteCreateForm
from ..models import Entity
from ..models import EquipmentView
from ..models import Geo
from ..models import Meter
from ..models import PointView
from ..models import SiteView
from .point import PointTable

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError
from django.db.models.functions import Lower
from django.db.models import Q
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin

logger = logging.getLogger(__name__)


class SiteTable(Table):
    entity_id = LinkColumn('core:site_detail',
                           args=[A('entity_id')],
                           text=lambda record: record.object_id,
                           verbose_name='Site ID')
    description = Column()
    area = Column()
    city = Column()
    state = Column()

    class Meta:
        model = SiteView
        fields = ('entity_id', 'description', 'state', 'city', 'area', )
        order_by = 'description'


class SiteFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = SiteView
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(entity_id__icontains=value)
            | Q(description__icontains=value)
            | Q(city__icontains=value)
            | Q(state__icontains=value)
            | Q(area__icontains=value)
        )


class SiteBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if context.get('object'):
            b.append({'label': 'Site {}'.format(context['object'].description or context['object'].entity_id)})
        return b


class SiteListView(LoginRequiredMixin, SingleTableMixin, GoogleApiMixin, WithBreadcrumbsMixin, FilterView):
    model = SiteView
    table_class = SiteTable
    filterset_class = SiteFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/site_list.html'

    def get_context_data(self, **kwargs):
        context = super(SiteListView, self).get_context_data(**kwargs)
        table = context['table']

        addr_locs = []
        if table and table.paginated_rows:
            counter = 0
            for row in table.paginated_rows:
                object_id = row.get_cell_value('entity_id')
                site = None
                try:
                    site = SiteView.objects.get(object_id=object_id)
                except Entity.DoesNotExist:
                    pass
                if not site:
                    continue
                description = row.get_cell_value('description')
                if site.entity_id:
                    tags = utils.get_tags_for_topic(site.entity_id)
                    for tag in tags:
                        addr_loc = utils.get_site_addr_loc(tag.kv_tags, site.entity_id, self.request.session)
                        if addr_loc:
                            addr_loc["index"] = counter
                            if description:
                                addr_loc["description"] = description
                            addr_locs.append(addr_loc)
                counter = counter + 1

        if addr_locs:
            context['addr_locs'] = addr_locs

        return context


site_list_view = SiteListView.as_view()


class SiteListJsonView(LoginRequiredMixin, ListView):
    model = SiteView

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.order_by(Lower('object_id'), Lower('description'))

    def render_to_response(self, context, **response_kwargs):
        data = list(context['object_list'].values('entity_id', 'object_id', 'description', 'city', 'state', 'area'))
        return JsonResponse({'items': data})


site_list_json_view = SiteListJsonView.as_view()


class SiteCreateView(LoginRequiredMixin, SiteBCMixin, CreateView):
    model = Entity
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/site_edit.html'
    form_class = SiteCreateForm

    def get_context_data(self, **kwargs):
        context = super(SiteCreateView, self).get_context_data(**kwargs)
        context['country_list'] = Geo.get_country_choices()

        return context


site_create_view = SiteCreateView.as_view()


class SiteDetailView(LoginRequiredMixin, SingleTableMixin, WithFilesAndNotesAndTagsMixin, SiteBCMixin, DetailView):
    model = SiteView
    slug_field = "entity_id"
    slug_url_kwarg = "site"
    template_name = 'core/site_detail.html'
    table_class = PointTable
    entity_id_field = 'site'

    def get_context_data(self, **kwargs):
        context = super(SiteDetailView, self).get_context_data(**kwargs)
        results = []
        site = get_object_or_404(SiteView, entity_id=self.kwargs['site'])
        equipments = EquipmentView.objects.filter(site_id=site.object_id).exclude(m_tags__contains=['point'])
        for e in equipments:
            data_points = PointView.objects.filter(equipment_id=e.object_id).count()
            results.append({'site': site, 'equipment': e, 'data_points': data_points})
        context['equipments'] = results
        context['link_add_url'] = reverse("core:equipment_create", kwargs={"site": self.kwargs['site']})

        bacnet_configs = PointView.objects.filter(site_id=site.object_id).exclude(
            kv_tags__bacnet_prefix__isnull=True).exclude(
            kv_tags__bacnet_prefix__exact='').values(
            'site_id', 'kv_tags__bacnet_prefix', 'kv_tags__bacnet_device_id').annotate(
            dcount=Count('kv_tags__bacnet_prefix'))

        if bacnet_configs:
            bacnet_cfg = []
            for bacnet_config in bacnet_configs:
                item = {'prefix': bacnet_config['kv_tags__bacnet_prefix'],
                        'device_id': bacnet_config['kv_tags__bacnet_device_id']}
                bc_equipments = EquipmentView.objects.filter(
                    kv_tags__bacnet_prefix=bacnet_config['kv_tags__bacnet_prefix'],
                    site_id=bacnet_config['site_id']
                    )
                if bc_equipments:
                    bc_equipment = bc_equipments[0]
                    if bc_equipment:
                        item["bc_equipment_entity_id"] = bc_equipment.entity_id
                        item["bc_equipment_description"] = bc_equipment.description
                bacnet_cfg.append(item)
            context['bacnet_configs'] = bacnet_cfg

        meters = Meter.objects.filter(site_id=site.entity_id, thru_datetime__isnull=True).order_by('meter_id')
        context['meters'] = meters

        return context


site_detail_view = SiteDetailView.as_view()


@login_required()
def site_ahu_summary_json(request, site):
    s = get_object_or_404(SiteView, entity_id=site)
    ahus = EquipmentView.objects.filter(site_id=s.object_id).filter(m_tags__contains=['ahu'])
    logger.info('site_ahu_summary_json found AHU equipments: %s', ahus)
    results = {}
    ahus_results = []
    # get range of date, from data point values epoch
    epoch_0 = None
    epoch_1 = None
    try:
        for e in ahus:
            ahu_data_points = utils.get_ahu_current_values(e.object_id)
            logger.info('site_ahu_summary_json ==> %s', e.object_id)
            points = []
            for k, point in ahu_data_points.items():
                logger.info('ahu_data_point %s ==> %s', k, point)
                v = point.current_value
                epoch = v.get('epoch')
                if epoch:
                    if not epoch_0 or epoch_0 > epoch:
                        epoch_0 = epoch
                    if not epoch_1 or epoch_1 < epoch:
                        epoch_1 = epoch
                points.append({
                    'name': k,
                    'value': v,
                    'topic': point.topic,
                    'tags': point.m_tags,
                    'ts': utils.format_epoch(epoch) if epoch else None
                })
            ahus_results.append({
                'equipment': {
                    'entity_id': e.entity_id,
                    'object_id': e.object_id,
                    'description': e.description
                },
                'data_points': points
            })
    except OperationalError:
        logging.warning('Crate database unavailable')

    logger.info('site_ahu_summary_json ahus_results: %s', ahus_results)
    results['ahus'] = ahus_results
    if epoch_0:
        results['ahus_from'] = utils.format_epoch(epoch_0)
    if epoch_1 != epoch_0:
        results['ahus_to'] = utils.format_epoch(epoch_1)
    return JsonResponse(results)


@login_required()
def site_pie_chart_data_json(request, site):
    s = get_object_or_404(SiteView, entity_id=site)
    equipments = EquipmentView.objects.filter(site_id=s.object_id).exclude(m_tags__contains=['point'])
    pie = {}
    if request.GET.get('cold_threshold'):
        cold_threshold = float(request.GET.get('cold_threshold'))
    else:
        cold_threshold = 69
    if request.GET.get('hot_threshold'):
        hot_threshold = float(request.GET.get('hot_threshold'))
    else:
        hot_threshold = 75
    for e in equipments:
        data_points = PointView.objects.filter(equipment_id=e.object_id)
        data_points = data_points.filter(m_tags__contains=['air', 'his', 'point', 'sensor', 'temp'])
        data_points = data_points.exclude(m_tags__contains=['equip'])
        try:
            for d in utils.add_current_values(data_points, raw=True):
                cv = d.current_value.get('value', 'N/A')
                logger.info('site_pie_chart_data_json got value %s -> %s', d.entity_id, cv)
                if isinstance(cv, str):
                    try:
                        cv = float(cv)
                    except ValueError:
                        cv = 'N/A'
                if 'N/A' == cv or cv > 200 or cv < -50:
                    if 'No Data' not in pie:
                        pie['No Data'] = 1
                    else:
                        pie['No Data'] += 1
                elif cv < cold_threshold:
                    if 'Cold' not in pie:
                        pie['Cold'] = 1
                    else:
                        pie['Cold'] += 1
                elif cv > hot_threshold:
                    if 'Hot' not in pie:
                        pie['Hot'] = 1
                    else:
                        pie['Hot'] += 1
                else:
                    if 'Comfortable' not in pie:
                        pie['Comfortable'] = 1
                    else:
                        pie['Comfortable'] += 1
        except OperationalError:
            logging.warning('Crate database unavailable')

    labels = []
    values = []
    logger.info('site_pie_chart_data_json pie: %s', pie)
    for k, v in pie.items():
        labels.append(k)
        values.append(v)
    return JsonResponse({'values': values, 'labels': labels})
