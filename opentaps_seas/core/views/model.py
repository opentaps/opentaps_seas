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
from .common import WithFilesAndNotesAndTagsMixin
from .. import utils
from ..forms import ModelCreateForm
from ..forms import ModelDuplicateForm
from ..forms import ModelUpdateForm
from ..models import Entity
from ..models import ModelView

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.db.models import Q
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import DeleteView
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

logger = logging.getLogger(__name__)


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
    head_tags = ['dis', 'modelRef', 'model']
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


class ModelDuplicateView(LoginRequiredMixin, ModelBCMixin, CreateView):
    model = ModelView
    slug_field = "entity_id"
    slug_url_kwarg = "entity_id"
    template_name = 'core/model_edit.html'
    form_class = ModelDuplicateForm

    def get_initial(self):
        if 'entity_id' in self.kwargs:
            try:
                pm = Entity.objects.get(entity_id=self.kwargs['entity_id'], m_tags__contains=['model'])
                return {
                    'source_id': pm.entity_id,
                    'entity_id': utils.make_random_id(pm.kv_tags['id']),
                    'description':  pm.kv_tags.get('dis', '') + ' Copy'
                    }
            except Entity.DoesNotExist:
                pass
        return {}


model_duplicate_view = ModelDuplicateView.as_view()


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
