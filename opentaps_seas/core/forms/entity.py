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
from ..models import EntityFile
from ..models import EntityNote
from django import forms

logger = logging.getLogger(__name__)


class EntityFileUploadForm(forms.ModelForm):

    class Meta:
        model = EntityFile
        fields = ["id", "entity_id", "comments", "owner", "uploaded_file"]


class EntityNoteForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = EntityNote
        fields = ["id", "entity_id", "content", "owner"]


class EntityNoteUpdateForm(forms.Form):
    id = forms.IntegerField()
    entity_id = forms.CharField(max_length=255)
    content = forms.CharField(widget=forms.Textarea, required=True)


class EntityNoteDeleteForm(forms.Form):
    id = forms.IntegerField()
    entity_id = forms.CharField(max_length=255)


class EntityLinkForm(forms.ModelForm):
    entity_id = forms.CharField(max_length=255)
    comments = forms.CharField(widget=forms.Textarea, required=False)
    link = forms.URLField()
    link_name = forms.CharField()

    class Meta:
        model = EntityFile
        fields = ["id", "entity_id", "comments", "owner", "link", "link_name"]
