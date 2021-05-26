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
import json

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from .. import utils
from ..celery import Progress
from ..models import EntityPermission, Geo
from ..models import TimeZone
from ..models import UnitOfMeasure

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic import TemplateView
from easy_thumbnails.files import get_thumbnailer

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


class GoogleApiMixin(object):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if settings.GOOGLE_API_KEY:
            context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
        return context


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


class GetTaskProgressView(LoginRequiredMixin, WithBreadcrumbsMixin, TemplateView):
    template_name = 'core/task_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progress'] = Progress(kwargs.get('task_id')).get_info()
        logger.info('GetTaskProgressView context = {}'.format(context))
        return context

    def get_breadcrumbs(self, context):
        b = []
        b.append({'label': 'Meter'})
        return b


get_task_progress = GetTaskProgressView.as_view()


@login_required()
def get_task_progress_json(request, task_id):
    progress = Progress(task_id)
    return HttpResponse(json.dumps(progress.get_info()), content_type='application/json')


class UOMListJsonView(LoginRequiredMixin, ListView):
    model = UnitOfMeasure

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)

        restricted = self.kwargs['restricted']
        if restricted:
            qs = qs.filter(uom_id__istartswith=restricted)
        return qs.order_by(Lower('description'))

    def render_to_response(self, context, **response_kwargs):
        data = list(context['object_list'].values('uom_id', 'description', 'type'))
        return JsonResponse({'items': data})


uom_list_json_view = UOMListJsonView.as_view()


def filter_entities_by_permission(queryset, user):
    if not user.is_superuser:
        return queryset.filter(entity_id__in=EntityPermission.objects.filter(user=user))
    return queryset


def check_entity_permission_or_not_allowed(entity_id, user):
    if not user.is_superuser and not EntityPermission.objects.filter(entity_id=entity_id, user_id=user.id).exists():
        raise PermissionDenied()

