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
from .. import utils
from ..models import Entity
from ..models import SiteView
from ..models import Tag
from ..models import TopicTagRule
from ..models import TopicTagRuleSet
from ..models import Topic
from .model import ModelField
from django import forms

logger = logging.getLogger(__name__)


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
    diff_format = forms.BooleanField(label="Preview in a diff format", required=False, initial=False)

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
        diff_format = self.cleaned_data['diff_format']
        pretend = False
        if preview_type:
            pretend = True

        logger.info('TopicTagRuleSetRunForm: for set %s and additional filter: %s, pretend: %s',
                    ruleset_id, topic_filter, pretend)
        rule_set = TopicTagRuleSet.objects.get(id=ruleset_id)
        # collect count of topics we ran for
        updated_set = set()
        updated_entities = {}
        updated_tags = {}
        removed_tags = {}
        new_equipments = []
        for rule in rule_set.topictagrule_set.all():
            rule_filters = rule.filters
            # Add the topic_filter to the rule filters if given
            if topic_filter:
                tf = {'type': 'c', 'value': topic_filter}
                if rule_filters:
                    rule_filters.append(tf)
                else:
                    rule_filters = [tf]
            if rule.tags:
                updated, updated_curr_entities, updated_curr_tags, removed_curr_tags = utils.tag_topics(
                    rule_filters, rule.tags, select_all=True, pretend=pretend)
                for x in updated:
                    updated_set.add(x.get('topic'))

                for key in updated_curr_entities.keys():
                    updated_curr_entity = updated_curr_entities.get(key, {})
                    topic = updated_curr_entity.topic
                    kv_tags = updated_curr_entity.kv_tags
                    m_tags = updated_curr_entity.m_tags
                    updated_entity = updated_entities.get(key, {})
                    updated_entity['topic'] = topic
                    updated_kv_tags = updated_entity.get('kv_tags', {})
                    updated_m_tags = updated_entity.get('m_tags', [])
                    for tag, value in kv_tags.items():
                        updated_kv_tags[tag] = value
                    for tag in m_tags:
                        if tag not in updated_m_tags:
                            updated_m_tags.append(tag)

                    updated_entity['kv_tags'] = updated_kv_tags
                    updated_entity['m_tags'] = updated_m_tags

                    updated_entities[key] = updated_entity

                for key, updated_curr_tag in updated_curr_tags.items():
                    updated_tag = updated_tags.get(key, {})
                    for tag, value in updated_curr_tag.items():
                        updated_tag[tag] = value
                    updated_tags[key] = updated_tag

                for key, removed_curr_tag in removed_curr_tags.items():
                    removed_tag = removed_tags.get(key, {})
                    for tag, value in removed_curr_tag.items():
                        removed_tag[tag] = value
                    removed_tags[key] = removed_tag

            if rule.action and rule.action_fields and not pretend:
                if rule.action == 'create equipment':
                    new_equipments = utils.create_equipment_action(rule_filters, rule.action_fields)

        return updated_set, updated_entities, preview_type, updated_tags, removed_tags, diff_format, new_equipments


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


class TopicTagRuleRunForm(forms.Form):
    rule_id = ModelField(label='Rule', max_length=255, required=True)
    topic_filter = ModelField(label='Topic Filter', max_length=255, required=False)
    preview_type = forms.CharField(required=False)
    diff_format = forms.BooleanField(label="Preview in a diff format", required=False, initial=False)

    def is_valid(self):
        if not super().is_valid():
            return False
        rule_id = self.cleaned_data['rule_id']
        if not TopicTagRule.objects.filter(id=rule_id).exists():
            logger.error('TopicTagRuleRunForm: rule %s not found.', rule_id)
            self.add_error('rule_id', 'Rule not found.')
            return False
        return True

    def save(self, commit=True):
        # run the topic tag ruleset
        topic_filter = self.cleaned_data['topic_filter']
        rule_id = self.cleaned_data['rule_id']
        preview_type = self.cleaned_data['preview_type']
        diff_format = self.cleaned_data['diff_format']

        pretend = False
        if preview_type:
            pretend = True

        logger.info('TopicTagRuleRunForm: for set %s and additional filter: %s, pretend: %s',
                    rule_id, topic_filter, pretend)
        rule = TopicTagRule.objects.get(id=rule_id)
        # collect count of topics we ran for
        updated_set = set()
        updated_entities = {}
        updated_tags = {}
        removed_tags = {}
        new_equipments = []
        rule_filters = rule.filters
        # Add the topic_filter to the rule filters if given
        if topic_filter:
            tf = {'type': 'c', 'value': topic_filter}
            if rule_filters:
                rule_filters.append(tf)
            else:
                rule_filters = [tf]
        if rule.tags:
            updated, updated_curr_entities, updated_curr_tags, removed_curr_tags = utils.tag_topics(
                rule_filters, rule.tags, select_all=True, pretend=pretend)
            for x in updated:
                updated_set.add(x.get('topic'))

            for key in updated_curr_entities.keys():
                updated_curr_entity = updated_curr_entities.get(key, {})
                topic = updated_curr_entity.topic
                kv_tags = updated_curr_entity.kv_tags
                m_tags = updated_curr_entity.m_tags
                updated_entity = updated_entities.get(key, {})
                updated_entity['topic'] = topic
                updated_kv_tags = updated_entity.get('kv_tags', {})
                updated_m_tags = updated_entity.get('m_tags', [])
                for tag, value in kv_tags.items():
                    updated_kv_tags[tag] = value
                for tag in m_tags:
                    if tag not in updated_m_tags:
                        updated_m_tags.append(tag)

                updated_entity['kv_tags'] = updated_kv_tags
                updated_entity['m_tags'] = updated_m_tags

                updated_entities[key] = updated_entity

            for key, updated_curr_tag in updated_curr_tags.items():
                updated_tag = updated_tags.get(key, {})
                for tag, value in updated_curr_tag.items():
                    updated_tag[tag] = value
                updated_tags[key] = updated_tag

            for key, removed_curr_tag in removed_curr_tags.items():
                removed_tag = removed_tags.get(key, {})
                for tag, value in removed_curr_tag.items():
                    removed_tag[tag] = value
                removed_tags[key] = removed_tag

        if rule.action and rule.action_fields and not pretend:
            if rule.action == 'create equipment':
                new_equipments = utils.create_equipment_action(rule_filters, rule.action_fields)

        return updated_set, updated_entities, preview_type, updated_tags, removed_tags, diff_format, new_equipments


class TopicAssocForm(forms.Form):
    topic = forms.CharField(max_length=255)
    site_id = forms.CharField(max_length=255)
    equipment_id = forms.CharField(max_length=255)
    data_point_name = forms.CharField(max_length=255)


class TopicExportForm(forms.Form):
    site = forms.ChoiceField(required=False)
    device_prefix = forms.CharField(required=False)
    only_with_trending = forms.BooleanField(label="Only export topics with Interval set", required=False, initial=True)
    his_tagged_topics_only = forms.BooleanField(label="Only export data points with his tag set",
                                                required=False, initial=False)

    def __init__(self, *args, **kwargs):
        site_id = kwargs.pop('site_id')
        super(TopicExportForm, self).__init__(*args, **kwargs)
        if not site_id:
            self.fields['site'] = forms.ChoiceField(choices=SiteView.get_choices())

    class Meta:
        fields = ["site_id", "device_prefix", "only_with_trending", "his_tagged_topics_only"]


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

                                    action = rule.get("action")
                                    if action:
                                        topic_tag_rule.action = action

                                    action_fields = rule.get("action_fields")
                                    if action_fields:
                                        topic_tag_rule.action_fields = action_fields

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


class TopicImportForm(forms.Form):
    site = forms.ChoiceField(required=True)
    device_prefix = forms.CharField(max_length=255)
    csv_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.csv'}))
    config_file = forms.FileField(widget=forms.FileInput(attrs={'accept': '.config'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site'] = forms.ChoiceField(choices=SiteView.get_choices())
        self.fields['device_prefix'].widget.attrs.update({'placeholder': 'eg: campus/building/device'})

    def save(self, commit=True):
        prefix = self.cleaned_data['device_prefix']
        file = self.cleaned_data['csv_file']
        config = self.cleaned_data['config_file']
        site_id = self.cleaned_data['site']
        import_count = 0
        error_count = 0
        logger.info('TopicImportForm: with prefix %s and file %s / %s / %s',
                    prefix, file.name, file.content_type, file.size)
        f = TextIOWrapper(file.file, encoding=file.charset if file.charset else 'utf-8')
        records = csv.DictReader(f)
        logger.info('TopicImportForm: with prefix %s and file %s / %s / %s',
                    prefix, config.name, config.content_type, config.size)
        fc = TextIOWrapper(config.file, encoding=config.charset if config.charset else 'utf-8')
        config_data = fc.read()

        import_errors = False
        import_success = False
        site = None
        if site_id:
            try:
                site = Entity.objects.get(entity_id=site_id)
            except TopicTagRuleSet.DoesNotExist:
                import_errors = 'Could not get site {}'.format(site_id)

        if site:
            for row in records:
                if 'Volttron Point Name' in row:
                    topic = '/'.join([prefix, row['Volttron Point Name']])
                    entity_id = utils.make_random_id(topic)
                    name = row['Volttron Point Name']
                    # create the topic if it does not exist in the Crate Database
                    Topic.ensure_topic_exists(topic)
                    # update or create the Data Point
                    try:
                        e = Entity.objects.get(topic=topic)
                    except Entity.DoesNotExist:
                        e = Entity(entity_id=entity_id, topic=topic)
                        e.add_tag('id', entity_id, commit=False)
                    e.add_tag('point', commit=False)
                    e.add_tag('dis', name, commit=False)
                    if site.kv_tags.get('id'):
                        e.add_tag('siteRef', site.kv_tags.get('id'), commit=False)
                    if row.get('Units'):
                        e.add_tag('unit', row['Units'], commit=False)

                    e.add_tag(Tag.bacnet_tag_prefix + 'prefix', prefix, commit=False)
                    # add all bacnet tags
                    for k, v in row.items():
                        field = k.lower()
                        field = field.replace(' ', '_')
                        if field == 'point_name':
                            field = 'reference_point_name'
                        if v:
                            e.add_tag(Tag.bacnet_tag_prefix + field, v, commit=False)
                    # add config file fields
                    try:
                        config_data_json = json.loads(config_data)
                    except Exception:
                        logging.error("Cannot parse bacnet_config json")
                    else:
                        for key in config_data_json.keys():
                            value = config_data_json.get(key)
                            field = key.lower()
                            field = field.replace(' ', '_')
                            if value:
                                if key == 'driver_config':
                                    for key1 in value.keys():
                                        value1 = value.get(key1)
                                        field = key1.lower()
                                        field = field.replace(' ', '_')
                                        e.add_tag(Tag.bacnet_tag_prefix + field, value1, commit=False)
                                else:
                                    if key == 'interval':
                                        e.add_tag(field, value, commit=False)
                                    else:
                                        e.add_tag(Tag.bacnet_tag_prefix + field, value, commit=False)

                    logger.info('TopicImportForm: imported Data Point %s as %s with topic %s', entity_id, name, topic)
                    e.save()
                    import_count += 1
                else:
                    error_count += 1
                    logger.error('TopicImportView cannot import row, no point name found, %s', row)

            import_success = 'Imported {} topics and Data Points with prefix {}'.format(import_count, prefix)
            if error_count:
                import_errors = 'Could not Import {} records.'.format(error_count)

        result = {}

        if import_errors:
            result['import_errors'] = import_errors
        if import_success:
            result['import_success'] = import_success

        return result
