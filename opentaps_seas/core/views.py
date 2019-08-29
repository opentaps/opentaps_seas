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

import csv
import json
import os
import tempfile
from io import TextIOWrapper
from io import BytesIO
from io import StringIO
from zipfile import ZipFile
import logging
from urllib.parse import urlparse

from datetime import datetime

from . import utils
from .forms import EntityLinkForm
from .forms import EntityNoteDeleteForm
from .forms import EntityNoteForm
from .forms import EntityNoteUpdateForm
from .forms import FileDeleteForm
from .forms import FileUpdateForm
from .forms import FileUploadForm
from .forms import ModelCreateForm
from .forms import ModelUpdateForm
from .forms import SiteCreateForm
from .forms import TagChangeForm
from .forms import TagUpdateForm
from .forms import TopicAssocForm
from .forms import TopicImportForm
from .forms import TopicExportForm
from .forms import TopicTagRuleCreateForm
from .forms import TopicTagRuleSetCreateForm
from .forms import TopicTagRuleSetImportForm
from .forms import TopicTagRuleSetRunForm
from .forms import EquipmentCreateForm
from .forms import TagImportForm
from .models import Entity
from .models import EntityFile
from .models import EntityNote
from .models import EquipmentView
from .models import Geo
from .models import ListableEntity
from .models import ModelView
from .models import PointView
from .models import SiteView
from .models import Tag
from .models import TimeZone
from .models import Topic
from .models import TopicTagRule
from .models import TopicTagRuleSet
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import ProtectedError
from django.db.models import Q
from django.db.models import Count
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2.config import RequestConfig
from django_tables2 import Column
from django_tables2 import CheckBoxColumn
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin
from easy_thumbnails.files import get_thumbnailer
from filer.models import Image as FilerFile
from rest_framework.decorators import api_view

logger = logging.getLogger(__name__)


class WithBreadcrumbsMixin(object):
    def get_breadcrumbs(self, context):
        b = []
        if self.model and self.model._meta and self.model._meta.verbose_name_plural:
            b.append({'label': self.model._meta.verbose_name_plural.capitalize()})
        return b

    def render_to_response(self, context, **kwargs):
        r = super().render_to_response(context, **kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs(context)
        return r


class TagFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = Tag
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(tag__icontains=value) | Q(description__icontains=value)
        )


class TagTable(Table):
    tag = LinkColumn('core:tag_detail', args=[A('tag')])

    class Meta:
        order_by = 'tag'
        model = Tag
        fields = ('tag', 'kind', 'description', )


class TagListTable(Table):
    tag = Column(verbose_name='Tags')

    class Meta:
        order_by = 'tag'


class TagBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:tag_list'), 'label': 'Tags'})
        if context.get('object'):
            b.append({'label': 'Tag {}'.format(context['object'].tag)})
        return b


class TagDetailView(LoginRequiredMixin, TagBCMixin, DetailView):
    model = Tag
    slug_field = "tag"
    slug_url_kwarg = "tag"


tag_detail_view = TagDetailView.as_view()


class TagCreateView(LoginRequiredMixin, TagBCMixin, CreateView):
    model = Tag
    slug_field = "tag"
    slug_url_kwarg = "tag"
    template_name = 'core/tag_edit.html'
    form_class = TagChangeForm


tag_create_view = TagCreateView.as_view()


class TagEditView(LoginRequiredMixin, TagBCMixin, UpdateView):
    model = Tag
    slug_field = "tag"
    slug_url_kwarg = "tag"
    template_name = 'core/tag_edit.html'
    form_class = TagUpdateForm


tag_edit_view = TagEditView.as_view()


class TagDeleteView(LoginRequiredMixin, TagBCMixin, DeleteView):
    model = Tag
    slug_field = "tag"
    slug_url_kwarg = "tag"
    template_name = 'core/tag_delete.html'
    success_url = reverse_lazy('core:tag_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        try:
            self.object.delete()
        except ProtectedError:
            messages.add_message(request, messages.ERROR, 'Can not delete: this Tag is being used!')
            return HttpResponseRedirect(self.object.get_absolute_url())

        return HttpResponseRedirect(success_url)


tag_delete_view = TagDeleteView.as_view()


class TagListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = Tag
    table_class = TagTable
    filterset_class = TagFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/tag_list.html'


tag_list_view = TagListView.as_view()


class TagListJsonView(LoginRequiredMixin, ListView):
    model = Tag

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.order_by(Lower('tag'), Lower('description'))

    def render_to_response(self, context, **response_kwargs):
        data = list(context['object_list'].values('tag', 'description', 'kind'))
        return JsonResponse({'items': data})


tag_list_json_view = TagListJsonView.as_view()


class EntityFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = ListableEntity
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(entity_id__icontains=value) | Q(description__icontains=value)
        )


class EntityTable(Table):
    entity_id = LinkColumn('core:entity_detail',
                           args=[A('entity_id')],
                           text=lambda record: record.object_id,
                           verbose_name='Entity ID')
    description = Column()

    class Meta:
        model = ListableEntity
        fields = ('entity_id', 'description', )
        order_by = 'description'


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


class TopicTable(Table):
    cb = CheckBoxColumn(accessor='topic')
    topic = Column()
    point_description = LinkColumn('core:point_detail',
                                   args=[A('entity_id')],
                                   verbose_name='Data Point', orderable=False)
    button = Column(accessor='topic', verbose_name='', default='', orderable=False)

    def render_button(self, record):
        p = record.get_related_point()
        if p:
            return ''
        else:
            return format_html('''
                <a class="btn btn-secondary btn-sm" href="{}">
                <i class="fa fa-plus"></i> Add
                </a>'''.format(reverse(
                    "core:topic_setup",
                    kwargs={"topic": record.topic}),))

    class Meta:
        order_by = 'topic'


class TopicFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = Topic
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(topic__icontains=value)
        )


class TopicTagRuleSetTable(Table):
    name = LinkColumn('core:topictagruleset_detail',
                      args=[A('id')],
                      text=lambda record: record.name)
    rules = Column(accessor='topictagrule_set.count', orderable=False)
    buttons = Column(accessor='id', verbose_name='', default='', orderable=False)

    def render_buttons(self, record):
        return format_html('''
            <a class="btn btn-secondary btn-sm" href="{}">
            <i class="fa fa-cog"></i> Run
            </a>
            <a class="btn btn-danger btn-sm" href="#" v-confirm="delete_tag_ruleset({})">
            <i class="fa fa-trash"></i> Delete
            </a>'''.format(reverse('core:topictagruleset_run', kwargs={'id': record.id}), record.id),)

    class Meta:
        order_by = 'name'
        row_attrs = {
            'id': lambda record: 'topicruleset_' + str(record.id)
        }


class TopicTagRuleSetExportTable(Table):
    cb = CheckBoxColumn(accessor='id')
    name = Column()
    rules = Column(accessor='topictagrule_set.count', orderable=False)

    class Meta:
        order_by = 'name'
        row_attrs = {
            'id': lambda record: 'topicruleset_' + str(record.id)
        }


class TopicTagRuleTable(Table):
    name = LinkColumn('core:topictagrule_detail',
                      args=[A('id')],
                      text=lambda record: record.name)
    filters = Column(accessor='filters.__len__', orderable=False)
    tags = Column(accessor='tags.__len__', orderable=False)
    action = Column(orderable=False)
    buttons = Column(accessor='id', verbose_name='', default='', orderable=False)

    def render_buttons(self, record):
        return format_html('''
            <a class="btn btn-danger btn-sm" href="#" v-confirm="delete_tag_rule({})">
            <i class="fa fa-trash"></i> Delete
            </a>'''.format(record.id, record.id),)

    class Meta:
        order_by = 'name'
        row_attrs = {
            'id': lambda record: 'topicrule_' + str(record.id)
        }


class TopicTagRuleSetFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = TopicTagRuleSet
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
        )


class TopicTagRuleFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = TopicTagRule
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
        )


class ModelTable(Table):
    entity_id = LinkColumn('core:model_detail',
                           args=[A('entity_id')],
                           text=lambda record: record.object_id,
                           verbose_name='Model ID')
    description = Column()

    class Meta:
        order_by = 'entity_id'


class ModelFilter(FilterSet):
    query = CharFilter(method='filter_by_all_fields')

    class Meta:
        model = ModelView
        fields = []

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(entity_id__icontains=value)
            | Q(description__icontains=value)
        )


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


class PointTable(Table):
    description = LinkColumn('core:point_detail',
                             args=[A('entity_id')],
                             verbose_name='Data Point')
    current_value = Column(verbose_name='Latest Value')

    class Meta:
        order_by = 'description'


class WithFilesAndNotesAndTagsMixin(object):
    @property
    def entity_id_field(self):
        return NotImplemented

    def get_context_data(self, **kwargs):
        context = super(WithFilesAndNotesAndTagsMixin, self).get_context_data(**kwargs)

        # check for files
        context['file_upload_form'] = {
            'url': reverse("core:entity_file_upload", kwargs={"entity_id": self.kwargs[self.entity_id_field]}),
            'link_add_url': reverse("core:entity_link", kwargs={"entity_id": self.kwargs[self.entity_id_field]}),
            'params': [
                {'key': 'entity_id', 'value': self.kwargs[self.entity_id_field]}
            ]
        }

        # check for notes
        context['notes_form'] = {
            'url': reverse("core:entity_note", kwargs={"entity_id": self.kwargs[self.entity_id_field]}),
            'params': [
                {'key': 'entity_id', 'value': self.kwargs[self.entity_id_field]}
            ]
        }

        # check for tags
        context['tags'] = utils.get_tags_list_for_topic(self.kwargs[self.entity_id_field])
        context['tags_form'] = {
            'url': reverse("core:entity_tag", kwargs={"entity_id": self.kwargs[self.entity_id_field]})
        }

        # check head tags
        h_tags = []
        if hasattr(self, 'head_tags') and self.head_tags:
            for htag in self.head_tags:
                v = utils.get_tag(htag)
                if v:
                    t = {'tag': v.tag, 'description': v.description, 'details': v.details, 'kind': v.kind}
                    ref = v.get_ref_entity()
                    if ref:
                        t['ref_entity'] = ref.as_dict()
                    for tag in context['tags']:
                        if tag['tag'] == htag:
                            t['found'] = True
                            if 'value' in tag:
                                t['value'] = tag['value']
                            if 'slug' in tag:
                                t['slug'] = tag['slug']
                            break
                    h_tags.append(t)
            context['head_tags'] = h_tags
        return context


class EntityListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = ListableEntity
    table_class = EntityTable
    filterset_class = EntityFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/entity_list.html'


entity_list_view = EntityListView.as_view()


class EntityDetailView(LoginRequiredMixin, WithFilesAndNotesAndTagsMixin, WithBreadcrumbsMixin, DetailView):
    model = Entity
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    entity_id_field = 'entity_id'

    def get_breadcrumbs(self, context):
        return [
            {'url': reverse('core:entity_list'), 'label': 'Entities'},
            {'label': 'Entity {}'.format(self.kwargs['entity_id'])}
        ]

    def render_to_response(self, context, **response_kwargs):
        entity_id = self.kwargs['entity_id']
        mtags = utils.get_mtags_for_topic(entity_id)
        for tag in mtags:
            for tag in tag.m_tags:
                if tag == 'site':
                    return HttpResponseRedirect(reverse("core:site_detail", kwargs={"site": entity_id}))
                if tag == 'model':
                    return HttpResponseRedirect(reverse("core:model_detail", kwargs={"entity_id": entity_id}))
                if tag == 'equip':
                    return HttpResponseRedirect(reverse("core:equipment_detail", kwargs={"equip": entity_id}))
                if tag == 'point':
                    return HttpResponseRedirect(reverse("core:point_detail", kwargs={"entity_id": entity_id}))

        return super(EntityDetailView, self).render_to_response(context, **response_kwargs)


entity_detail_view = EntityDetailView.as_view()


class ModelBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:model_list'), 'label': 'Models'})
        m = context.get('object')
        if m:
            b.append({'label': '{}'.format(m.description or m.object_id)})
            while m:
                m = m.get_parent_model()
                if not m:
                    break
                b.insert(1, {
                    'url': reverse('core:model_detail', kwargs={'entity_id': m.entity_id}),
                    'label': '{}'.format(m.description or m.object_id)})

        return b


class ModelListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = ModelView
    table_class = ModelTable
    filterset_class = ModelFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/model_list.html'

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        # allow a direct search of the child models
        if self.request.GET.get('query'):
            return qs
        return qs.exclude(kv_tags__has_key='modelRef')


model_list_view = ModelListView.as_view()


class ModelListJsonView(LoginRequiredMixin, ListView):
    model = ModelView
    parent_given = False

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        # allow a direct search of the child models
        if 'parent' not in self.request.GET:
            qs = qs.order_by(Lower('object_id'), Lower('description'))
            return qs
        qs = qs.order_by(Lower('description'), Lower('object_id'))
        self.parent_given = True
        p = self.request.GET.get('parent')
        if p and p != '_':
            return qs.filter(kv_tags__modelRef=p)
        else:
            return qs.exclude(kv_tags__has_key='modelRef')

    def render_to_response(self, context, **response_kwargs):
        if self.parent_given:
            data = list(context['object_list'].values('entity_id', 'object_id', 'description', 'm_tags', 'kv_tags'))
        else:
            data = list(context['object_list'].values('entity_id', 'object_id', 'description'))
        return JsonResponse({'items': data})


model_list_json_view = ModelListJsonView.as_view()


class ModelDetailView(LoginRequiredMixin, WithFilesAndNotesAndTagsMixin, ModelBCMixin, DetailView):
    model = ModelView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    entity_id_field = 'entity_id'
    head_tags = ['dis', 'model']
    template_name = 'core/model_detail.html'


model_detail_view = ModelDetailView.as_view()


class ModelCreateView(LoginRequiredMixin, ModelBCMixin, CreateView):
    model = ModelView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/model_edit.html'
    form_class = ModelCreateForm

    def get_initial(self):
        if 'entity_id' in self.kwargs:
            try:
                pm = Entity.objects.get(entity_id=self.kwargs['entity_id'], m_tags__contains=['model'])
                return {'parent_id': pm.kv_tags['id']}
            except Entity.DoesNotExist:
                pass
        return {}


model_create_view = ModelCreateView.as_view()


class ModelEditView(LoginRequiredMixin, ModelBCMixin, UpdateView):
    model = ModelView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/model_edit.html'
    form_class = ModelUpdateForm

    def get_initial(self):
        initial = super().get_initial()
        logging.info('ModelEditView::initial = %s', initial)
        obj = self.get_object()
        if obj and 'modelRef' in obj.kv_tags:
            initial['parent_id'] = obj.kv_tags['modelRef']
        return initial

    def get_success_url(self):
        obj = self.get_object()
        logging.info('ModelEditView::get_success_url = %s', obj.get_absolute_url())
        return obj.get_absolute_url()


model_edit_view = ModelEditView.as_view()


class ModelDeleteView(LoginRequiredMixin, ModelBCMixin, DeleteView):
    model = ModelView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/model_delete.html'
    success_url = reverse_lazy('core:model_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        try:
            self.object.delete()
        except ProtectedError:
            messages.add_message(request, messages.ERROR, 'Can not delete: this Model is being used!')
            return HttpResponseRedirect(self.object.get_absolute_url())

        return HttpResponseRedirect(success_url)


model_delete_view = ModelDeleteView.as_view()


class SiteBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
        if context.get('object'):
            b.append({'label': 'Site {}'.format(context['object'].description or context['object'].entity_id)})
        return b


class SiteListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
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

        if addr_locs and settings.GOOGLE_API_KEY:
            context['addr_locs'] = addr_locs
            context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY

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
            kv_tags__bacnet_prefix__exact='').values('kv_tags__bacnet_prefix', 'kv_tags__bacnet_device_id').annotate(
            dcount=Count('kv_tags__bacnet_prefix'))
        if bacnet_configs:
            bacnet_cfg = []
            for bacnet_config in bacnet_configs:
                item = {'prefix': bacnet_config['kv_tags__bacnet_prefix'],
                        'device_id': bacnet_config['kv_tags__bacnet_device_id']}
                bc_equipments = EquipmentView.objects.filter(
                    kv_tags__bacnet_prefix=bacnet_config['kv_tags__bacnet_prefix'])
                if bc_equipments:
                    bc_equipment = bc_equipments[0]
                    if bc_equipment:
                        item["bc_equipment_entity_id"] = bc_equipment.entity_id
                        item["bc_equipment_description"] = bc_equipment.description
                bacnet_cfg.append(item)
            context['bacnet_configs'] = bacnet_cfg

        return context


site_detail_view = SiteDetailView.as_view()


class StateListJsonView(LoginRequiredMixin, ListView):
    model = Geo

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.order_by(Lower('geo_name'))

    def render_to_response(self, context, **response_kwargs):
        country = self.kwargs['country']
        data = []
        if country:
            data = Geo.get_states_list(country)

        return JsonResponse({'items': data})


state_list_json_view = StateListJsonView.as_view()


class TimezoneListJsonView(LoginRequiredMixin, ListView):
    model = TimeZone

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.order_by('tzoffset', Lower('time_zone'))

    def render_to_response(self, context, **response_kwargs):
        # note this can pass the geo_code_name as well
        geo_id = self.kwargs['geo_id']
        geo = Geo.objects.filter(geo_code_id=geo_id).first()
        if not geo:
            geo = Geo.objects.filter(geo_code_name=geo_id).first()
        if geo:
            geo_id = geo.geo_code_id
        data = TimeZone.get_choices(geo_id)
        # convert from ChoiceField choices to JSON

        return JsonResponse({'items': [{'id': x[0], 'name': x[1]} for x in data]})


timezone_list_json_view = TimezoneListJsonView.as_view()


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

        return context

    def get_form_kwargs(self):
        kwargs = super(EquipmentCreateView, self).get_form_kwargs()
        site = SiteView.objects.get(entity_id=self.kwargs['site'])
        kwargs.update({'site_id': site.object_id})
        return kwargs


equipment_create_view = EquipmentCreateView.as_view()


class TopicListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, ListView):
    model = Topic
    table_class = TopicTable
    table_pagination = {'per_page': 15}
    template_name = 'core/topic_list.html'

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        self.used_filters = []
        self.rule = None

        topic_filter = None
        if "topic_filter" in self.request.session:
            topic_filter = self.request.session["topic_filter"]

        if topic_filter:
            self.request.session["topic_filter"] = None

        self.select_not_mapped_topics = self.request.GET.get('select_not_mapped_topics')
        if self.select_not_mapped_topics:
            # only list topics where there is no related data point
            # because those are 2 different DB need to get all the data points
            # where topic is non null and remove those topics
            # note: cast topic into entity_id as raw query must have the model PK
            r = PointView.objects.raw("SELECT DISTINCT(topic) as entity_id FROM {}".format(PointView._meta.db_table))
            qs = qs.filter(topic__in=[p.entity_id for p in r])

        if self.kwargs.get('id'):
            rule_id = self.kwargs['id']
            logging.info('got a rule ID given: %s', rule_id)
            self.rule = get_object_or_404(TopicTagRule, id=rule_id)
            q_filters = []
            for f in self.rule.filters:
                self.used_filters.append({
                    'field': f.get('field'),
                    'type': f.get('type'),
                    'value': f.get('value')
                })
                q_filters.append((f.get('field'), f.get('type'), f.get('value')))
            qs = utils.apply_filters_to_queryset(qs, q_filters)

        elif topic_filter:
            filter_elem = {'type': 'c', 'value': topic_filter}
            self.used_filters.append(filter_elem)
            qs = qs.filter(Q(topic__icontains=topic_filter))
        else:

            n = 0
            filters_count = self.request.GET.get('filters_count')
            if filters_count:
                n = int(filters_count)

            q_filters = []
            for i in range(n):
                filter_type = self.request.GET.get('t' + str(i))
                filter_field = self.request.GET.get('n' + str(i))
                if filter_type:
                    filter_value = self.request.GET.get('f' + str(i))
                    logging.info('TopicListView get_queryset got filter [%s - %s : %s]',
                                 filter_field, filter_type, filter_value)
                    self.used_filters.append({
                        'field': filter_field,
                        'type': filter_type,
                        'value': filter_value
                    })
                    q_filters.append((filter_field, filter_type, filter_value))
            qs = utils.apply_filters_to_queryset(qs, q_filters)

        # add empty filter at the end
        self.used_filters.append({'type': '', 'value': ''})
        logging.info('TopicListView get_queryset filtered %s', qs)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['used_filters'] = self.used_filters
        context['sites_list'] = SiteView.get_site_obj_choices()
        if context['sites_list']:
            site_id = context['sites_list'][0]['id']
            if site_id:
                context['default_rule_action_site_id'] = site_id
        if self.rule:
            context['rule'] = self.rule
            if self.rule.action:
                context['rule_action'] = self.rule.action
            if self.rule.action_fields:
                context['rule_action_fields'] = json.dumps(self.rule.action_fields)

        return context

    def get_breadcrumbs(self, context):
        if self.rule:
            b = []
            b.append({'url': reverse('core:topictagruleset_list'), 'label': 'Topic Tag Rule Sets'})
            b.append({'url': reverse('core:topictagruleset_detail', kwargs={'id': self.rule.rule_set.id}),
                      'label': 'Rule Set {}'.format(self.rule.rule_set.name or self.rule.rule_set.id)})
            b.append({'label': 'Rule {}'.format(self.rule.name or self.rule.id)})
            return b
        return super().get_breadcrumbs(context)

    def post(self, request, *args, **kwargs):
        bacnet_prefix = request.POST.get('bacnet_prefix')
        if bacnet_prefix:
            self.request.session["topic_filter"] = bacnet_prefix
        return HttpResponseRedirect(reverse('core:topic_list'))


topic_list_view = TopicListView.as_view()


@login_required()
@require_POST
def topic_list_table(request):
    qs = Topic.objects.all()

    select_not_mapped_topics = request.POST.get('select_not_mapped_topics')
    if select_not_mapped_topics:
        # only list topics where there is no related data point
        # because those are 2 different DB need to get all the data points
        # where topic is non null and remove those topics
        # note: cast topic into entity_id as raw query must have the model PK
        r = PointView.objects.raw("SELECT DISTINCT(topic) as entity_id FROM {}".format(PointView._meta.db_table))
        qs = qs.exclude(topic__in=[p.entity_id for p in r])

    n = 0
    filters_count = request.POST.get('filters_count')
    if filters_count:
        n = int(filters_count)

    q_filters = []
    for i in range(n):
        filter_field = request.POST.get('n' + str(i))
        filter_type = request.POST.get('t' + str(i))
        if filter_type:
            filter_value = request.POST.get('f' + str(i))
            q_filters.append((filter_field, filter_type, filter_value))
    qs = utils.apply_filters_to_queryset(qs, q_filters)

    rc = RequestConfig(request, paginate={'per_page': 15})
    table = TopicTable(qs, orderable=True, order_by='topic')
    table = rc.configure(table)
    return HttpResponse(table.as_html(request))


@login_required()
@api_view(['GET', 'POST'])
def tag_topics(request):
    data = request.data
    logger.info('tag_topics: with %s', data)

    tags = data.get('tags')
    topics = data.get('topics')
    select_all = data.get('select_all')
    filters = data.get('filters')
    snmt = data.get('select_not_mapped_topics')

    if not tags:
        return JsonResponse({'errors': 'No Tags given'})
    if not topics and not select_all:
        return JsonResponse({'errors': 'No Topics selected'})

    # store a dict of topic -> data_point.entity_id
    updated = utils.tag_topics(filters, tags, select_all=select_all, topics=topics, select_not_mapped_topics=snmt)
    if not updated:
        return JsonResponse({'errors': 'No Topic matched the given filters.'})
    return JsonResponse({'success': 1, 'updated': updated, 'tags': tags})


@login_required()
@api_view(['GET', 'POST', 'DELETE'])
def topic_rules(request):
    data = request.data
    rule_set_id = data.get('rule_set_id')
    success = 1
    if request.method == 'DELETE':
        rule_id = data.get('rule_id')
        if rule_id:
            try:
                rule = TopicTagRule.objects.get(id=rule_id)
                rule.delete()
                return JsonResponse({'success': 1})
            except TopicTagRule.DoesNotExist:
                return JsonResponse({'error': 'Rule not found: {}'.format(rule_id)}, status=404)
        elif rule_set_id:
            try:
                rule = TopicTagRuleSet.objects.get(id=rule_set_id)
                rule.delete()
                return JsonResponse({'success': 1})
            except TopicTagRuleSet.DoesNotExist:
                return JsonResponse({'error': 'Rule Set not found: {}'.format(rule_set_id)}, status=404)

        else:
            return JsonResponse({'error': 'Rule or Rule Set ID required'})

    elif request.method == 'POST':
        # save the given rule
        rule_id = data.get('rule_id')
        rule = None
        if rule_id:
            # update the given rule
            try:
                rule = TopicTagRule.objects.get(id=rule_id)
            except TopicTagRule.DoesNotExist:
                return JsonResponse({'error': 'Rule not found: {}'.format(rule_id)}, status=404)
        rule_set_name = data.get('rule_set_name')
        name = data.get('name')
        if not name:
            return JsonResponse({'errors': 'Rule Name is required.'})
        filters = data.get('filters') or []
        tags = data.get('tags') or []
        logging.info('topic_rule save filters: %s', filters)
        logging.info('topic_rule save tags: %s', tags)
        # check if the rule set exists, dont allow multiple rulesets with same name
        if 'new' == rule_set_id:
            if not rule_set_name:
                return JsonResponse({'errors': 'RuleSet Name is required.'})

            try:
                rule_set = TopicTagRuleSet.objects.get(name=rule_set_name)
                if rule_set:
                    return JsonResponse({'errors': 'RuleSet "{}" already exists.'.format(rule_set_name)})
            except TopicTagRuleSet.DoesNotExist:
                rule_set = TopicTagRuleSet(name=rule_set_name)
                rule_set.save()

        else:
            if not rule_set_id and not rule_set_name:
                return JsonResponse({'errors': 'Please select a RuleSet.'})
            try:
                if rule_set_id:
                    rule_set = TopicTagRuleSet.objects.get(id=rule_set_id)
                elif rule_set_name:
                    rule_set = TopicTagRuleSet.objects.get(name=rule_set_name)
            except TopicTagRuleSet.DoesNotExist:
                return JsonResponse({'errors': 'RuleSet "{}" not found.'.format(rule_set_id)})

        # we have a valid rule_set
        rule_set_id = rule_set.id
        # check if the rule set already include a rule with the given name
        # dont allow multiple rules with same name in a set
        success = 'created'
        if not rule:
            try:
                rule = TopicTagRule.objects.get(name=name, rule_set=rule_set)
                if rule:
                    err = 'Rule "{}" already exists in that rule set, please choose a different name.'.format(name)
                    return JsonResponse({'errors': err})
            except TopicTagRule.DoesNotExist:
                rule = TopicTagRule()
        else:
            success = 'updated'
        rule.name = name
        rule.filters = filters
        rule.tags = tags
        rule.rule_set = rule_set
        rule_action = data.get('rule_action')
        rule_action_delete = data.get('rule_action_delete')
        rule_action_fields = data.get('rule_action_fields')
        if rule_action_delete:
            rule.action = None
            rule.action_fields = None
        elif rule_action:
            rule.action = rule_action
            if rule_action_fields:
                rule.action_fields = rule_action_fields

        rule.save()
        # return success
        return JsonResponse({'success': success,
                             'rule': {
                                'name': rule.name,
                                'id': rule.id,
                                'filters': rule.filters,
                                'tags': rule.tags},
                             'rule_set': {
                                'id': rule.rule_set.id,
                                'name': rule.rule_set.name
                             }})

    # return list of saved rules
    if rule_set_id:
        qs = TopicTagRule.objects.filter(rule_set=rule_set_id)
    else:
        qs = TopicTagRuleSet.objects.all()

    rules = list(qs.values())
    return JsonResponse({'success': 1, 'rules': rules})


class TopicTagRuleSetBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:topictagruleset_list'), 'label': 'Topic Tag Rule Sets'})
        if context.get('object'):
            b.append({'label': 'Rule Set {}'.format(context['object'].name or context['object'].id)})
        return b


class TopicTagRuleSetListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = TopicTagRuleSet
    table_class = TopicTagRuleSetTable
    filterset_class = TopicTagRuleSetFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/topictagruleset_list.html'


topictagruleset_list_view = TopicTagRuleSetListView.as_view()


class TopicTagRuleSetExportView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = TopicTagRuleSet
    table_class = TopicTagRuleSetExportTable
    template_name = 'core/topictagruleset_export.html'

    def post(self, request, *args, **kwargs):
        cb = request.POST.getlist('cb')
        response = HttpResponse(content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename="TopicTagRuleSets.json"'

        output = StringIO()
        tag_rule_sets = {"tag_rule_sets": []}

        if cb:
            for rule_set_id in cb:
                try:
                    rule_set = TopicTagRuleSet.objects.get(id=rule_set_id)
                except TopicTagRuleSet.DoesNotExist:
                    pass
                else:
                    tag_rule_set = {"name": rule_set.name, "rules": []}
                    rules = TopicTagRule.objects.filter(rule_set=rule_set_id)
                    if rules:
                        for rule in rules:
                            rule_item = {"name": rule.name, "filters": rule.filters, "tags": rule.tags}
                            tag_rule_set["rules"].append(rule_item)

                    tag_rule_sets["tag_rule_sets"].append(tag_rule_set)

        json_string = json.dumps(tag_rule_sets, indent=4, sort_keys=True)
        output.write(json_string)
        response.write(output.getvalue())

        return response


topictagruleset_export_view = TopicTagRuleSetExportView.as_view()


class TopicTagRuleSetImportView(LoginRequiredMixin, WithBreadcrumbsMixin, FormView):
    model = TopicTagRuleSet
    template_name = 'core/topictagruleset_import.html'
    form_class = TopicTagRuleSetImportForm

    def get_success_url(self):
        return reverse("core:topictagruleset_list")

    def form_valid(self, form):
        form_results = form.save()

        # an error message
        import_errors = form_results.get('import_errors')
        # the imported rule sets
        success_rule_sets = form_results.get('success_rule_sets')

        if import_errors:
            messages.error(self.request, import_errors)
            return self.form_invalid(form)
        elif success_rule_sets:
            messages.success(self.request, 'Successfully imported {} rule sets.'.format(", ".join(success_rule_sets)))
        else:
            messages.error(self.request, "Rule sets list to import is empty.")
            return self.form_invalid(form)

        return super().form_valid(form)


topictagruleset_import_view = TopicTagRuleSetImportView.as_view()


class TopicTagRuleSetCreateView(LoginRequiredMixin, TopicTagRuleSetBCMixin, CreateView):
    model = TopicTagRuleSet
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'core/topictagruleset_edit.html'
    form_class = TopicTagRuleSetCreateForm


topictagruleset_create_view = TopicTagRuleSetCreateView.as_view()


class TopicTagRuleSetDetailView(LoginRequiredMixin, SingleTableMixin, TopicTagRuleSetBCMixin, FilterView):
    model = TopicTagRule
    template_name = 'core/topictagruleset_detail.html'
    table_class = TopicTagRuleTable
    filterset_class = TopicTagRuleFilter

    def get_queryset(self):
        qs = super().get_queryset()
        rule_set = get_object_or_404(TopicTagRuleSet, id=self.kwargs['id'])
        return qs.filter(rule_set=rule_set)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = get_object_or_404(TopicTagRuleSet, id=self.kwargs['id'])
        return context


topictagruleset_detail_view = TopicTagRuleSetDetailView.as_view()


class TopicTagRuleCreateView(LoginRequiredMixin, TopicTagRuleSetBCMixin, CreateView):
    model = TopicTagRule
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'core/topictagrule_edit.html'
    form_class = TopicTagRuleCreateForm

    def get_initial(self):
        return {'rule_set': self.kwargs.get('id')}


topictagrule_create_view = TopicTagRuleCreateView.as_view()


class TopicTagRuleRunView(LoginRequiredMixin, TopicTagRuleSetBCMixin, FormView):
    form_class = TopicTagRuleSetRunForm
    template_name = 'core/topictagruleset_run.html'

    def get_initial(self):
        logging.info('get_initial: %s', self.kwargs)
        initials = {'ruleset_id': self.kwargs.get('id')}
        if self.request.GET and 'topic_filter' in self.request.GET:
            initials['topic_filter'] = self.request.GET['topic_filter']
        return initials

    def get_form_kwargs(self):
        args = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            # first change the data to be a copy of POST
            args.update({
                'data': self.request.POST.copy(),
            })
            # add the URL given ID to the params for the Form
            if 'id' in self.kwargs and 'ruleset_id' not in args['data']:
                args['data'].update({'ruleset_id': self.kwargs.get('id')})
        return args

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'id' in self.kwargs:
            rule_set = get_object_or_404(TopicTagRuleSet, id=self.kwargs['id'])
            context['rule_set'] = rule_set
            context['object'] = rule_set
        return context

    def form_invalid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        errors = {}
        for field in form:
            for error in field.errors:
                errors[field.name] = error

        if errors:
            context['errors'] = errors
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            updated_set, updated_entities, preview_type, updated_tags, removed_tags, diff_format = form.save()
            if preview_type:
                if diff_format:
                    report_rows, report_header = utils.tag_rulesets_run_report_diff(
                                                       updated_entities, updated_tags, removed_tags)
                    if not report_rows:
                        messages.error(self.request, "Preview diff is empty")
                        context = self.get_context_data(**kwargs)
                        return self.render_to_response(context)
                    else:
                        if preview_type == 'preview_csv':
                            response = HttpResponse(content_type='text/csv')
                            response['Content-Disposition'] = 'attachment; filename="TagRulesetsPreviewDiffReport.csv"'

                            writer = csv.writer(response)
                            if report_header:
                                writer.writerow(report_header)
                                if report_rows:
                                    for row in report_rows:
                                        writer.writerow(row)
                            else:
                                writer.writerow([''])

                        else:
                            temp = tempfile.NamedTemporaryFile(delete=False)
                            temp.close()
                            with open(temp.name, 'w') as file_csv:
                                writer = csv.writer(file_csv)
                                if report_header:
                                    writer.writerow(report_header)
                                    if report_rows:
                                        for row in report_rows:
                                            writer.writerow(row)

                                    response = HttpResponseRedirect(
                                        reverse("core:report_preview_csv") + '?file=' + temp.name
                                        + '&name=Tag Rulesets Preview Diff Report')
                                else:
                                    writer.writerow([''])

                        return response
                else:
                    report_rows, report_header = utils.tag_rulesets_run_report(updated_entities)
                    if preview_type == 'preview_csv':
                        response = HttpResponse(content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="TagRulesetsPreviewReport.csv"'

                        writer = csv.writer(response)
                        if report_header:
                            writer.writerow(report_header)
                            if report_rows:
                                for row in report_rows:
                                    writer.writerow(row)
                        else:
                            writer.writerow([''])

                    else:
                        temp = tempfile.NamedTemporaryFile(delete=False)
                        temp.close()
                        with open(temp.name, 'w') as file_csv:
                            writer = csv.writer(file_csv)
                            if report_header:
                                writer.writerow(report_header)
                                if report_rows:
                                    for row in report_rows:
                                        updated_tag = updated_tags.get(row[0])
                                        removed_tag = removed_tags.get(row[0])
                                        if updated_tag or removed_tag:
                                            if not updated_tag:
                                                updated_tag = {}
                                            if not removed_tag:
                                                removed_tag = {}
                                            row_new = []
                                            for i, value in enumerate(row):
                                                header = report_header[i]
                                                value_updated = updated_tag.get(header)
                                                value_removed = removed_tag.get(header)
                                                if value_updated:
                                                    value += "::$$updated$$"
                                                elif value_removed:
                                                    value = value_removed + "::$$removed$$"
                                                row_new.append(value)

                                            writer.writerow(row_new)
                                        else:
                                            writer.writerow(row)
                            else:
                                writer.writerow([''])

                        response = HttpResponseRedirect(
                            reverse("core:report_preview_csv") + '?file=' + temp.name
                            + '&name=Tag Rulesets Preview Report')

                    return response
            else:
                return JsonResponse({'success': 1, 'updated': len(updated_set)})

        else:
            return self.form_invalid(form, **kwargs)


topictagrule_run_view = TopicTagRuleRunView.as_view()


class TopicImportView(LoginRequiredMixin, WithBreadcrumbsMixin, FormView):
    model = Topic
    template_name = 'core/topic_import.html'
    form_class = TopicImportForm

    def get_success_url(self):
        return reverse("core:topic_list")

    def get_context_data(self, **kwargs):
        context = super(TopicImportView, self).get_context_data(**kwargs)
        sites_number = SiteView.count()
        if not sites_number:
            context["no_sites"] = True
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form_results = form.save()

            import_errors = form_results.get('import_errors')
            import_success = form_results.get('import_success')
            if import_errors:
                messages.error(self.request, import_errors)
            if import_success:
                messages.success(self.request, import_success)

            return self.form_valid(form)
        else:
            messages.error(self.request, 'Cannot import data')
            return self.form_invalid(form)


topic_import_view = TopicImportView.as_view()


class TagImportView(LoginRequiredMixin, WithBreadcrumbsMixin, FormView):
    model = Topic
    template_name = 'core/tag_import.html'
    form_class = TagImportForm

    def get_success_url(self):
        return reverse("core:topic_list")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form_results = form.save()

            import_errors = form_results.get('import_errors')
            import_success = form_results.get('import_success')
            if import_errors:
                messages.error(self.request, import_errors)
            elif import_success:
                messages.success(self.request, import_success)

            return self.form_valid(form)
        else:
            messages.error(self.request, 'Source file is empty')
            return self.form_invalid(form)


tag_import_view = TagImportView.as_view()


class TopicExportView(LoginRequiredMixin, WithBreadcrumbsMixin, FormView):
    model = Topic
    template_name = 'core/topic_export.html'
    form_class = TopicExportForm

    def get_context_data(self, **kwargs):
        context = super(TopicExportView, self).get_context_data(**kwargs)
        sites_number = SiteView.count()
        if not sites_number:
            context["no_sites"] = True

        context['site_id'] = None
        if 'site' in self.kwargs:
            context['site_id'] = self.kwargs['site']
            context['back_url'] = reverse('core:site_detail', kwargs={'site': self.kwargs['site']})
            try:
                context['current_site'] = SiteView.objects.get(entity_id=self.kwargs['site'])
            except SiteView.DoesNotExist:
                pass

            if self.request.GET and 'bacnet_prefix' in self.request.GET:
                context['current_prefix'] = self.request.GET['bacnet_prefix']

        else:
            context['back_url'] = reverse('core:topic_list')
            context['sites_list'] = SiteView.get_site_choices()
            if context['sites_list']:
                site_id = context['sites_list'][0]['id']
                if site_id:
                    context['site_id'] = site_id

        return context

    def form_valid(self, form):
        return self.get_config_zip(self.get_context_data(form=form))

    def set_bacnet_config_field(self, config_file_json, kv_tags, tag):
        if kv_tags.get(tag):
            tag_description = utils.get_tag_description(
                tag, default=tag.replace(Tag.bacnet_tag_prefix, ''))
            config_file_json[tag_description] = kv_tags.get(tag)

    def get_config_zip(self, context, **response_kwargs):
        device_prefix = context["form"].cleaned_data['device_prefix']
        only_with_trending = context["form"].cleaned_data['only_with_trending']
        response = HttpResponse(content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=bacnet_config.zip"

        trendings = Entity.objects.filter(kv_tags__bacnet_prefix=device_prefix).values(
                    'kv_tags__interval').annotate(dcount=Count('kv_tags__interval'))

        files_list = []

        if trendings:
            for tr in trendings:
                config_file_json = {'driver_config': {}}
                trending_interval = None
                csv_file_name = "_Interval_Not_Set.csv"
                config_file_name = "_Interval_Not_Set.config"
                if tr['kv_tags__interval']:
                    trending_interval = tr['kv_tags__interval']
                    csv_file_name = '_Interval_' + trending_interval + ".csv"
                    config_file_name = '_Interval_' + trending_interval + ".config"

                if trending_interval is None and only_with_trending:
                    continue

                file_item = {'csv_file_name': csv_file_name, 'config_file_name': config_file_name}

                rows = Entity.objects.filter(
                       kv_tags__bacnet_prefix=device_prefix,
                       m_tags__contains=['point'],
                       kv_tags__interval=trending_interval)
                if rows:
                    # get config file tags from first row
                    kv_tags = rows[0].kv_tags
                    if kv_tags:
                        self.set_bacnet_config_field(config_file_json['driver_config'], kv_tags,
                                                     Tag.bacnet_tag_prefix + 'device_address')
                        self.set_bacnet_config_field(config_file_json['driver_config'], kv_tags,
                                                     Tag.bacnet_tag_prefix + 'device_id')
                        self.set_bacnet_config_field(config_file_json, kv_tags,
                                                     Tag.bacnet_tag_prefix + 'driver_type')
                        self.set_bacnet_config_field(config_file_json, kv_tags,
                                                     Tag.bacnet_tag_prefix + 'registry_config')
                        self.set_bacnet_config_field(config_file_json, kv_tags,
                                                     Tag.bacnet_tag_prefix + 'timezone')

                    header, bacnet_data = utils.get_bacnet_trending_data(rows)

                registry_config = config_file_json.get("registry_config")
                registry_config_new = None
                if registry_config:
                    parse_result = urlparse(registry_config)
                    if parse_result and parse_result.path:
                        arr = parse_result.path.split('/')
                        if arr:
                            arr[-1] = csv_file_name
                            path = '/'.join(arr)
                            parse_result = parse_result._replace(path=path)
                            registry_config_new = parse_result.geturl()

                if registry_config_new:
                    config_file_json["registry_config"] = registry_config_new
                else:
                    config_file_json["registry_config"] = "config://" + csv_file_name
                if trending_interval:
                    config_file_json["interval"] = trending_interval
                else:
                    if "interval" in config_file_json:
                        del config_file_json["interval"]

                file_item["config_file"] = json.dumps(config_file_json, indent=4, sort_keys=True)

                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(header)
                for row in bacnet_data:
                    writer.writerow(row)

                file_item['csv_file'] = output.getvalue()

                output.close()

                files_list.append(file_item)

        if files_list:
            in_memory = BytesIO()
            zip = ZipFile(in_memory, "a")
            for file_item in files_list:
                zip.writestr(file_item['config_file_name'], file_item['config_file'])
                zip.writestr(file_item['csv_file_name'], file_item['csv_file'])

            # fix for Linux zip files read in Windows
            for file in zip.filelist:
                file.create_system = 0

            zip.close()
            in_memory.seek(0)
            response.write(in_memory.read())

        return response

    def get_form_kwargs(self):
        kwargs = super(TopicExportView, self).get_form_kwargs()
        site_id = None
        if 'site' in self.kwargs:
            site_id = self.kwargs['site']
        kwargs.update({'site_id': site_id})
        return kwargs


topic_export_view = TopicExportView.as_view()


class TopicSetupView(LoginRequiredMixin, WithBreadcrumbsMixin, DetailView):
    model = Topic
    slug_field = "topic"
    slug_url_kwarg = "topic"
    template_name = 'core/topic_setup.html'

    def get_context_data(self, **kwargs):
        context = super(TopicSetupView, self).get_context_data(**kwargs)
        # add the parent Site (optional)
        try:
            context['site'] = SiteView.objects.get(object_id=context['object'].site_id)
        except SiteView.DoesNotExist:
            pass
        try:
            context['equipment'] = EquipmentView.objects.get(object_id=context['object'].equipment_id)
        except EquipmentView.DoesNotExist:
            pass
        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:topic_list'), 'label': 'Topics'})
        if context.get('object'):
            b.append({'label': context['object'].topic})
        return b


topic_setup_view = TopicSetupView.as_view()


@login_required()
def equipment_data_points_table(request, equip):
    logger.info('equipment_data_points_table: equip = %s', equip)
    equipment = get_object_or_404(EquipmentView, entity_id=equip)
    data = PointView.objects.filter(equipment_id=equipment.object_id).order_by('description')
    d2 = utils.add_current_values(data)
    table = PointTable(d2, orderable=False)
    return HttpResponse(table.as_html(request))


class EquipmentListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, FilterView):
    model = EquipmentView
    table_class = EquipmentTable
    filterset_class = EquipmentFilter
    table_pagination = {'per_page': 15}
    template_name = 'core/equipment_list.html'


equipment_list_view = EquipmentListView.as_view()


class EquipmentListJsonView(LoginRequiredMixin, ListView):
    model = EquipmentView

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
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
            except Exception:
                pass
        b.append({'label': 'Equipment {}'.format(context['object'].description)})
        return b

    def get_context_data(self, **kwargs):
        context = super(EquipmentDetailView, self).get_context_data(**kwargs)
        context['grafana_url'] = settings.GRAFANA_BASE_URL + "/d/"
        context['grafana_snapshot_url'] = settings.GRAFANA_BASE_URL + "/dashboard/snapshot/"
        # add the parent Site (optional)
        try:
            context['site'] = SiteView.objects.get(object_id=context['object'].site_id)
        except SiteView.DoesNotExist:
            pass

        context['data_points'] = PointView.objects.filter(equipment_id=context['object'].object_id).count()
        is_ahu = 0
        if 'ahu' in context['object'].m_tags:
            is_ahu = 1

        context['is_ahu'] = is_ahu

        return context


equipment_detail_view = EquipmentDetailView.as_view()


class EquipmentSiteDetailView(EquipmentDetailView):
    def get_context_data(self, **kwargs):
        context = super(EquipmentSiteDetailView, self).get_context_data(**kwargs)
        # add the parent Site
        context['site'] = get_object_or_404(SiteView, entity_id=self.kwargs['site'])
        return context


equipment_site_detail_view = EquipmentSiteDetailView.as_view()


class WithPointBreadcrumbsMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        if context.get('site'):
            b.append({'url': reverse('core:site_list'), 'label': 'Sites'})
            b.append({'url': reverse('core:site_detail', kwargs={'site': context['site'].entity_id}),
                      'label': 'Site {}'.format(context['site'].description)})
            if context.get('equipment'):
                b.append({'url': reverse('core:site_equipment_detail', kwargs={
                            'site': context['site'].entity_id,
                            'equip': context['equipment'].entity_id}),
                          'label': 'Equipment {}'.format(context['equipment'].description)})
        else:
            b.append({'url': reverse('core:entity_list'), 'label': 'Entities'})

        if context.get('object'):
            b.append({'label': 'Data Point {}'.format(context['object'].description)})
        return b


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

        # add the parent Equipment
        context['equipment'] = get_object_or_404(EquipmentView, entity_id=self.kwargs['equip'])

        if context['object']:
            context['charts'] = utils.charts_for_points([context['object']])

        return context

    def get_object(self, **kwargs):
        p = super(EquipmentPointDetailView, self).get_object(**kwargs)
        return utils.add_current_values([p])[0]


equipment_point_detail_view = EquipmentPointDetailView.as_view()


class PointDetailView(LoginRequiredMixin, WithFilesAndNotesAndTagsMixin, WithPointBreadcrumbsMixin, DetailView):
    model = PointView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/point_detail.html'
    entity_id_field = 'entity_id'

    def get_context_data(self, **kwargs):
        context = super(PointDetailView, self).get_context_data(**kwargs)
        context['grafana_url'] = settings.GRAFANA_BASE_URL + "/d/"
        # add the parent Site (optional)
        try:
            context['site'] = SiteView.objects.get(object_id=context['object'].site_id)
        except SiteView.DoesNotExist:
            pass

        # add the parent Equipment (optional)
        try:
            context['equipment'] = EquipmentView.objects.get(object_id=context['object'].equipment_id)
        except EquipmentView.DoesNotExist:
            pass

        if context['object']:
            context['charts'] = utils.charts_for_points([context['object']])

        return context

    def get_object(self, **kwargs):
        p = super(PointDetailView, self).get_object(**kwargs)
        return utils.add_current_values([p])[0]


point_detail_view = PointDetailView.as_view()


def point_data_json(request, point, site=None, equip=None):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    resolution = request.GET.get('res')
    trange = request.GET.get('range')
    p = PointView.objects.get(entity_id=point)
    if p:
        return JsonResponse({'values': utils.get_point_values(p, date_trunc=resolution, trange=trange)})
    else:
        logger.warning('No point found with entity_id = %s', point)
        return JsonResponse({'error': 'Point data not found {} : {}'.format(equip, point)}, status=404)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


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
    labels = []
    values = []
    logger.info('site_pie_chart_data_json pie: %s', pie)
    for k, v in pie.items():
        labels.append(k)
        values.append(v)
    return JsonResponse({'values': values, 'labels': labels})


@login_required()
def point_data_csv(request, point, site=None, equip=None):
    resolution = request.GET.get('res')
    trange = request.GET.get('range')
    p = get_object_or_404(PointView, entity_id=point)
    site = p.kv_tags['siteRef']
    equip = p.kv_tags['equipRef']
    rows = utils.get_point_values(p, date_trunc=resolution, trange=trange)
    # limit output
    if len(rows) > 65535:
        del rows[:65535]

    last_timestamp = "0"
    if len(rows) > 0:
        last_timestamp = rows[:-1][0][0]

    value_title = 'value'
    if p.unit:
        value_title += ' ' + p.unit
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (writer.writerow([datetime.utcfromtimestamp(int(row[0]) / 1000).strftime('%Y-%m-%d %H:%M:%S'), row[1]])
            for row in rows),
        content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}_{}_{}_{}.csv"'.format(
        site, equip, point, resolution or utils.DEFAULT_RES, trange or utils.DEFAULT_RANGE, last_timestamp)
    return response


@login_required()
def topic_report_tags_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="TopicsTagsReport.csv"'

    report_rows, report_header = utils.get_topics_tags_report()

    writer = csv.writer(response)
    if report_header:
        writer.writerow(report_header)
        if report_rows:
            for row in report_rows:
                writer.writerow(row)
    else:
        writer.writerow([''])

    return response


def _read_files(files, items, protect=False, parent=None):
    for file in files:
        d = {
            'id': file.id,
            'comments': file.comments,
            'owner': file.owner.username,
            'created': utils.format_date(file.created)
        }
        if file.uploaded_file_id:
            d['url'] = file.uploaded_file.url
            d['name'] = file.uploaded_file.original_filename
            d['size'] = file.uploaded_file.size
            if file.can_thumbnail:
                d['thumbnail_url'] = get_thumbnailer(file.uploaded_file)['xs_thumb'].url
        else:
            d['url'] = file.link
            d['name'] = file.link_name

        if protect:
            d['_protect'] = 1
        if parent:
            d['parent'] = parent
        items.append(d)


@login_required()
def entity_file_upload(request, entity_id):
    if request.method == 'GET':
        items = []
        model_id = utils.get_related_model_id(entity_id)
        if model_id:
            model = ModelView.objects.filter(object_id=model_id).values()[0]
            # note: those should be read only
            _read_files(EntityFile.objects.filter(entity_id=model['entity_id']), items, protect=True, parent=model)
        _read_files(EntityFile.objects.filter(entity_id=entity_id), items)
        return JsonResponse({'items': items})
    elif request.method == 'POST':
        if request.POST.get('update'):
            form = FileUpdateForm(request.POST)
            if form.is_valid():
                e = EntityFile.objects.get(id=form.cleaned_data['id'], entity_id=form.cleaned_data['entity_id'])
                e.comments = form.cleaned_data['comments']
                e.save()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        elif request.POST.get('delete'):
            form = FileDeleteForm(request.POST)
            if form.is_valid():
                try:
                    e = EntityFile.objects.get(id=form.cleaned_data['id'], entity_id=form.cleaned_data['entity_id'])
                except EntityFile.DoesNotExist:
                    return JsonResponse({'errors': 'EntityFile not found {} : {}'.format(
                        form.cleaned_data['id'], form.cleaned_data['entity_id'])}, status=404)
                e.delete()

                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        else:
            form = FileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data['uploaded_file']
                file_obj = File(f, name=f.name)
                filer_file = FilerFile.objects.create(owner=request.user,
                                                      original_filename=f.name,
                                                      file=file_obj)
                e = EntityFile.objects.create(entity_id=form.cleaned_data['entity_id'],
                                              comments=form.cleaned_data['comments'],
                                              owner=request.user,
                                              uploaded_file=filer_file)
                # note try to make the thumbnail after upload, but catch errors since it may not be an image
                try:
                    thumb = get_thumbnailer(e.uploaded_file)['xs_thumb'].url
                    e.can_thumbnail = True
                    e.save()
                except Exception:
                    thumb = None
                return JsonResponse({'success': 1, 'results': [{
                    'id': e.id,
                    'comments': e.comments,
                    'owner': e.owner.username,
                    'created': utils.format_date(e.created),
                    'thumbnail_url': thumb,
                    'url': e.uploaded_file.url,
                    'name': e.uploaded_file.original_filename,
                    'size': e.uploaded_file.size,
                }]})
            else:
                return JsonResponse({'errors': form.errors})


def _read_notes(notes, items, protect=False, parent=None):
    for note in notes:
        d = {
            'id': note.id,
            'content': note.content,
            'owner': note.owner.username,
            'created': utils.format_date(note.created)
        }
        if protect:
            d['_protect'] = 1
        if parent:
            d['parent'] = parent
        items.append(d)


@login_required()
def entity_note(request, entity_id):
    if request.method == 'GET':
        items = []
        model_id = utils.get_related_model_id(entity_id)
        if model_id:
            model = ModelView.objects.filter(object_id=model_id).values()[0]
            # note: those should be read only
            _read_notes(EntityNote.objects.filter(entity_id=model['entity_id']), items, protect=True, parent=model)

        _read_notes(EntityNote.objects.filter(entity_id=entity_id), items)
        return JsonResponse({'items': items})
    elif request.method == 'POST':
        if request.POST.get('update'):
            form = EntityNoteUpdateForm(request.POST)
            if form.is_valid():
                try:
                    e = EntityNote.objects.get(id=form.cleaned_data['id'], entity_id=form.cleaned_data['entity_id'])
                except EntityNote.DoesNotExist:
                    return JsonResponse({'errors': 'EntityNote not found {} : {}'.format(
                        form.cleaned_data['id'], form.cleaned_data['entity_id'])}, status=404)
                e.content = form.cleaned_data['content']
                e.save()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        elif request.POST.get('delete'):
            form = EntityNoteDeleteForm(request.POST)
            if form.is_valid():
                EntityNote.objects.get(id=form.cleaned_data['id'], entity_id=form.cleaned_data['entity_id']).delete()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        else:
            form = EntityNoteForm(request.POST)
            if form.is_valid():
                e = form.save(commit=False)
                e.owner = request.user
                e.save()
                return JsonResponse({'success': 1, 'results': [{
                    'id': e.id,
                    'content': e.content,
                    'owner': e.owner.username,
                    'created': utils.format_date(e.created)
                }]})
            else:
                return JsonResponse({'errors': form.errors})


@require_POST
@login_required()
def entity_link(request, entity_id):
    if request.POST.get('update'):
        try:
            e = EntityFile.objects.get(id=request.POST.get('id'), entity_id=request.POST.get('entity_id'))
        except EntityFile.DoesNotExist:
            return JsonResponse({'errors': 'EntityFile not found {} : {}'.format(
                request.POST.get('id'), request.POST.get('entity_id'))}, status=404)
        form = EntityLinkForm(request.POST, instance=e)
    else:
        form = EntityLinkForm(request.POST)
    if form.is_valid():
        e = form.save(commit=False)
        e.owner = request.user
        e.save()
        return JsonResponse({'success': 1, 'results': [{
            'id': e.id,
            'comments': e.comments,
            'owner': e.owner.username,
            'url': e.link,
            'name': e.link_name,
            'created': utils.format_date(e.created)
        }]})
    else:
        return JsonResponse({'errors': form.errors})


def _read_tags(tags, items, protect=False, parent=None):
    for tag in tags:
        # special case: do not inherit the Model marker
        if protect and tag['tag'] in ['model', 'dis']:
            continue
        d = {
            'tag': tag['tag'],
            'details': tag['details'],
            'description': tag['description'],
        }
        for t in ['kind', 'value', 'slug']:
            if t in tag:
                d[t] = tag[t]
        if protect:
            d['_protect'] = 1
        if parent:
            d['parent'] = parent
        items.append(d)


@login_required()
def entity_tag(request, entity_id):
    if request.method == 'GET':
        items = []

        _read_tags(utils.get_tags_list_for_topic(entity_id), items)
        return JsonResponse({'items': items})
    elif request.method == 'POST':
        tag = request.POST.get('tag')
        value = request.POST.get('value')
        try:
            entity = Entity.objects.get(entity_id=entity_id)
        except Entity.DoesNotExist:
            return JsonResponse({'errors': 'Entity not found : {}'.format(entity_id)}, status=404)

        try:
            if request.POST.get('delete'):
                entity.remove_tag(tag)
                return JsonResponse({'success': 1})
            else:
                t = utils.get_tag(tag)
                if t:
                    # some basic validation
                    try:
                        t.valid_value(value)
                    except ValidationError as e:
                        return JsonResponse({'errors': {'value': [e.message]}})
                    entity.add_tag(tag, value)
                    t.value = value
                    logger.info('entity_tag: got tag %s', t)
                    ref = t.get_ref_entity()
                    logger.info('entity_tag: got tag ref %s', ref)
                    result = {
                        'tag': tag,
                        'description': t.description,
                        'kind': t.kind,
                        'value': value
                    }
                    if ref:
                        result['ref'] = ref.as_dict()
                        result['slug'] = ref.entity_id
                        if tag == 'modelRef':
                            model_obj = ModelView.objects.filter(entity_id=ref.entity_id).values().first()
                            entity.add_tags_from_model(model_obj)

                    return JsonResponse({'success': 1, 'results': [result]})
                else:
                    return JsonResponse({'errors': 'Tag not found : {}'.format(tag)}, status=404)

        except Exception:
            logger.exception('Could not set the tag')
            return JsonResponse({'errors': 'Could not perform the operation'})


@require_POST
@login_required()
def topic_assoc(request, topic):
    form = TopicAssocForm(request.POST)
    if form.is_valid():
        try:
            Topic.objects.get(topic=topic)
        except Topic.DoesNotExist:
            return JsonResponse({'errors': 'Topic not found : {}'.format(topic)}, status=404)
        site_id = form.cleaned_data['site_id']
        equipment_id = form.cleaned_data['equipment_id']
        site = None
        site_entity_id = None
        equipment = None
        equipment_entity_id = None
        # can use existing or create a new Site
        if request.POST.get('_new_site'):
            site_name = site_id
            site_id = utils.make_random_id(site_name)
            logger.info('topic_assoc check for NOT existing Site : %s', site_id)
            try:
                s = SiteView.objects.get(object_id=site_id)
                site_entity_id = s.entity_id
                return JsonResponse({
                    'errors': {'site_id': ['Site already exists : {}'.format(site_id)]}})
            except SiteView.DoesNotExist:
                site = Entity(entity_id=slugify(site_id))
                site.add_tag('site', commit=False)
                site.add_tag('dis', site_name, commit=False)
                site.add_tag('id', site_id, commit=False)
        else:
            logger.info('topic_assoc check for MUST exist Site : %s', site_id)
            try:
                s = SiteView.objects.get(object_id=site_id)
                site_entity_id = s.entity_id
            except SiteView.DoesNotExist:
                return JsonResponse({
                    'errors': {'site_id': ['Site not found : {}'.format(site_id)]}})
        if request.POST.get('_new_equipment'):
            equipment_name = equipment_id
            equipment_id = utils.make_random_id(equipment_name)
            logger.info('topic_assoc check for NOT existing Equipment : %s', equipment_id)
            try:
                eq = EquipmentView.objects.get(object_id=equipment_id)
                equipment_entity_id = eq.entity_id
                return JsonResponse({
                    'errors': {'equipment_id': ['Equipment already exists : {}'.format(equipment_id)]}})
            except EquipmentView.DoesNotExist:
                equipment = Entity(entity_id=slugify(equipment_id))
                equipment.add_tag('equip', commit=False)
                equipment.add_tag('siteRef', site_id, commit=False)
                equipment.add_tag('dis', equipment_name, commit=False)
                equipment.add_tag('id', equipment_id, commit=False)
        else:
            logger.info('topic_assoc check for MUST exist Equipment : %s', equipment_id)
            try:
                eq = EquipmentView.objects.get(object_id=equipment_id, site_id=site_id)
                equipment_entity_id = eq.entity_id
            except EquipmentView.DoesNotExist:
                return JsonResponse({
                    'errors': {'equipment_id': ['Equipment not found : {}'.format(equipment_id)]}})
        # all good
        data_point_name = form.cleaned_data['data_point_name']
        entity_id = slugify(data_point_name)

        try:
            Entity.objects.get(kv_tags__id=data_point_name)
            return JsonResponse({
                'errors': {'data_point_name': ['Entity already exists with ID : {}'.format(data_point_name)]}})
        except Entity.DoesNotExist:
            pass

        if site:
            logger.info('topic_assoc create Site : %s', site)
            site_entity_id = site.entity_id
            site.save()
        if equipment:
            logger.info('topic_assoc create Equipment : %s', equipment)
            equipment_entity_id = equipment.entity_id
            equipment.save()
        e = Entity(entity_id=entity_id, topic=topic)
        e.add_tag('point', commit=False)
        e.add_tag('his', commit=False)
        e.add_tag('id', data_point_name, commit=False)
        e.add_tag('dis', data_point_name, commit=False)
        e.add_tag('siteRef', site_id, commit=False)
        e.add_tag('equipRef', equipment_id, commit=False)
        e.save()
        # create grafana dashboard
        r = utils.create_grafana_dashboard(topic)
        if r:
            result = r.json()
            if r.status_code == 200:
                if result["uid"]:
                    e.dashboard_uid = result["uid"]
                    e.save()
                    logger.error('create_grafana_dashboard created dashboard uid : %s', result["uid"])
                else:
                    logger.error('create_grafana_dashboard did not return an uid : %s', result)
            else:
                logger.error('create_grafana_dashboard request status invalid : %s', r.status_code)

        return JsonResponse({
            'success': 1,
            'site': {'slug': site_entity_id, 'id': site_id},
            'equipment': {'slug': equipment_entity_id, 'id': equipment_id},
            'point': {'slug': entity_id, 'id': data_point_name}
        })
    else:
        return JsonResponse({'errors': form.errors})


class BacnetPrefixJsonView(LoginRequiredMixin, ListView):
    model = PointView

    def render_to_response(self, context, **response_kwargs):
        site_id = self.kwargs['site']
        data = []
        if site_id:
            site = None
            try:
                site = SiteView.objects.get(entity_id=site_id)
            except SiteView.DoesNotExist:
                logger.error('Cannot get site by id : %s', site_id)
            if site:
                bacnet_configs = PointView.objects.filter(site_id=site.object_id).exclude(
                    kv_tags__bacnet_prefix__isnull=True).exclude(
                    kv_tags__bacnet_prefix__exact='').values('kv_tags__bacnet_prefix',
                                                             'kv_tags__bacnet_device_id').annotate(
                                                             dcount=Count('kv_tags__bacnet_prefix'))
                if bacnet_configs:
                    for bacnet_config in bacnet_configs:
                        item = {'id': bacnet_config['kv_tags__bacnet_prefix'],
                                'prefix': bacnet_config['kv_tags__bacnet_prefix']}
                        data.append(item)

        return JsonResponse({'items': data})


bacnet_prefix_list_json_view = BacnetPrefixJsonView.as_view()


@require_POST
@login_required()
def equipment_dashboard(request, equip):
    result = {}
    try:
        entity = Entity.objects.get(entity_id=equip)
    except EquipmentView.DoesNotExist:
        result = {'errors': 'Equipment not found : {}'.format(equip)}
    else:
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


class ReportPreviewCsvView(LoginRequiredMixin, WithBreadcrumbsMixin, TemplateView):
    model = Topic
    template_name = 'core/report_preview_csv.html'

    def get_context_data(self, **kwargs):
        context = super(ReportPreviewCsvView, self).get_context_data(**kwargs)
        file_name = self.request.GET.get('file')
        report_name = self.request.GET.get('name')
        if file_name:
            report_rows = []
            report_header = []
            try:
                with open(file_name, 'rb') as csv_file:
                    f = TextIOWrapper(csv_file, encoding='utf-8')
                    reader = csv.reader(f)
                    first_row = True
                    for row in reader:
                        if first_row:
                            report_header.append(row)
                            first_row = False
                        else:
                            row_new = []
                            for value in row:
                                item = {'value': value}
                                if '::$$updated$$' in value:
                                    item['op'] = 'updated'
                                    item['value'] = value.replace('::$$updated$$', '')
                                elif '::$$removed$$' in value:
                                    item['op'] = 'removed'
                                    item['value'] = value.replace('::$$removed$$', '')

                                if 'type:MARKER' in value:
                                    item['value'] = 'X'

                                row_new.append(item)
                            report_rows.append(row_new)
            except OSError:
                messages.error(self.request, 'Cannot open repot file')
            else:
                os.remove(file_name)

            context['report_name'] = report_name
            context['report_header'] = report_header
            context['report_rows'] = report_rows

        return context


report_preview_csv_view = ReportPreviewCsvView.as_view()
