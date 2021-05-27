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
from ..models import Entity, EntityPermission
from ..models import TimeZone
from django import forms
from django.template.defaultfilters import slugify

logger = logging.getLogger(__name__)


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
        self.user = kwargs.pop('user')
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

        # Add permission for the current user (even if that user is Admin)
        permission = EntityPermission(entity_id=entity_id, user=self.user)
        permission.save()

        self.instance = Entity.objects.get(entity_id=entity_id)
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = Entity
        fields = ["entity_id", "description", "area", "address", "country", "state", "city", "timezone"]
