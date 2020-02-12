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
from io import TextIOWrapper
from ..models import Entity
from ..models import Tag
from django import forms

logger = logging.getLogger(__name__)


class TagChangeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TagChangeForm, self).__init__(*args, **kwargs)
        self.fields['kind'].required = True

    class Meta:
        model = Tag
        fields = ["tag", "kind", "description", "details"]


class TagUpdateForm(TagChangeForm):
    def __init__(self, *args, **kwargs):
        super(TagUpdateForm, self).__init__(*args, **kwargs)
        self.fields['tag'].widget = forms.HiddenInput()


class TagImportForm(forms.Form):
    csv_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.csv'}))
    clear_existing_tags = forms.BooleanField(label="Clear existing tags", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        csv_file = self.cleaned_data['csv_file']
        clear_existing_tags = self.cleaned_data['clear_existing_tags']
        f = TextIOWrapper(csv_file.file, encoding=csv_file.charset if csv_file.charset else 'utf-8')
        records = csv.DictReader(f)

        import_errors = False
        import_success = False
        count = 0
        count_imported = 0
        count_notfound = 0
        if records:
            # the first row is the tags
            for row in records:
                count += 1
                topic = row.get('topic')
                if not topic:
                    topic = row.get('__topic')
                entities = Entity.objects.filter(topic=topic)
                if entities:
                    for entity in entities:
                        if clear_existing_tags:
                            entity.remove_all_tags(commit=False)
                        for tag in row.keys():
                            if tag != 'topic' and not tag.startswith('__'):
                                value = row.get(tag)
                                # check tag Kind
                                if value:
                                    try:
                                        tag_object = Tag.objects.get(tag=tag)
                                    except Tag.DoesNotExist:
                                        logging.error("Cannot get tag {}".format(tag))
                                    else:
                                        if tag_object.kind == 'Marker':
                                            entity.add_tag(tag, value=None, commit=False)
                                        else:
                                            entity.add_tag(tag, value=value, commit=False)

                        entity.save()

                    count_imported += 1
                else:
                    count_notfound += 1

        else:
            import_errors = 'Cannot parse source file'

        if count:
            if count_imported:
                t = "row" if count_imported == 1 else "rows"
                import_success = "Imported {count} {t} successfully. ".format(count=count_imported, t=t)
            else:
                import_success = ""
            if count_notfound:
                t = "row" if count_notfound == 1 else "rows"
                import_success += "{count} {t} from your CSV could not be found.".format(count=count_notfound, t=t)
        else:
            import_errors = 'There is no any data row in the source file'

        result = {}

        if import_errors:
            result['import_errors'] = import_errors
        elif import_success:
            result['import_success'] = import_success

        return result
