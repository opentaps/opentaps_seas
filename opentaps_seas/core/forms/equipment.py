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
import solaredge
from .. import tasks
from .. import utils
from ..models import Entity
from ..models import Meter
from ..models import ModelView
from ..models import Tag
from ..models import SolarEdgeSetting
from django import forms
from django.template.defaultfilters import slugify
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class EquipmentCreateForm(forms.ModelForm):
    entity_id = forms.CharField(label='Equipment ID', max_length=255, required=False)
    equipment_type = forms.ChoiceField(label='Type', required=True, choices=(
        ('GENERIC', 'Generic Equipment'),
        ('SOLAREDGE', 'SolarEdge')))
    solaredge_api_key = forms.CharField(label='SolarEdge API Key', max_length=255, required=False)
    solaredge_site_id = forms.CharField(label='SolarEdge Site ID', max_length=255, required=False)
    description = forms.CharField(max_length=255, required=True)
    model = forms.ChoiceField(required=False)
    bacnet_prefix = forms.CharField(max_length=255, required=False)
    device_id = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.site_id = kwargs.pop('site_id')
        super().__init__(*args, **kwargs)
        self.fields['model'] = forms.ChoiceField(choices=ModelView.get_choices(), required=False)

    def is_valid(self):
        if not super().is_valid():
            return False
        # when setting a SolarEdge equipment then API key and Site ID are required
        if self.cleaned_data['equipment_type'] == 'SOLAREDGE':
            se_err = False
            if 'solaredge_api_key' not in self.cleaned_data or not self.cleaned_data['solaredge_api_key']:
                self.add_error('solaredge_api_key', 'Required')
                se_err = True
            if 'solaredge_site_id' not in self.cleaned_data or not self.cleaned_data['solaredge_site_id']:
                self.add_error('solaredge_site_id', 'Required')
                se_err = True
            # make sure the API works
            try:
                se = solaredge.Solaredge(self.cleaned_data['solaredge_api_key'])
                se.get_overview(self.cleaned_data['solaredge_site_id'])
            except HTTPError as e:
                # Need to check its an 404, 503, 500, 403 etc.
                logger.exception(e)
                se_err = True
                status_code = e.response.status_code
                if status_code == 403:
                    self.add_error('solaredge_api_key', 'Invalid API Key')
                if status_code == 400:
                    self.add_error('solaredge_site_id', 'Invalid Site ID')
            except Exception as e:
                logger.exception(e)
                self.add_error('solaredge_api_key', 'Check API Key')
                self.add_error('solaredge_site_id', 'Check Site ID')
                self.add_error(None, 'SolarEdge {} check the API Key and Site ID are correct.'.format(e))
                se_err = True
            if se_err:
                return False
        return True

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

        # check we can get the SolarEdge data if configured ofr before saving entities..
        site = Entity.objects.get(kv_tags__id=self.site_id)
        site_details = {}
        if 'equipment_type' in self.cleaned_data and self.cleaned_data['equipment_type'] == 'SOLAREDGE':
            kwargs = self.cleaned_data.copy()
            kwargs['entity_id'] = entity_id
            kwargs['site_id'] = self.site_id
            kwargs['user'] = self.user
            async_res = tasks.fetch_solaredge_for_equipment_task.delay(kwargs)
            site_details['task_id'] = async_res.task_id

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

        if 'equipment_type' in self.cleaned_data and self.cleaned_data['equipment_type'] == 'SOLAREDGE':
            # create a meter based on the SolarEdge site
            m = Meter.objects.create(
                meter_id=entity_id,
                site=site,
                equipment=equipment,
                description='SolarEdge: ...')
            # store the solarEdge api kye and siteId, encrypt the key
            SolarEdgeSetting.objects.create(
                entity_id=entity_id,
                meter=m,
                site_details=site_details,
                site_id=self.cleaned_data['solaredge_site_id'],
                api_key=self.cleaned_data['solaredge_api_key'])

        self._post_clean()
        return self.instance

    class Meta:
        model = Entity
        fields = ["entity_id", "description", "model"]
