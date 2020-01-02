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
from ..core.models import Meter
from ..core.models import SiteView
from ..core.views import WithBreadcrumbsMixin
from . import utils
from .models import BaselineModel
from .forms import MeterModelCreateForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView

logger = logging.getLogger(__name__)


class ModelBCMixin(WithBreadcrumbsMixin):

    def get_breadcrumbs(self, context):
        b = []
        b.append({'url': reverse('core:site_list'), 'label': 'Sites'})

        meter = None
        if context.get('object') and context['object'].meter:
            meter = context['object'].meter
        elif context.get('meter_id'):
            meter = Meter.objects.get(meter_id=context['meter_id'])

        site = None
        if meter and meter.site:
            site = SiteView.objects.get(entity_id=meter.site.entity_id)
            label = 'Site'
            if site.description:
                label = site.description
            url = reverse("core:site_detail", kwargs={'site': site.entity_id})
            b.append({'url': url, 'label': label})

        if meter:
            label = 'Meter'
            if meter.description:
                label = meter.description
            url = reverse("core:meter_detail", kwargs={'meter_id': meter.meter_id})
            b.append({'url': url, 'label': label})

        if context.get('id'):
            b.append({'label': 'Meter Model {}'.format(self.kwargs['id'])})
        return b


class MeterModelDetailView(LoginRequiredMixin, ModelBCMixin, DetailView):
    model = BaselineModel
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'eemeter/model_detail.html'


meter_model_detail_view = MeterModelDetailView.as_view()


class MeterModelCreateView(LoginRequiredMixin, ModelBCMixin, CreateView):
    model = BaselineModel
    slug_field = "meter_id"
    slug_url_kwarg = "meter_id"
    template_name = 'eemeter/model_edit.html'
    form_class = MeterModelCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meter_id'] = self.kwargs['meter_id']
        return context

    def get_initial(self):
        if 'meter_id' in self.kwargs:
            try:
                pm = Meter.objects.get(meter_id=self.kwargs['meter_id'])
                return {'meter_id': pm.meter_id}
            except Meter.DoesNotExist:
                pass
        return {}


meter_model_create_view = MeterModelCreateView.as_view()


class MeterModelDeleteView(LoginRequiredMixin, ModelBCMixin, DeleteView):
    model = BaselineModel
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'eemeter/model_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.meter:
            success_url = reverse("core:meter_detail", kwargs={'meter_id': self.object.meter_id})
        else:
            success_url = reverse("core:site_list")
        self.object.delete()

        return HttpResponseRedirect(success_url)


meter_model_delete_view = MeterModelDeleteView.as_view()


@login_required()
@require_POST
def meter_model_calc_saving_view(request, meter_id, id):
    model = get_object_or_404(BaselineModel, id=id, meter_id=meter_id)
    m = utils.load_model(model)
    data = utils.read_meter_data(model.meter, freq=model.frequency)
    savings = utils.get_savings(data, m)
    logger.info('meter_model_calc_saving_view: got saving = {}'.format(savings))
    messages.success(request, 'Calculated savings as of now: {}'.format(savings))
    return HttpResponseRedirect(model.get_absolute_url())
