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
from . import utils
from .models import EntityFile
from .models import EntityNote
from .models import Entity
from .models import ModelView
from .models import Tag
from .models import TopicTagRule
from .models import TopicTagRuleSet
from .models import TimeZone
from django import forms
from django.template.defaultfilters import slugify

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


class ModelCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ModelCreateForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            return False
        logger.info('ModelCreateForm: check is_valid')
        obj_id = self.cleaned_data['entity_id']
        if Entity.objects.filter(kv_tags__id=obj_id).exists():
            logger.error('ModelCreateForm: got model with id = %s', obj_id)
            self.add_error('entity_id', 'Model with this Model ID already exists.')
            return False
        return True

    def save(self, commit=True):
        obj_id = self.cleaned_data['entity_id']
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
    def __init__(self, *args, **kwargs):
        super(ModelUpdateForm, self).__init__(*args, **kwargs)
        self.fields['entity_id'].widget = forms.HiddenInput()


class TopicTagRuleSetCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            return False
        name = self.cleaned_data['name']
        if TopicTagRuleSet.objects.filter(name=name).exists():
            logger.error('TopicTagRuleSetCreateForm: got rule set with name = %s', name)
            self.add_error('name', 'Rule Set with this name already exists.')
            return False
        return True

    class Meta:
        model = TopicTagRuleSet
        fields = ["name"]


class TopicTagRuleCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            return False
        rule_set = self.cleaned_data['rule_set']
        name = self.cleaned_data['name']
        if not type(rule_set) == TopicTagRuleSet and not TopicTagRuleSet.objects.filter(id=rule_set).exists():
            logger.error('TopicTagRuleCreateForm: rule set not found = %s', rule_set)
            self.add_error('rule_set', 'Rule Set [{}] does not exist.'.format(rule_set))
            return False
        if TopicTagRule.objects.filter(rule_set=rule_set, name=name).exists():
            logger.error('TopicTagRuleCreateForm: got rule with name = %s', name)
            self.add_error('name', 'Rule with this name already exists in this rule set.')
            return False
        return True

    class Meta:
        model = TopicTagRule
        fields = ["rule_set", "name"]


class SiteCreateForm(forms.ModelForm):
    entity_id = forms.CharField(label='Site ID', max_length=255, required=False)
    description = forms.CharField(max_length=255, required=True)
    area = forms.CharField(max_length=255, required=False)
    address = forms.CharField(label='Street address', max_length=255, required=False)
    country = forms.Field(required=False)
    state = forms.Field(required=False)
    city = forms.CharField(max_length=255, required=False)
    timezone = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(SiteCreateForm, self).__init__(*args, **kwargs)
        self.fields['timezone'] = forms.ChoiceField(choices=TimeZone.get_choices())

    def save(self, commit=True):
        description = self.cleaned_data['description']
        entity_id = self.cleaned_data['entity_id']
        if not entity_id or entity_id == '':
            entity_id = utils.make_random_id(description)

        object_id = entity_id
        entity_id = slugify(entity_id)
        self.cleaned_data['entity_id'] = entity_id

        site = Entity(entity_id=entity_id)
        site.add_tag('site', commit=False)
        site.add_tag('id', object_id, commit=False)
        site.add_tag('dis', description, commit=False)
        area = self.cleaned_data['area']
        if area:
            site.add_tag('area', area, commit=False)
        address = self.cleaned_data['address']
        if address:
            site.add_tag('geoAddr', address, commit=False)
        country = self.cleaned_data['country']
        if country:
            site.add_tag('geoCountry', country, commit=False)
        state = self.cleaned_data['state']
        if state:
            site.add_tag('geoState', state, commit=False)
        city = self.cleaned_data['city']
        if city:
            site.add_tag('geoCity', city, commit=False)
        timezone = self.cleaned_data['timezone']
        if timezone:
            site.add_tag('tz', timezone, commit=False)

        site.save()
        self.instance = Entity.objects.get(entity_id=entity_id)
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = Entity
        fields = ["entity_id", "description", "area", "address", "country", "state", "city", "timezone"]


class EquipmentCreateForm(forms.ModelForm):
    entity_id = forms.CharField(label='Equipment ID', max_length=255, required=False)
    description = forms.CharField(max_length=255, required=True)
    model = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        self.site_id = kwargs.pop('site_id')
        super(EquipmentCreateForm, self).__init__(*args, **kwargs)
        self.fields['model'] = forms.ChoiceField(choices=ModelView.get_choices(), required=False)

    def save(self, commit=True):
        description = self.cleaned_data['description']
        entity_id = self.cleaned_data['entity_id']
        if not entity_id or entity_id == '':
            entity_id = utils.make_random_id(description)

        object_id = entity_id
        entity_id = slugify(entity_id)
        self.cleaned_data['entity_id'] = entity_id

        equipment = Entity(entity_id=entity_id)
        equipment.add_tag('equip', commit=False)
        equipment.add_tag('id', object_id, commit=False)
        equipment.add_tag('dis', description, commit=False)
        equipment.add_tag('siteRef', self.site_id, commit=False)

        model = self.cleaned_data['model']
        if model:
            equipment.add_tag('modelRef', model, commit=False)

        equipment.save()
        self.instance = Entity.objects.get(entity_id=entity_id)
        self._post_clean()
        return self.instance

    class Meta:
        model = Entity
        fields = ["entity_id", "description", "model"]


class EntityFileUploadForm(forms.ModelForm):

    class Meta:
        model = EntityFile
        fields = ["id", "entity_id", "comments", "owner", "uploaded_file"]


class FileUploadForm(forms.Form):
    entity_id = forms.CharField(max_length=255)
    comments = forms.CharField(widget=forms.Textarea, required=False)
    uploaded_file = forms.FileField()


class FileDeleteForm(forms.Form):
    id = forms.IntegerField()
    entity_id = forms.CharField(max_length=255)


class FileUpdateForm(forms.Form):
    id = forms.IntegerField()
    entity_id = forms.CharField(max_length=255)
    comments = forms.CharField(widget=forms.Textarea, required=False)


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


class TopicAssocForm(forms.Form):
    topic = forms.CharField(max_length=255)
    site_id = forms.CharField(max_length=255)
    equipment_id = forms.CharField(max_length=255)
    data_point_name = forms.CharField(max_length=255)


class TopicImportForm(forms.Form):
    device_prefix = forms.CharField(max_length=255)
    csv_file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_prefix'].widget.attrs.update({'placeholder': 'eg: campus/building/equipment'})
