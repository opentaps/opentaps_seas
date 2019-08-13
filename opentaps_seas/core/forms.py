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
import json
import csv
from io import TextIOWrapper
from . import utils
from .models import EntityFile
from .models import EntityNote
from .models import Entity
from .models import ModelView
from .models import SiteView
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


class TopicTagRuleSetRunForm(forms.Form):
    ruleset_id = ModelField(label='RuleSet', max_length=255, required=True)
    topic_filter = ModelField(label='Topic Filter', max_length=255, required=False)
    preview_type = forms.CharField(required=False)

    def is_valid(self):
        if not super().is_valid():
            return False
        ruleset_id = self.cleaned_data['ruleset_id']
        if not TopicTagRuleSet.objects.filter(id=ruleset_id).exists():
            logger.error('TopicTagRuleSetRunForm: rule set %s not found.', ruleset_id)
            self.add_error('ruleset_id', 'Rule Set not found.')
            return False
        return True

    def save(self, commit=True):
        # run the topic tag ruleset
        topic_filter = self.cleaned_data['topic_filter']
        ruleset_id = self.cleaned_data['ruleset_id']
        preview_type = self.cleaned_data['preview_type']
        pretend = False
        if preview_type:
            pretend = True

        logger.info('TopicTagRuleSetRunForm: for set %s and additional filter: %s', ruleset_id, topic_filter)
        rule_set = TopicTagRuleSet.objects.get(id=ruleset_id)
        # collect count of topics we ran for
        updated_set = set()
        updated_entities = {}
        for rule in rule_set.topictagrule_set.all():
            if rule.tags:
                rule_filters = rule.filters
                # Add the topic_filter to the rule filters if given
                if topic_filter:
                    tf = {'type': 'c', 'value': topic_filter}
                    if rule_filters:
                        rule_filters.append(tf)
                    else:
                        rule_filters = [tf]
                updated, updated_entities = utils.tag_topics(rule_filters, rule.tags, select_all=True, pretend=pretend)
                for x in updated:
                    updated_set.add(x.get('topic'))
        return updated_set, updated_entities, preview_type


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
    site = forms.ChoiceField(required=True)
    device_prefix = forms.CharField(max_length=255)
    csv_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.csv'}))
    config_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.config'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site'] = forms.ChoiceField(choices=SiteView.get_choices())
        self.fields['device_prefix'].widget.attrs.update({'placeholder': 'eg: campus/building/device'})


class TopicExportForm(forms.Form):
    site = forms.ChoiceField(required=False)
    device_prefix = forms.CharField(required=False)
    only_with_trending = forms.BooleanField(label="Only export topics with Trending set", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        site_id = kwargs.pop('site_id')
        super(TopicExportForm, self).__init__(*args, **kwargs)
        if not site_id:
            self.fields['site'] = forms.ChoiceField(choices=SiteView.get_choices())

    class Meta:
        fields = ["site_id", "device_prefix", "only_with_trending"]


class TopicTagRuleSetImportForm(forms.Form):
    json_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.json'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True, run_rule=False):
        json_file = self.cleaned_data['json_file']
        fc = TextIOWrapper(json_file.file, encoding=json_file.charset if json_file.charset else 'utf-8')

        # an error message
        import_errors = False
        # the imported rule sets
        success_rule_sets = []
        # if the rulesets are run, count how many topics were affected
        runner_count = 0
        try:
            rule_sets_data = json.loads(fc.read())
        except json.decoder.JSONDecodeError:
            import_errors = "Cannot parse JSON file."
        else:
            if rule_sets_data and rule_sets_data.get("tag_rule_sets"):
                for tag_rule_set in rule_sets_data.get("tag_rule_sets"):
                    name = tag_rule_set.get("name")
                    if name:
                        # check if rule sets with given name is already exists
                        name = name.strip()
                        topic_tag_rule_sets = TopicTagRuleSet.objects.filter(name=name)
                        if topic_tag_rule_sets:
                            for topic_tag_rule_set in topic_tag_rule_sets:
                                TopicTagRule.objects.filter(rule_set=topic_tag_rule_set.id).delete()
                                topic_tag_rule_set.delete()

                        # import
                        topic_tag_rule_set = TopicTagRuleSet(name=name)
                        topic_tag_rule_set.save()
                        success_rule_sets.append(name)

                        rules = tag_rule_set.get("rules")
                        if rules:
                            for rule in rules:
                                name = rule.get("name")
                                if name:
                                    topic_tag_rule = TopicTagRule(name=name, rule_set=topic_tag_rule_set)
                                    filters = rule.get("filters")
                                    if filters:
                                        topic_tag_rule.filters = filters
                                    else:
                                        topic_tag_rule.filters = []

                                    tags = rule.get("tags")
                                    if tags:
                                        topic_tag_rule.tags = tags
                                    else:
                                        topic_tag_rule.tags = []

                                    topic_tag_rule.save()
                        if run_rule:
                            # run the imported ruleset
                            runner = TopicTagRuleSetRunForm({'ruleset_id': topic_tag_rule_set.id})
                            if runner.is_valid():
                                updated_set = runner.save()
                                runner_count += len(updated_set)
            else:
                import_errors = "JSON file rule sets is empty."

        if import_errors:
            return {'import_errors': import_errors}
        elif success_rule_sets:
            res = {'success_rule_sets': success_rule_sets}
            if run_rule:
                res['runner_count'] = runner_count
            return res
        else:
            return {'import_errors': "Rule sets list to import is empty."}


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
            import_success = "Imported {}, not found {} of {} rows".format(
                count_imported, count_notfound, count)
        else:
            import_errors = 'There is no any data row in the source file'

        if import_errors:
            return {'import_errors': import_errors}
        elif import_success:
            return {'import_success': import_success}

        return {}
