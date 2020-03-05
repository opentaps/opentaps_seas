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
from flatpickr import DatePickerInput
from flatpickr import DateTimePickerInput
from django import forms
from django.db import models

logger = logging.getLogger(__name__)


class DateTimeInput(DateTimePickerInput):

    def __init__(self, attrs=None, options=None):
        opts = {
            "dateFormat": "Y-m-d H:i:S",
            "time_24hr": "true",
            "allowInput": "true",
            "enableSeconds": "true",
            "minuteIncrement": 1
        }
        if options:
            opts = opts.update(options)
        super().__init__(attrs=attrs, options=opts)


class DateInput(DatePickerInput):

    def __init__(self, attrs=None, options=None):
        opts = {
            "dateFormat": "Y-m-d H:i:S",
            "allowInput": "true"
        }
        if options:
            opts = opts.update(options)
        super().__init__(attrs=attrs, options=opts)


class DateTimeField(forms.DateTimeField):

    widget = DateTimeInput


class DateField(forms.DateField):

    widget = DateInput


class MaskedTextInput(forms.TextInput):

    @classmethod
    def mask_value(clss, value):
        if value:
            return '*' * len(value[:-4]) + value[-4:]
        return value

    def format_value(self, value):
        value = super().format_value(value)
        return MaskedTextInput.mask_value(value)


# Note this only work on ModelForms, there just add:
#    formfield_callback = make_custom_datefields
# to change all date and date time fields normally made from
# the model fields
def make_custom_datefields(f, **kwargs):
    if isinstance(f, models.DateTimeField):
        # return form field with your custom widget here...
        return f.formfield(form_class=DateTimeField, **kwargs)
    elif isinstance(f, models.DateField):
        # return form field with your custom widget here...
        return f.formfield(form_class=DateField, **kwargs)
    else:
        return f.formfield(**kwargs)
