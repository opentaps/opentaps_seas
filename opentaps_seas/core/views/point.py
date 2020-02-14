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
from datetime import datetime

from .common import WithFilesAndNotesAndTagsMixin
from .common import WithPointBreadcrumbsMixin
from .. import utils
from ..models import datetime_to_string
from ..models import EquipmentView
from ..models import PointView
from ..models import SiteView

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError
from django.db.models import Count
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.views.generic import ListView
from django_tables2 import Column
from django_tables2 import LinkColumn
from django_tables2 import Table
from django_tables2.utils import A  # alias for Accessor

logger = logging.getLogger(__name__)


class PointTable(Table):
    description = LinkColumn('core:point_detail',
                             args=[A('entity_id')],
                             verbose_name='Data Point')
    current_value = Column(verbose_name='Latest Value')

    class Meta:
        order_by = 'description'


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
            charts = []
            try:
                charts = utils.charts_for_points([context['object']])
            except OperationalError:
                logging.warning('Crate database unavailable')

            context['charts'] = charts

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
        (writer.writerow([datetime_to_string(datetime.utcfromtimestamp(int(row[0]) / 1000)), row[1]])
            for row in rows),
        content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}_{}_{}_{}.csv"'.format(
        site, equip, point, resolution or utils.DEFAULT_RES, trange or utils.DEFAULT_RANGE, last_timestamp)
    return response


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
