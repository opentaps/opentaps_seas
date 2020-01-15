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
from datetime import datetime
from datetime import timedelta
from ..core.models import Meter
from ..core.models import SiteView
from ..core.views import WithBreadcrumbsMixin
from .models import BaselineModel
from .forms import CalcMeterSavingsForm
from .forms import MeterModelCreateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic.edit import FormView

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


class MeterModelExtraDetailView(LoginRequiredMixin, ModelBCMixin, DetailView):
    model = BaselineModel
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'eemeter/model_extra_detail.html'


meter_model_extra_detail_view = MeterModelExtraDetailView.as_view()


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
        initials = {}
        if 'meter_id' in self.kwargs:
            try:
                pm = Meter.objects.get(meter_id=self.kwargs['meter_id'])
                initials['meter_id'] = pm.meter_id
                last = pm.get_meter_data().last()
                if last:
                    initials['thru_date'] = last.as_of_datetime
            except Meter.DoesNotExist:
                pass
        return initials

    def form_valid(self, form):
        if form.cleaned_data['use_async']:
            self.object = form.save()
            return HttpResponseRedirect(reverse("core:get_task_progress", kwargs={'task_id': self.object.task_id}))
        else:
            return super().form_valid(form)


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


class MeterModelProductionDeleteView(LoginRequiredMixin, ModelBCMixin, DeleteView):
    model = BaselineModel
    slug_field = "id"
    slug_url_kwarg = "id"
    template_name = 'eemeter/model_production_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.get_production().delete()
        return HttpResponseRedirect(self.object.get_absolute_url())


meter_model_production_delete_view = MeterModelProductionDeleteView.as_view()


class MeterModelCalcSavingView(LoginRequiredMixin, FormView):
    form_class = CalcMeterSavingsForm
    template_name = 'eemeter/calc_saving.html'

    def get_initial(self):
        logging.info('get_initial: %s', self.kwargs)
        now = datetime.utcnow()
        start = now - timedelta(days=30)
        return {
            'from_datetime': start,
            'to_datetime': now,
            'meter_id': self.kwargs.get('meter_id'),
            'model_id': self.kwargs.get('id')
        }

    def get_form_kwargs(self):
        args = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            # first change the data to be a copy of POST
            args.update({
                'data': self.request.POST.copy(),
            })
            # add the URL given ID to the params for the Form
            if 'id' in self.kwargs and 'model_id' not in args['data']:
                args['data'].update({'model_id': self.kwargs.get('id')})
        return args

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'meter_id' in self.kwargs:
            meter = get_object_or_404(Meter, meter_id=self.kwargs['meter_id'])
            context['meter'] = meter
        if 'id' in self.kwargs:
            model = get_object_or_404(BaselineModel, id=self.kwargs['id'])
            context['model'] = model
            context['object'] = model
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(form.model.get_absolute_url())
        else:
            return self.form_invalid(form)


meter_model_calc_saving_view = MeterModelCalcSavingView.as_view()
