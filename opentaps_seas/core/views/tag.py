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
from ..forms import TagChangeForm
from ..forms import TagUpdateForm
from ..forms import TagImportForm
from ..models import Tag
from ..models import Topic

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic.edit import FormView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin

logger = logging.getLogger(__name__)


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
