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
import logging
import json
import tempfile
import os
from io import BytesIO
from io import StringIO
from io import TextIOWrapper
from urllib.parse import urlparse
from zipfile import ZipFile

from .common import WithBreadcrumbsMixin
from .. import utils
from ..models import Entity, EntityPermission
from ..models import EquipmentView
from ..models import Tag
from ..models import Topic
from ..models import TopicTagRule
from ..models import TopicTagRuleSet
from ..models import SiteView
from ..forms.topic import TopicExportForm
from ..forms.topic import TopicImportForm
from ..forms.topic import TopicAssocForm
from ..forms.topic import TopicTagRuleSetImportForm
from ..forms.topic import TopicTagRuleSetCreateForm
from ..forms.topic import TopicTagRuleCreateForm
from ..forms.topic import TopicTagRuleSetRunForm
from ..forms.topic import TopicTagRuleRunForm

from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connections
from django.db import OperationalError
from django.db.models import Q
from django.db.models import Count
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2 import CheckBoxColumn
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.config import RequestConfig
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin
from rest_framework.decorators import api_view

logger = logging.getLogger(__name__)


class TopicTable(Table):
    cb = CheckBoxColumn(accessor='topic')
    topic = Column()
    bacnet_objectName = Column(accessor='topic', verbose_name='Object Name', default='')
    bacnet_presentValue = Column(accessor='topic', verbose_name='Present Value', default='')
    bacnet_units = Column(accessor='topic', verbose_name='Units', default='')

    button = Column(accessor='topic', verbose_name='', default='', orderable=False)

    def render_bacnet_units(self, record):
        p = record.get_related_point()
        if p and p.kv_tags.get('bacnet_units'):
            return p.kv_tags.get('bacnet_units')
        else:
            return ''

    def render_bacnet_presentValue(self, record):
        p = record.get_related_point()
        if p and p.kv_tags.get('bacnet_presentValue'):
            return p.kv_tags.get('bacnet_presentValue')
        else:
            return ''

    def render_bacnet_objectName(self, record):
        p = record.get_related_point()
        if p and p.kv_tags.get('bacnet_objectName'):
            return p.kv_tags.get('bacnet_objectName')
        else:
            return ''

    def render_button(self, record):
        p = record.get_related_point()
        if p:
            return format_html('''
                <a class="btn btn-secondary btn-sm" href="{}">
                <i class="fa fa-external-link-alt"></i>  View
                </a>'''.format(reverse(
                    "core:point_detail",
                    kwargs={"entity_id": p.entity_id}),))
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


class TopicListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, ListView):
    model = Topic
    table_class = TopicTable
    table_pagination = {'per_page': 10}
    template_name = 'core/topic_list.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            connections['crate'].ensure_connection()
            self.crate_conn = True
        except OperationalError:
            logging.warning('Crate database unavailable')
            self.crate_conn = False

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        self.rule = None
        if not self.crate_conn:
            return qs

        self.used_filters = []

        topic_filter = None
        site_filter = None
        bacnet_prefix = None
        if "topic_filter" in self.request.session:
            topic_filter = self.request.session["topic_filter"]
            self.request.session["topic_filter"] = None
        if "site_filter" in self.request.session:
            site_filter = self.request.session["site_filter"]
            self.request.session["site_filter"] = None
        if "bacnet_prefix" in self.request.session:
            bacnet_prefix = self.request.session["bacnet_prefix"]
            self.request.session["bacnet_prefix"] = None

        self.select_not_mapped_topics = self.request.GET.get('select_not_mapped_topics')
        if self.select_not_mapped_topics:
            # only list topics where there is no related data point
            # because those are 2 different DB need to get all the data points
            # where topic is non null and remove those topics
            # note: cast topic into entity_id as raw query must have the model PK
            qs = qs.exclude(m_tags__contains=['point'])

        if self.kwargs.get('id'):
            rule_id = self.kwargs['id']
            logging.info('got a rule ID given: %s', rule_id)
            self.rule = get_object_or_404(TopicTagRule, id=rule_id)
            q_filters = []
            for f in self.rule.filters:
                self.used_filters.append({
                    'field': f.get('field'),
                    'type': f.get('type'),
                    'op': f.get('op'),
                    'value': f.get('value')
                })
                q_filters.append((f.get('field'), f.get('type'), f.get('value'), f.get('op')))
            qs = utils.apply_filters_to_queryset(qs, q_filters)

        elif site_filter or topic_filter or bacnet_prefix:
            if bacnet_prefix:
                filter_elem = {'field': 'bacnet_device_id', 'type': 'eq', 'value': bacnet_prefix}
                self.used_filters.append(filter_elem)
                qs = qs.filter(Q(kv_tags__bacnet_device_id__iexact=bacnet_prefix))

            if site_filter:
                filter_elem = {'field': 'siteRef', 'type': 'eq', 'value': site_filter}
                self.used_filters.append(filter_elem)
                qs = qs.filter(Q(kv_tags__siteRef__iexact=site_filter))

            if topic_filter:
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
                filter_op = self.request.GET.get('o' + str(i))
                if filter_type:
                    filter_value = self.request.GET.get('f' + str(i))
                    logging.info('TopicListView get_queryset got filter [ (%s) %s - %s : %s]',
                                 filter_op, filter_field, filter_type, filter_value)
                    self.used_filters.append({
                        'field': filter_field,
                        'type': filter_type,
                        'op': filter_op,
                        'value': filter_value
                    })
                    q_filters.append((filter_field, filter_type, filter_value, filter_op))
            qs = utils.apply_filters_to_queryset(qs, q_filters)

        # add empty filter at the end
        self.used_filters.append({'type': '', 'value': ''})
        logging.info('TopicListView get_queryset filtered %s', qs)
        return qs

    def get_context_data(self, **kwargs):
        if not self.crate_conn:
            context = {}
            context['crate_conn'] = self.crate_conn
            return context

        context = super().get_context_data(**kwargs)
        context['crate_conn'] = self.crate_conn
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
        site = request.POST.get('site')
        if bacnet_prefix:
            logging.info('TopicListView POST got bacnet_prefix %s', bacnet_prefix)
            self.request.session["bacnet_prefix"] = bacnet_prefix
        if site:
            logging.info('TopicListView POST got site %s', site)
            self.request.session["site_filter"] = site

        return HttpResponseRedirect(reverse('core:topic_list'))


topic_list_view = TopicListView.as_view()


@login_required()
@require_POST
def topic_list_table(request):
    qs = Topic.objects.all().exclude(m_tags__contains=['site']).exclude(m_tags__contains=['equip'])

    select_not_mapped_topics = request.POST.get('select_not_mapped_topics')
    if select_not_mapped_topics:
        # only list topics where there is no related data point
        # because those are 2 different DB need to get all the data points
        # where topic is non null and remove those topics
        # note: cast topic into entity_id as raw query must have the model PK
        qs = qs.exclude(m_tags__contains=['point'])

    n = 0
    filters_count = request.POST.get('filters_count')
    if filters_count:
        n = int(filters_count)

    q_filters = []
    for i in range(n):
        filter_field = request.POST.get('n' + str(i))
        filter_type = request.POST.get('t' + str(i))
        filter_op = request.POST.get('o' + str(i))
        if filter_type:
            filter_value = request.POST.get('f' + str(i))
            logging.info('topic_list_table got filter [ (%s) %s - %s : %s]',
                         filter_op, filter_field, filter_type, filter_value)
            q_filters.append((filter_field, filter_type, filter_value, filter_op))
    qs = utils.apply_filters_to_queryset(qs, q_filters)

    rc = RequestConfig(request, paginate={'per_page': 15})
    table = TopicTable(qs, orderable=True, order_by='topic')
    table = rc.configure(table)
    resp = HttpResponse(table.as_html(request))
    resp['topics_counter'] = str(len(qs))
    return resp


@login_required()
@api_view(['POST'])
def topic_list_table_fields(request):
    topic_fields = request.data
    request.session["topic_fields"] = topic_fields

    response = JsonResponse({'success': 1})
    return response


class TopicListJsonView(LoginRequiredMixin, ListView):
    model = Topic

    def post(self, request, *args, **kwargs):
        logging.info('TopicListJsonView render_to_response ...')
        sort_by = self.request.POST.get('sortBy')
        if not sort_by:
            sort_by = 'topic'
        if sort_by != 'topic':
            sort_by = 'kv_tags__' + sort_by
        if self.request.POST.get('sortDesc'):
            sort_by = '-' + sort_by

        qs = Topic.objects.all().exclude(m_tags__contains=['site'])
        qs = qs.exclude(m_tags__contains=['equip']).order_by(sort_by)
        select_not_mapped_topics = self.request.POST.get('select_not_mapped_topics')
        if select_not_mapped_topics:
            # only list topics where there is no related data point
            # because those are 2 different DB need to get all the data points
            # where topic is non null and remove those topics
            # note: cast topic into entity_id as raw query must have the model PK
            qs = qs.exclude(m_tags__contains=['point'])

        n = 0
        filters_count = self.request.POST.get('filters_count')
        if filters_count:
            n = int(filters_count)

        q_filters = []
        for i in range(n):
            filter_field = self.request.POST.get('n' + str(i))
            filter_type = self.request.POST.get('t' + str(i))
            filter_op = self.request.POST.get('o' + str(i))
            if filter_type:
                filter_value = self.request.POST.get('f' + str(i))
                logging.info('topic_list_table got filter [ (%s) %s - %s : %s]',
                             filter_op, filter_field, filter_type, filter_value)
                q_filters.append((filter_field, filter_type, filter_value, filter_op))
        qs = utils.apply_filters_to_queryset(qs, q_filters)

        per_page = self.request.GET.get('per_page') or 10
        page = self.request.GET.get('page') or 1
        paginator = Paginator(qs, per_page)

        logging.info('TopicListJsonView render_to_response DONE')
        topics_list = paginator.get_page(page).object_list.values()
        data = []
        try:
            for item in topics_list:
                p = utils.get_topic_point(item['topic'])
                if p:
                    item['point_entity_id'] = p.entity_id

                data.append(item)
        except Exception:
            return JsonResponse({'error': 'Cannot get topics sorted by {}'.format(sort_by)})

        response = {'data': data, 'count': paginator.count}
        if 'topic_fields' in self.request.session:
            response['topic_fields'] = self.request.session['topic_fields']

        return JsonResponse(response)


topic_list_json = TopicListJsonView.as_view()


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
            <a class="btn btn-secondary btn-sm" href="{}">
            <i class="fa fa-cog"></i> Run
            </a>
            <a class="btn btn-danger btn-sm" href="#" v-confirm="delete_tag_rule({})">
            <i class="fa fa-trash"></i> Delete
            </a>'''.format(reverse('core:topictagrule_run', kwargs={'id': record.id}), record.id,),)

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
    updated, _, _, _ = utils.tag_topics(filters, tags, select_all=select_all,
                                        topics=topics, select_not_mapped_topics=snmt)
    if not updated:
        return JsonResponse({'errors': 'No Topic matched the given filters.'})
    return JsonResponse({'success': 1, 'updated': len(updated), 'tags': tags})


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


class TopicTagRuleBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:topictagruleset_list'), 'label': 'Topic Tag Rule Sets'})
        if context.get('object'):
            b.append({'label': 'Rule {}'.format(context['object'].name or context['object'].id)})
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
                            rule_item = {"name": rule.name, "filters": rule.filters,
                                         "tags": rule.tags, "action": rule.action, "action_fields": rule.action_fields}
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


class TopicTagRuleSetRunView(LoginRequiredMixin, TopicTagRuleSetBCMixin, FormView):
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
            updated_set, updated_entities, preview_type, updated_tags, removed_tags, diff_format, new_eqm = form.save()
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
                if len(updated_set) > 0 or len(new_eqm) > 0:
                    response = JsonResponse({'success': 1, 'updated': len(updated_set),
                                             'new_equipments': len(new_eqm)})
                else:
                    response = JsonResponse({'errors': 'Nothing applied'})
                return response

        else:
            return self.form_invalid(form, **kwargs)


topictagruleset_run_view = TopicTagRuleSetRunView.as_view()


class TopicTagRuleRunView(LoginRequiredMixin, TopicTagRuleBCMixin, FormView):
    form_class = TopicTagRuleRunForm
    template_name = 'core/topictagrule_run.html'

    def get_initial(self):
        logging.info('get_initial: %s', self.kwargs)
        initials = {'rule_id': self.kwargs.get('id')}
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
            if 'id' in self.kwargs and 'rule_id' not in args['data']:
                args['data'].update({'rule_id': self.kwargs.get('id')})
        return args

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'id' in self.kwargs:
            rule = get_object_or_404(TopicTagRule, id=self.kwargs['id'])
            context['rule'] = rule
            context['object'] = rule
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
            updated_set, updated_entities, preview_type, updated_tags, removed_tags, diff_format, new_eqm = form.save()
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
                            response['Content-Disposition'] = 'attachment; filename="TagRulePreviewDiffReport.csv"'

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
                                        + '&name=Tag Rule Preview Diff Report')
                                else:
                                    writer.writerow([''])

                        return response
                else:
                    report_rows, report_header = utils.tag_rulesets_run_report(updated_entities)
                    if preview_type == 'preview_csv':
                        response = HttpResponse(content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="TagRulePreviewReport.csv"'

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
                            + '&name=Tag Rule Preview Report')

                    return response
            else:
                if len(updated_set) > 0 or len(new_eqm) > 0:
                    response = JsonResponse({'success': 1, 'updated': len(updated_set),
                                             'new_equipments': len(new_eqm)})
                else:
                    response = JsonResponse({'errors': 'Nothing applied'})
                return response
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
            logging.info('TopicExportView get_context_data site_id %s', context['site_id'])
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
        site = context["form"].cleaned_data['site'] or context['site_id']
        only_with_trending = context["form"].cleaned_data['only_with_trending']
        his_tagged_topics_only = context["form"].cleaned_data['his_tagged_topics_only']
        response = HttpResponse(content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=bacnet_config.zip"

        try:
            s = SiteView.objects.get(entity_id=site)
            site_id = s.object_id
        except SiteView.DoesNotExist:
            site_id = None

        if device_prefix:
            trendings = Entity.objects.filter(kv_tags__bacnet_prefix=device_prefix, kv_tags__siteRef=site_id).values(
                    'kv_tags__interval').annotate(dcount=Count('kv_tags__interval'))
        else:
            trendings = Entity.objects.filter(kv_tags__siteRef=site_id).values(
                    'kv_tags__interval').annotate(dcount=Count('kv_tags__interval'))

        files_list = []

        allow_tags = ['point']
        if his_tagged_topics_only:
            allow_tags.append('his')

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

                if device_prefix:
                    rows = Entity.objects.filter(
                       kv_tags__siteRef=site_id,
                       kv_tags__bacnet_prefix=device_prefix,
                       m_tags__contains=allow_tags,
                       kv_tags__interval=trending_interval)
                else:
                    rows = Entity.objects.filter(
                       kv_tags__siteRef=site_id,
                       m_tags__contains=allow_tags,
                       kv_tags__interval=trending_interval)

                header = []
                bacnet_data = []
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
            # Add permission for the current user (even if that user is Admin)
            permission = EntityPermission(entity_id=entity_id, user=request.user)
            permission.save()
        if equipment:
            logger.info('topic_assoc create Equipment : %s', equipment)
            equipment_entity_id = equipment.entity_id
            equipment.save()
        e = Entity(entity_id=entity_id, topic=topic)
        e.add_tag('point', commit=False)
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
