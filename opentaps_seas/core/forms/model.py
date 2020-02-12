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
from ..models import Entity
from ..models import ModelView
from django import forms
from django.template.defaultfilters import slugify

logger = logging.getLogger(__name__)


class ModelInput(forms.TextInput):
    template_name = 'core/forms/modelinput.html'


class ModelField(forms.CharField):
    widget = ModelInput


class ModelCreateForm(forms.ModelForm):
    parent_id = ModelField(label='Parent Model ID', max_length=255, required=False)

    check_unique_entity_id = True

    def __init__(self, *args, **kwargs):
        super(ModelCreateForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            logger.error('ModelCreateForm: super not valid')
            return False
        logger.info('ModelCreateForm: check is_valid')
        obj_id = self.cleaned_data['entity_id']
        if self.check_unique_entity_id and Entity.objects.filter(kv_tags__id=obj_id).exists():
            logger.error('ModelCreateForm: got model with id = %s', obj_id)
            self.add_error('entity_id', 'Model with this Model ID already exists.')
            return False
        parent_id = self.cleaned_data['parent_id']
        if parent_id:
            # check parent model exists
            try:
                Entity.objects.get(kv_tags__id=parent_id, m_tags__contains=['model'])
            except Entity.DoesNotExist:
                logger.error('ModelCreateForm: model not found with id = %s', parent_id)
                self.add_error('parent_id', 'Model {} does not exist.'.format(parent_id))
                return False
        return True

    def save(self, commit=True):
        obj_id = self.cleaned_data['entity_id']
        parent_id = self.cleaned_data['parent_id']
        entity_id = slugify(obj_id)
        logger.info('ModelCreateForm: for model %s', obj_id)
        try:
            m = Entity.objects.get(kv_tags__id=obj_id)
            logger.info('ModelCreateForm: got model %s', m)
        except Entity.DoesNotExist:
            logger.info('ModelCreateForm: model not found, creating ... %s', self.instance)
            m = Entity(entity_id=entity_id)
            m.add_tag('id', obj_id, commit=False)
            m.add_tag('model', commit=False)
        if parent_id:
            m.add_tag('modelRef', parent_id, commit=False)
        if self.instance.description:
            m.add_tag('dis', self.instance.description, commit=False)
        if commit:
            m.save()
            self.instance = ModelView.objects.get(entity_id=entity_id)
            self.cleaned_data['entity_id'] = entity_id
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = ModelView
        fields = ["entity_id", "description"]


class ModelUpdateForm(ModelCreateForm):
    check_unique_entity_id = False

    def __init__(self, *args, **kwargs):
        super(ModelUpdateForm, self).__init__(*args, **kwargs)
        self.fields['entity_id'].widget = forms.HiddenInput()


class ModelDuplicateForm(forms.ModelForm):
    source_id = ModelField(label='Parent Model ID', max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super(ModelDuplicateForm, self).__init__(*args, **kwargs)
        self.fields['source_id'].widget = forms.HiddenInput()

    def is_valid(self):
        if not super().is_valid():
            logger.error('ModelDuplicateForm: super not valid')
            return False
        logger.info('ModelDuplicateForm: check is_valid')
        obj_id = self.cleaned_data['entity_id']

        if Entity.objects.filter(kv_tags__id=obj_id).exists():
            logger.error('ModelDuplicateForm: got model with id = %s', obj_id)
            self.add_error('entity_id', 'Model with this Model ID already exists.')
            return False

        return True

    def save(self, commit=True):
        obj_id = self.cleaned_data['entity_id']
        source_id = self.cleaned_data['source_id']
        description = self.cleaned_data['description']
        entity_id = slugify(obj_id)
        logger.info('ModelDuplicateForm: for source model %s', source_id)
        skip_tags = ['id', 'dis']

        new_model = Entity(entity_id=entity_id)
        new_model.add_tag('id', obj_id, commit=False)
        new_model.add_tag('model', commit=False)

        try:
            source_model = Entity.objects.get(entity_id=source_id)
            logger.info('ModelDuplicateForm: got model %s', source_model)

            for tag, value in source_model.kv_tags.items():
                if tag not in skip_tags:
                    new_model.add_tag(tag, value, commit=False)

            for tag in source_model.m_tags:
                new_model.add_tag(tag, None, commit=False)

        except Entity.DoesNotExist:
            logger.info('ModelDuplicateForm: source model %s not found', source_id)

        if description:
            new_model.add_tag('dis', description, commit=False)

        if commit:
            new_model.save()
            self.instance = ModelView.objects.get(entity_id=entity_id)
            self.cleaned_data['entity_id'] = entity_id
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = ModelView
        fields = ["entity_id", "description"]
