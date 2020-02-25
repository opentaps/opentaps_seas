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
from ..models import FinancialTransaction
from ..models import FinancialTransactionNote
from ..models import FinancialTransactionFile
from flatpickr import DateTimePickerInput
from django import forms

logger = logging.getLogger(__name__)


class FinancialTransactionUpdateForm(forms.ModelForm):

    class Meta:
        date_time_options = {"dateFormat": "Y-m-d H:i:S", "time_24hr": "true", "allowInput": "true",
                             "enableSeconds": "true", "minuteIncrement": 1}
        model = FinancialTransaction
        fields = [
            "transaction_datetime",
            "status",
            "from_party",
            "to_party",
            "amount",
            "uom",
            "transaction_type",
            "from_datetime",
            "thru_datetime",
            "meter",
            "source"
            ]
        widgets = {'transaction_datetime': DateTimePickerInput(options=date_time_options),
                   'from_datetime': DateTimePickerInput(options=date_time_options),
                   'thru_datetime': DateTimePickerInput(options=date_time_options)}


class FinancialTransactionNoteForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = FinancialTransactionNote
        fields = ["id", "financial_transaction", "content", "owner"]


class FinancialTransactionNoteUpdateForm(forms.Form):
    id = forms.IntegerField()
    financial_transaction = forms.IntegerField()
    content = forms.CharField(widget=forms.Textarea, required=True)


class FinancialTransactionNoteDeleteForm(forms.Form):
    id = forms.IntegerField()
    financial_transaction = forms.IntegerField()


class FinancialTransactionFileUploadForm(forms.Form):
    financial_transaction = forms.IntegerField()
    comments = forms.CharField(widget=forms.Textarea, required=False)
    uploaded_file = forms.FileField()


class FinancialTransactionFileDeleteForm(forms.Form):
    id = forms.IntegerField()
    financial_transaction = forms.IntegerField()


class FinancialTransactionFileUpdateForm(forms.Form):
    id = forms.IntegerField()
    financial_transaction = forms.IntegerField()
    comments = forms.CharField(widget=forms.Textarea, required=False)


class FinancialTransactionLinkForm(forms.ModelForm):
    comments = forms.CharField(widget=forms.Textarea, required=False)
    link = forms.URLField()
    link_name = forms.CharField()

    class Meta:
        model = FinancialTransactionFile
        fields = ["id", "financial_transaction", "comments", "owner", "link", "link_name"]
