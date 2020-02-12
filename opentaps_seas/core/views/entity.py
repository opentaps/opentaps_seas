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

from .common import _read_files
from .common import _read_notes
from .common import WithBreadcrumbsMixin
from .common import WithFilesAndNotesAndTagsMixin
from .. import utils
from ..models import Entity
from ..models import EntityFile
from ..models import EntityNote
from ..models import ListableEntity
from ..models import ModelView
from ..forms.entity import EntityLinkForm
from ..forms.entity import EntityNoteDeleteForm
from ..forms.entity import EntityNoteForm
from ..forms.entity import EntityNoteUpdateForm
from ..forms.file import FileDeleteForm
from ..forms.file import FileUpdateForm
from ..forms.file import FileUploadForm

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Q
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django_filters import CharFilter
from django_filters import FilterSet
from django_filters.views import FilterView
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor
from django_tables2.views import SingleTableMixin
from easy_thumbnails.files import get_thumbnailer
from filer.models import Image as FilerFile

logger = logging.getLogger(__name__)


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
