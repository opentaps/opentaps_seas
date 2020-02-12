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
from .. import utils
from ..models import Entity
from ..models import ModelView
from ..models import Tag
from django import forms
from django.template.defaultfilters import slugify

logger = logging.getLogger(__name__)


class EquipmentCreateForm(forms.ModelForm):
    entity_id = forms.CharField(label='Equipment ID', max_length=255, required=False)
    description = forms.CharField(max_length=255, required=True)
    model = forms.ChoiceField(required=False)
    bacnet_prefix = forms.CharField(max_length=255, required=False)
    device_id = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        self.site_id = kwargs.pop('site_id')
        super(EquipmentCreateForm, self).__init__(*args, **kwargs)
        self.fields['model'] = forms.ChoiceField(choices=ModelView.get_choices(), required=False)

    def save(self, commit=True):
        description = self.cleaned_data['description']
        entity_id = self.cleaned_data['entity_id']
        if not entity_id or entity_id == '':
            entity_id = utils.make_random_id(description)

        bacnet_prefix = self.cleaned_data['bacnet_prefix']
        device_id = self.cleaned_data['device_id']
        object_id = entity_id
        entity_id = slugify(entity_id)
        self.cleaned_data['entity_id'] = entity_id

        equipment = Entity(entity_id=entity_id)
        equipment.add_tag('equip', commit=False)
        equipment.add_tag('id', object_id, commit=False)
        equipment.add_tag('dis', description, commit=False)
        equipment.add_tag('siteRef', self.site_id, commit=False)
        if bacnet_prefix:
            equipment.add_tag(Tag.bacnet_tag_prefix + 'prefix', bacnet_prefix, commit=False)
            # get points with given bacnet_prefix and set equipRef
            points = Entity.objects.filter(kv_tags__bacnet_prefix=bacnet_prefix).filter(m_tags__contains=['point'])
            if points:
                for point in points:
                    point.add_tag('equipRef', object_id, commit=True)
        if device_id:
            equipment.add_tag(Tag.bacnet_tag_prefix + 'device_id', device_id, commit=False)

        model = self.cleaned_data['model']
        if model:
            equipment.add_tag('modelRef', model, commit=False)
            # add tags from model
            model_obj = ModelView.objects.filter(object_id=model).values().first()
            equipment.add_tags_from_model(model_obj, commit=False)

        equipment.save()
        self.instance = Entity.objects.get(entity_id=entity_id)
        self._post_clean()
        return self.instance

    class Meta:
        model = Entity
        fields = ["entity_id", "description", "model"]
