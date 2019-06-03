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

import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from opentaps_seas.core.models import Entity
from opentaps_seas.core.models import Tag


class TagsAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Tag.objects.get_or_create(tag='ac', defaults={
            'kind': 'Marker',
            'description': 'AC'
            })
        Tag.objects.get_or_create(tag='active', defaults={
            'kind': 'Marker',
            'description': 'Active power'
            })
        Tag.objects.get_or_create(tag='entering', defaults={
            'kind': 'Marker',
            'description': 'Water or steam entering boiler or chiller'
            })
        Tag.objects.get_or_create(tag='makeup', defaults={
            'kind': 'Marker',
            'description': 'Makeup water in cooling tower boiler',
            'details': 'Paired with water to indicate control or measurement of the makeup water in a coolingToweror boiler used to replace water lost through leaks, evaporation, or blowdown'
            })

    def setUp(self):
        self._cleanup_data()
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        Tag.objects.filter(tag__startswith='_test').delete()
        Entity.objects.filter(entity_id__startswith='_test').delete()

    def _create_model(self, model_id, description):
        Entity.objects.create(entity_id=model_id, m_tags=['model'], kv_tags={'id': model_id, 'dis': description})

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_list_requires_login(self):
        url = reverse('core:tag_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_search(self):
        self._login()
        url = reverse('core:tag_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(url + '?query=boiler')
        self.assertContains(response, 'Water or steam entering boiler or chiller')
        self.assertContains(response, 'Makeup water in cooling tower boiler')
        self.assertNotContains(response, 'Active power')

    def test_list_json_requires_login(self):
        url = reverse('core:tag_list_json')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_json(self):
        url = reverse('core:tag_list_json')
        self._login()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 4,
                          msg='Expected at least 4 tags to be listed, got {0}'.format(len(data['items'])))

    def test_create_requires_login(self):
        url = reverse('core:tag_create')
        tag = {'tag': '_test/mytag', 'description': 'this is a test tag', 'kind': 'Str'}
        response = self.client.post(url, tag)
        self.assertEquals(response.status_code, 302)

    def test_create(self):
        tag_id = '_test/mytag'
        create_url = reverse('core:tag_create')
        view_url = reverse('core:tag_detail', kwargs={"tag": tag_id})
        self._login()

        tag = {'tag': tag_id, 'description': 'this is a test tag', 'kind': 'Str'}
        response = self.client.post(create_url, tag)
        self.assertRedirects(response, view_url)
        response = self.client.get(view_url, tag)
        self.assertContains(response, 'this is a test tag')

        tag = {}
        response = self.client.post(create_url, tag)
        self.assertFormError(response, 'form', 'tag', 'This field is required.')
        self.assertFormError(response, 'form', 'kind', 'This field is required.')

        tag = {'tag': tag_id, 'description': 'another tag ?', 'kind': 'Ref'}
        response = self.client.post(create_url, tag)
        self.assertFormError(response, 'form', 'tag', 'Tag with this Tag Name already exists.')

        tag = {'tag': '_test/mytag2', 'description': 'another tag ?', 'kind': 'DoesNotExist'}
        response = self.client.post(create_url, tag)
        self.assertFormError(response, 'form', 'kind',
                             'Select a valid choice. DoesNotExist is not one of the available choices.')

    def test_delete_requires_login(self):
        tag_id = '_test/mytag'
        delete_url = reverse('core:tag_delete', kwargs={"tag": tag_id})
        tag = {'tag': tag_id, 'description': 'this is a test tag', 'kind': 'Str'}
        response = self.client.post(delete_url, tag)
        self.assertEquals(response.status_code, 302)

    def test_delete(self):
        tag_id = '_test/mytag'
        list_url = reverse('core:tag_list')
        delete_url = reverse('core:tag_delete', kwargs={"tag": tag_id})
        create_url = reverse('core:tag_create')
        view_url = reverse('core:tag_detail', kwargs={"tag": tag_id})
        self._login()

        tag = {'tag': tag_id, 'description': 'this is a test tag to delete', 'kind': 'Str'}
        response = self.client.post(create_url, tag)
        self.assertRedirects(response, view_url)

        response = self.client.get(view_url, tag)
        self.assertContains(response, 'Tag {0}'.format(tag_id))
        self.assertContains(response, 'this is a test tag to delete')

        response = self.client.get(delete_url)
        self.assertContains(response, 'Tag {0}'.format(tag_id))
        self.assertContains(response, 'Are you sure you want to delete this Tag?')

        response = self.client.post(delete_url)
        self.assertRedirects(response, list_url)
        response = self.client.get(list_url)
        self.assertNotContains(response, tag_id)
        self.assertNotContains(response, 'this is a test tag to delete')

        response = self.client.get(view_url, tag)
        self.assertEquals(response.status_code, 404)

    def test_delete_used_tags(self):
        tag_id = '_test/mytag'
        entity_id = '_test/testmodeltag'
        view_url = reverse('core:tag_detail', kwargs={"tag": tag_id})
        delete_url = reverse('core:tag_delete', kwargs={"tag": tag_id})
        create_url = reverse('core:tag_create')
        self._login()
        self._create_model(entity_id, 'A test model')

        tag_data = {'tag': tag_id, 'description': 'this is a test tag to delete', 'kind': 'Str'}
        response = self.client.post(create_url, tag_data)
        self.assertRedirects(response, reverse('core:tag_detail', kwargs={"tag": tag_id}))

        tag_data = {'tag': tag_id + '2', 'description': 'this is a test marker tag to delete', 'kind': 'Marker'}
        response = self.client.post(create_url, tag_data)
        self.assertRedirects(response, reverse('core:tag_detail', kwargs={"tag": tag_id + '2'}))

        tag_url = reverse('core:entity_tag', kwargs={'entity_id': entity_id})
        response = self.client.post(tag_url, {'entity_id': entity_id,
                                              'tag': tag_id,
                                              'value': 'test value'})
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('results' in data, msg='Expected the JSON response to include results')
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')

        response = self.client.post(tag_url, {'entity_id': entity_id,
                                              'tag': tag_id + '2'})
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('results' in data, msg='Expected the JSON response to include results')
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')

        tag = Tag.objects.get(tag=tag_id)
        self.assertTrue(isinstance(tag, Tag))
        self.assertEquals(tag.get_use_count(), 1)
        self.assertFalse(tag.can_delete())

        tag2 = Tag.objects.get(tag=tag_id + '2')
        self.assertTrue(isinstance(tag2, Tag))
        self.assertEquals(tag2.get_use_count(), 1)
        self.assertFalse(tag2.can_delete())

        response = self.client.get(view_url)
        self.assertContains(response, 'This tag is being used and cannot be deleted.')

        response = self.client.get(delete_url)
        self.assertContains(response, 'This Tag is being used and cannot be deleted.')

        response = self.client.post(delete_url, follow=True)
        self.assertRedirects(response, reverse('core:tag_detail', kwargs={"tag": tag_id}))
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Can not delete: this Tag is being used!')

        response = self.client.post(tag_url, {'entity_id': entity_id,
                                              'delete': 1,
                                              'tag': tag_id,
                                              'value': 'test value'})
        self.assertEquals(response.status_code, 200)

        tag = Tag.objects.get(tag=tag_id)
        self.assertTrue(isinstance(tag, Tag))
        self.assertEquals(tag.get_use_count(), 0)
        self.assertTrue(tag.can_delete())

        tag2 = Tag.objects.get(tag=tag_id + '2')
        self.assertTrue(isinstance(tag2, Tag))
        self.assertEquals(tag2.get_use_count(), 1)
        self.assertFalse(tag2.can_delete())

        response = self.client.post(tag_url, {'entity_id': entity_id,
                                              'delete': 1,
                                              'tag': tag_id + '2'})
        self.assertEquals(response.status_code, 200)

        tag2 = Tag.objects.get(tag=tag_id + '2')
        self.assertTrue(isinstance(tag2, Tag))
        self.assertEquals(tag2.get_use_count(), 0)
        self.assertTrue(tag2.can_delete())
