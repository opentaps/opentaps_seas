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

from .common import _read_notes
from .common import _read_files
from .common import WithBreadcrumbsMixin
from .. import utils
from ..forms.transaction import FinancialTransactionUpdateForm
from ..forms.transaction import FinancialTransactionNoteForm
from ..forms.transaction import FinancialTransactionNoteUpdateForm
from ..forms.transaction import FinancialTransactionNoteDeleteForm
from ..forms.transaction import FinancialTransactionLinkForm
from ..forms.transaction import FinancialTransactionFileDeleteForm
from ..forms.transaction import FinancialTransactionFileUpdateForm
from ..forms.transaction import FinancialTransactionFileUploadForm
from ..models import FinancialTransaction
from ..models import FinancialTransactionFile
from ..models import FinancialTransactionNote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files import File
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django_tables2 import Column
from django_tables2 import Table
from django_tables2.views import SingleTableMixin
from easy_thumbnails.files import get_thumbnailer
from filer.models import Image as FilerFile

logger = logging.getLogger(__name__)


class FinancialTransactionTable(Table):
    financial_transaction_id = Column(verbose_name='ID', linkify=lambda record: record.get_absolute_url())
    amount = Column(attrs={'th': {'align': 'right'}, 'td': {'align': 'right'}})
    meter = Column(linkify=True)
    meter__site = Column(linkify=True)

    def render_amount(self, record):
        return "{} {}".format(record.uom.symbol, record.amount)

    class Meta:
        attrs = {"style": "font-size:small"}
        model = FinancialTransaction
        fields = (
            'transaction_datetime',
            'financial_transaction_id',
            'from_party',
            'to_party',
            'amount',
            'status',
            'meter'
            )
        order_by = '-transaction_datetime'


class TransactionListView(LoginRequiredMixin, SingleTableMixin, WithBreadcrumbsMixin, ListView):
    model = FinancialTransaction
    table_class = FinancialTransactionTable
    table_pagination = {'per_page': 10}
    template_name = 'core/transaction_list.html'


transaction_list_view = TransactionListView.as_view()


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = FinancialTransaction
    slug_field = "financial_transaction_id"
    slug_url_kwarg = "financial_transaction_id"
    template_name = 'core/transaction_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.kwargs["financial_transaction_id"]

        # check for files
        context['file_upload_form'] = {
            'url': reverse("core:transaction_file_upload", kwargs={"financial_transaction_id": obj_id}),
            'link_add_url': reverse("core:transaction_link", kwargs={"financial_transaction_id": obj_id}),
            'params': [
                {'key': 'financial_transaction', 'value': obj_id}
            ]
        }

        # check for notes
        context['notes_form'] = {
            'url': reverse("core:transaction_note", kwargs={"financial_transaction_id": obj_id}),
            'params': [
                {'key': 'financial_transaction', 'value': obj_id}
            ]
        }
        return context


transaction_detail_view = TransactionDetailView.as_view()


class TransactionEditView(LoginRequiredMixin, WithBreadcrumbsMixin, UpdateView):
    model = FinancialTransaction
    slug_field = "financial_transaction_id"
    slug_url_kwarg = "financial_transaction_id"
    template_name = 'core/transaction_edit.html'
    form_class = FinancialTransactionUpdateForm


transaction_edit_view = TransactionEditView.as_view()


class TransactionDeleteView(LoginRequiredMixin, WithBreadcrumbsMixin, DeleteView):
    model = FinancialTransaction
    slug_field = "financial_transaction_id"
    slug_url_kwarg = "financial_transaction_id"
    template_name = 'core/transaction_delete.html'
    success_url = reverse_lazy('core:transaction_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        try:
            self.object.delete()
        except ProtectedError:
            messages.add_message(request, messages.ERROR, 'Can not delete this Transaction!')
            return HttpResponseRedirect(self.object.get_absolute_url())

        return HttpResponseRedirect(success_url)


transaction_delete_view = TransactionDeleteView.as_view()


@login_required()
def transaction_note(request, financial_transaction_id):
    if request.method == 'GET':
        items = []
        _read_notes(FinancialTransactionNote.objects.filter(financial_transaction_id=financial_transaction_id), items)
        return JsonResponse({'items': items})
    elif request.method == 'POST':
        if request.POST.get('update'):
            form = FinancialTransactionNoteUpdateForm(request.POST)
            if form.is_valid():
                try:
                    e = FinancialTransactionNote.objects.get(id=form.cleaned_data['id'],
                                                             financial_transaction_id=financial_transaction_id)
                except FinancialTransactionNote.DoesNotExist:
                    return JsonResponse({'errors': 'FinancialTransactionNote not found {} : {}'.format(
                        form.cleaned_data['id'], form.cleaned_data['entity_id'])}, status=404)
                e.content = form.cleaned_data['content']
                e.save()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        elif request.POST.get('delete'):
            form = FinancialTransactionNoteDeleteForm(request.POST)
            if form.is_valid():
                FinancialTransactionNote.objects.get(id=form.cleaned_data['id'],
                                                     financial_transaction_id=financial_transaction_id).delete()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        else:
            form = FinancialTransactionNoteForm(request.POST)
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


@login_required()
def transaction_file_upload(request, financial_transaction_id):
    if request.method == 'GET':
        items = []
        _read_files(FinancialTransactionFile.objects.filter(financial_transaction_id=financial_transaction_id), items)
        return JsonResponse({'items': items})
    elif request.method == 'POST':
        if request.POST.get('update'):
            form = FinancialTransactionFileUpdateForm(request.POST)
            if form.is_valid():
                e = FinancialTransactionFile.objects.get(id=form.cleaned_data['id'],
                                                         financial_transaction_id=financial_transaction_id)
                e.comments = form.cleaned_data['comments']
                e.save()
                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        elif request.POST.get('delete'):
            form = FinancialTransactionFileDeleteForm(request.POST)
            if form.is_valid():
                try:
                    e = FinancialTransactionFile.objects.get(id=form.cleaned_data['id'],
                                                             financial_transaction_id=financial_transaction_id)
                except FinancialTransactionFile.DoesNotExist:
                    return JsonResponse({'errors': 'FinancialTransactionFile not found {} : {}'.format(
                        form.cleaned_data['id'], financial_transaction_id)}, status=404)
                e.delete()

                return JsonResponse({'success': 1, 'id': form.cleaned_data['id']})
            else:
                return JsonResponse({'errors': form.errors})
        else:
            form = FinancialTransactionFileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data['uploaded_file']
                file_obj = File(f, name=f.name)
                filer_file = FilerFile.objects.create(owner=request.user,
                                                      original_filename=f.name,
                                                      file=file_obj)
                e = FinancialTransactionFile.objects.create(financial_transaction_id=financial_transaction_id,
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


@require_POST
@login_required()
def transaction_link(request, financial_transaction_id):
    if request.POST.get('update'):
        try:
            e = FinancialTransactionFile.objects.get(id=request.POST.get('id'),
                                                     financial_transaction_id=financial_transaction_id)
        except FinancialTransactionFile.DoesNotExist:
            return JsonResponse({'errors': 'FinancialTransactionFile not found {} : {}'.format(
                request.POST.get('id'), financial_transaction_id)}, status=404)
        form = FinancialTransactionLinkForm(request.POST, instance=e)
    else:
        form = FinancialTransactionLinkForm(request.POST)
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
