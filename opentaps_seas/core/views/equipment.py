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

from .common import WithBreadcrumbsMixin, check_entity_permission_or_not_allowed, filter_entities_by_permission
from .common import WithFilesAndNotesAndTagsMixin
from .common import WithPointBreadcrumbsMixin
from .point import PointTable
from .. import utils
from .. import tasks
from ..celery import Progress
from ..forms.equipment import EquipmentCreateForm
from ..forms.equipment import SolarEdgeUpdateForm
from ..models import Entity, EntityPermission
from ..models import EquipmentView
from ..models import PointView
from ..models import SiteView
from ..models import SolarEdgeSetting

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


def filter_equipments_by_permission(queryset, user):
    # for normal users only show equipments for sites they have permissions to
    if not user.is_superuser:
        allowed_sites = filter_entities_by_permission(SiteView.objects, user)
        queryset = queryset.filter(kv_tags__siteRef__in=allowed_sites.values('object_id'))
    return queryset


class EquipmentTable(Table):
    entity_id = LinkColumn('core:site_equipment_detail',
                           args=[A('site_id'), A('entity_id')],
                           verbose_name='Equipment ID')
    description = Column()

    class Meta:
        model = EquipmentView
        fields = ('entity_id', 'description', )
        order_by = 'description'


class EquipmentFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = EquipmentView
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(entity_id__icontains=value)
            | Q(description__icontains=value)
        )


class EquipmentCreateView(LoginRequiredMixin, WithBreadcrumbsMixin, CreateView):
    model = Entity
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/equipment_edit.html'
    form_class = EquipmentCreateForm

    def get_initial(self):
        initials = {}
        if self.request.GET and 'bacnet_prefix' in self.request.GET:
            initials['bacnet_prefix'] = self.request.GET['bacnet_prefix']
        if self.request.GET and 'device_id' in self.request.GET:
            initials['device_id'] = self.request.GET['device_id']
        return initials

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if context['object']:
            site_desc = context['object'].entity_id
            if context['object'].description:
                site_desc = context['object'].description
            b.append({'url': reverse('core:site_detail', kwargs={'site': context['object'].entity_id}),
                      'label': 'Site {}'.format(site_desc)})
        b.append({'label': 'Equipment'})
        return b

    def get_context_data(self, **kwargs):
        context = super(EquipmentCreateView, self).get_context_data(**kwargs)
        # add the parent Site
        context['object'] = get_object_or_404(SiteView, entity_id=self.kwargs['site'])
        check_entity_permission_or_not_allowed(self.kwargs['site'], self.request.user)
        return context

    def get_form_kwargs(self):
        kwargs = super(EquipmentCreateView, self).get_form_kwargs()
        site = SiteView.objects.get(entity_id=self.kwargs['site'])
        kwargs.update({'site_id': site.object_id})
        kwargs.update({'user': self.request.user})
        return kwargs


equipment_create_view = EquipmentCreateView.as_view()


class EquipmentListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = EquipmentView
    table_class = EquipmentTable
    filterset_class = EquipmentFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/equipment_list.html'

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        # for normal users only show equipments for sites they have permissions to
        return filter_equipments_by_permission(qs, self.request.user)


equipment_list_view = EquipmentListView.as_view()


class EquipmentListJsonView(LoginRequiredMixin, ListView):
    model = EquipmentView

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        # for normal users only show equipments for sites they have permissions to
        qs = filter_equipments_by_permission(qs, self.request.user)
        return qs.order_by(Lower('object_id'), Lower('description'))

    def render_to_response(self, context, **response_kwargs):
        qs = context['object_list']
        site = None
        if self.request:
            site_id = self.request.GET.get('site')
            if site_id:
                try:
                    site = SiteView.objects.get(entity_id=site_id)
                except SiteView.DoesNotExist:
                    site = SiteView.objects.get(object_id=site_id)
        if site:
            qs = qs.filter(site_id=site.object_id)

        data = list(qs.values('entity_id', 'object_id', 'description'))
        return JsonResponse({'items': data})


equipment_list_json_view = EquipmentListJsonView.as_view()


class EquipmentDetailView(LoginRequiredMixin, WithFilesAndNotesAndTagsMixin, WithBreadcrumbsMixin, DetailView):
    model = EquipmentView
    slug_field = "entity_id"
    slug_url_kwarg = "equip"
    template_name = 'core/equipment_detail.html'
    entity_id_field = 'equip'
    head_tags = ['modelRef']

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if context.get('object') and context['object'].site_id:
            try:
                site = SiteView.objects.get(kv_tags__id=context['object'].site_id)
                if site:
                    site_desc = site.description or context['object'].site_id
                    b.append({'url': reverse('core:site_detail', kwargs={'site': site.entity_id}),
                              'label': 'Site {}'.format(site_desc)})
            except Exception as e:
                logging.error(e)

        b.append({'label': 'Equipment {}'.format(context['object'].description)})
        return b

    def get_context_data(self, **kwargs):
        context = super(EquipmentDetailView, self).get_context_data(**kwargs)
        context['grafana_url'] = settings.GRAFANA_BASE_URL + "/d/"
        context['grafana_snapshot_url'] = settings.GRAFANA_BASE_URL + "/dashboard/snapshot/"
        # add the parent Site (optional)
        try:
            context['site'] = SiteView.objects.get(object_id=context['object'].site_id)
            # for normal users only show equipment for sites they have permissions to
            check_entity_permission_or_not_allowed(context['site'].entity_id, self.request.user)
        except SiteView.DoesNotExist:
            pass
        # check SolarEdge data
        try:
            se = SolarEdgeSetting.objects.get(entity_id=context['object'].entity_id)
            context['solaredge'] = se
            if se.site_details and se.site_details.get('task_id'):
                # have not fetched the details yet
                task_id = se.site_details['task_id']
                context['solaredge_task_id'] = task_id
                context['solaredge_progress'] = Progress(task_id).get_info()
        except SolarEdgeSetting.DoesNotExist:
            pass

        context['data_points'] = PointView.objects.filter(equipment_id=context['object'].object_id).count()
        is_ahu = 0
        if 'ahu' in context['object'].m_tags:
            is_ahu = 1

        context['is_ahu'] = is_ahu

        return context


equipment_detail_view = EquipmentDetailView.as_view()


class EquipmentSolarEdgeEditView(LoginRequiredMixin, WithBreadcrumbsMixin, UpdateView):
    model = SolarEdgeSetting
    slug_field = "entity_id"
    slug_url_kwarg = "equip"
    template_name = 'core/solaredge_edit.html'
    form_class = SolarEdgeUpdateForm

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        o = context['object']
        if o:
            equip = EquipmentView.objects.get(entity_id=o.entity_id)
            try:
                site = SiteView.objects.get(kv_tags__id=equip.site_id)
                # for normal users only show equipment for sites they have permissions to
                check_entity_permission_or_not_allowed(site.entity_id, self.request.user)
                site_desc = site.description or equip.site_id
                b.append({'url': reverse('core:site_detail', kwargs={'site': site.entity_id}),
                          'label': 'Site {}'.format(site_desc)})
            except SiteView.DoesNotExist:
                pass
            b.append({'url': reverse('core:equipment_detail', kwargs={'equip': equip.entity_id}),
                      'label': 'Equipment {}'.format(equip.description)})
        b.append({'label': 'SolarEdge Settings'})
        return b

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_success_url(self):
        obj = self.get_object()
        equip = EquipmentView.objects.get(entity_id=obj.entity_id)
        return equip.get_absolute_url()


equipment_solaredge_edit_view = EquipmentSolarEdgeEditView.as_view()


class EquipmentSiteDetailView(EquipmentDetailView):
    def get_context_data(self, **kwargs):
        context = super(EquipmentSiteDetailView, self).get_context_data(**kwargs)
        # add the parent Site
        context['site'] = get_object_or_404(SiteView, entity_id=self.kwargs['site'])
        # for normal users only show equipment for sites they have permissions to
        check_entity_permission_or_not_allowed(context['site'].entity_id, self.request.user)
        return context


equipment_site_detail_view = EquipmentSiteDetailView.as_view()


@login_required()
def equipment_fetch_solaredge_details(request, equip):
    logger.info('equipment_fetch_solaredge_details: equip = %s', equip)
    equipment = get_object_or_404(EquipmentView, entity_id=equip)
    se = get_object_or_404(SolarEdgeSetting, entity_id=equip)
    result = {}
    
    try:
        site = SiteView.objects.get(kv_tags__id=equipment.site_id)
        # for normal users only show equipment for sites they have permissions to
        check_entity_permission_or_not_allowed(site.entity_id, request.user)
    except SiteView.DoesNotExist:
        pass

    kwargs = {
        'user': request.user,
        'entity_id': equipment.entity_id,
        'site_id': equipment.site_id,
        'description': equipment.description,
        'solaredge_api_key': se.api_key,
        'solaredge_site_id': se.site_id,
    }
    try:
        async_res = tasks.fetch_solaredge_for_equipment_task.delay(kwargs)
        logger.info('Started async fetching of solar data', async_res)
        result['success'] = 'async'
        result['task_id'] = async_res.task_id
    except Exception as e:
        # this could fail if Celery has issues in which case just note it
        msg = 'Could not start an async job to fetch SolarEdge data'
        logger.error('%s: %s', msg, e)
        # here we do it synchronously instead
        try:
            ses = tasks.fetch_solaredge_for_equipment(kwargs)
            result['success'] = 'sync'
            result['site_details'] = ses.site_details
            if ses.site_image:
                result['site_image'] = ses.site_image.url
            if ses.site_thumbnail:
                result['site_thumbnail'] = ses.site_thumbnail.url
        except Exception as e2:
            msg = 'Could not fetch SolarEdge data'
            logger.error('%s: %s', msg, e2)
            result['error'] = msg
            result['error_details'] = str(e2)
    return JsonResponse(result)


@login_required()
def equipment_data_points_table(request, equip):
    logger.info('equipment_data_points_table: equip = %s', equip)
    equipment = get_object_or_404(EquipmentView, entity_id=equip)
    
    try:
        site = SiteView.objects.get(kv_tags__id=equipment.site_id)
        # for normal users only show equipment for sites they have permissions to
        check_entity_permission_or_not_allowed(site.entity_id, request.user)
    except SiteView.DoesNotExist:
        pass

    data = PointView.objects.filter(equipment_id=equipment.object_id).order_by('description')
    d2 = utils.add_current_values(data)
    table = PointTable(d2, orderable=False)
    return HttpResponse(table.as_html(request))


class EquipmentPointDetailView(LoginRequiredMixin, WithFilesAndNotesAndTagsMixin,
                               WithPointBreadcrumbsMixin, DetailView):
    model = PointView
    slug_field = "entity_id"
    slug_url_kwarg = "point"
    template_name = 'core/point_detail.html'
    entity_id_field = 'point'

    def get_context_data(self, **kwargs):
        context = super(EquipmentPointDetailView, self).get_context_data(**kwargs)
        context['grafana_url'] = settings.GRAFANA_BASE_URL + "/d/"
        # add the parent Site
        context['site'] = get_object_or_404(SiteView, entity_id=self.kwargs['site'])
        check_entity_permission_or_not_allowed(self.kwargs['site'], self.request.user)

        # add the parent Equipment
        context['equipment'] = get_object_or_404(EquipmentView, entity_id=self.kwargs['equip'])

        if context['object']:
            context['charts'] = utils.charts_for_points([context['object']])

        return context

    def get_object(self, **kwargs):
        p = super(EquipmentPointDetailView, self).get_object(**kwargs)
        return utils.add_current_values([p])[0]


equipment_point_detail_view = EquipmentPointDetailView.as_view()


@require_POST
@login_required()
def equipment_dashboard(request, equip):
    result = {}
    try:
        entity = Entity.objects.get(entity_id=equip)
    except Entity.DoesNotExist:
        result = {'errors': 'Equipment not found : {}'.format(equip)}
    else:
        if entity.kv_tags.get('siteRef'):
            try:
                site = SiteView.objects.get(kv_tags__id=entity.kv_tags['siteRef'])
                # for normal users only show equipment for sites they have permissions to
                check_entity_permission_or_not_allowed(site.entity_id, request.user)
            except SiteView.DoesNotExist:
                pass
        topic = None
        if entity.kv_tags['dis']:
            topic = entity.kv_tags['dis']
        if not topic:
            topic = entity.kv_tags['id']
        if topic:
            default_err = 'Cannot create grafana dashboard'
            result_dashboard, result_shapshot = utils.create_equipment_grafana_dashboard(topic, entity.kv_tags['id'])
            if result_dashboard:
                result = result_dashboard.json()
                if result_dashboard.status_code == 200:
                    if result["uid"]:
                        entity.dashboard_uid = result["uid"]
                        result = {'success': 'Dashboard has been created.', 'dashboard_uid': result["uid"]}
                        if result_shapshot and result_shapshot.status_code == 200:
                            result_s = result_shapshot.json()
                            if result_s["key"]:
                                entity.dashboard_snapshot_uid = result_s["key"]
                                result["dashboard_snapshot_uid"] = entity.dashboard_snapshot_uid
                        entity.save()

                    else:
                        logger.error('create_equipment_grafana_dashboard did not return an uid : %s', result)
                        result = {'errors': default_err}
                else:
                    logger.error('create_equipment_grafana_dashboard response status invalid : %s',
                                 result_dashboard.status_code)
                    result = {'errors': default_err}
            else:
                logger.error('create_equipment_grafana_dashboard empty response')
                result = {'errors': default_err}
        else:
            result = {'errors': 'Cannot get Equipment {} description'.format(equip)}

    return JsonResponse(result)
