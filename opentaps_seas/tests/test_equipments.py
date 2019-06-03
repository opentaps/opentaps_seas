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
import os

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from opentaps_seas.core.models import Entity
from opentaps_seas.core.models import Tag
from django.core.files.uploadedfile import SimpleUploadedFile


class EquipmentAPITests(TestCase):

    def setUp(self):
        self._cleanup_data()
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')
        # we need at least a clean test Equipment to manipulate
        # note they do not support a _test/bar pattern so use _test_bar instead
        self.equipment_id = '_test_myequipment'
        self.model_id = '_test/mymodel'

    def tearDown(self):
        self._cleanup_data()

    def _create_model(self, model_id, description):
        Entity.objects.create(entity_id=model_id, m_tags=['model'], kv_tags={
            'id': model_id, 'dis': description})

    def _create_equipment(self, equipment_id, description):
        Entity.objects.create(entity_id=equipment_id, m_tags=['equip'], kv_tags={
            'id': equipment_id, 'dis': description})

    def _cleanup_data(self):
        Entity.objects.filter(entity_id__startswith='_test').delete()

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_list_requires_login(self):
        url = reverse('core:equipment_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_search(self):
        self._login()
        url = reverse('core:equipment_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_list_json_requires_login(self):
        url = reverse('core:equipment_list_json')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_json(self):
        url = reverse('core:equipment_list_json')
        self._login()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')

    def test_related_notes_requires_login(self):
        url = reverse('core:entity_note', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_related_notes(self):
        self._create_equipment(self.equipment_id, 'A test equipment')
        self._login()

        url = reverse('core:entity_note', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 0, msg='Expected the JSON response to include zero notes in results')

        note_content = 'A test note'
        post = {'entity_id': self.equipment_id, 'content': note_content}
        response = self.client.post(url, post)
        self.assertEquals(response.status_code, 200)
        data = response.json()
        self.assertTrue('results' in data, msg='Expected the JSON response to include results')
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')
        self.assertEquals(len(data['results']), 1, msg='Expected the JSON response to include 1 note in results')
        note_id = data['results'][0]['id']
        note_created = data['results'][0]['created']
        self.assertJSONEqual(response.content, {'success': 1, 'results': [{
            'id': note_id,
            'content': note_content,
            'owner': 'temporary',
            'created': note_created
        }]})

        note2_content = 'Another test note'
        post = {'entity_id': self.equipment_id, 'content': note2_content}
        response = self.client.post(url, post)
        self.assertEquals(response.status_code, 200)
        data = response.json()
        self.assertTrue('results' in data, msg='Expected the JSON response to include results')
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')
        self.assertEquals(len(data['results']), 1, msg='Expected the JSON response to include 1 note in results')
        note2_id = data['results'][0]['id']
        note_created = data['results'][0]['created']
        self.assertJSONEqual(response.content, {'success': 1, 'results': [{
            'id': note2_id,
            'content': note2_content,
            'owner': 'temporary',
            'created': note_created
        }]})

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 2, msg='Expected the JSON response to include 2 notes in results')

    def test_related_link_requires_login(self):
        url = reverse('core:entity_link', kwargs={'entity_id': self.equipment_id})
        response = self.client.post(url, {'entity_id': self.equipment_id})
        self.assertEquals(response.status_code, 302)

    def test_related_links(self):
        self._create_equipment(self.equipment_id, 'A test equipment')
        self._login()

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url_file)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 0, msg='Expected the JSON response to include zero links in results')

        url = reverse('core:entity_link', kwargs={'entity_id': self.equipment_id})

        post = {'entity_id': self.equipment_id, 'link_name': 'example',
                'link': 'http://example.com/', 'comments': 'example comment'}

        response = self.client.post(url, post)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data['success'], 1)
        comments = data['results'][0]['comments']
        owner = data['results'][0]['owner']
        url = data['results'][0]['url']
        name = data['results'][0]['name']
        self.assertEquals(comments, 'example comment')
        self.assertEquals(url, 'http://example.com/')
        self.assertEquals(name, 'example')
        self.assertEquals(owner, 'temporary')

        post = {'entity_id': self.equipment_id, 'link_name': 'another example',
                'link': 'http://example.com/', 'comments': 'another example comment'}

        url = reverse('core:entity_link', kwargs={'entity_id': self.equipment_id})
        response = self.client.post(url, post)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data['success'], 1)
        comments = data['results'][0]['comments']
        owner = data['results'][0]['owner']
        url = data['results'][0]['url']
        name = data['results'][0]['name']
        self.assertEquals(comments, 'another example comment')
        self.assertEquals(url, 'http://example.com/')
        self.assertEquals(name, 'another example')
        self.assertEquals(owner, 'temporary')

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url_file)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 2, msg='Expected the JSON response to include 2 links in results')

    def test_related_files_requires_login(self):
        url = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_related_files(self):
        self._create_equipment(self.equipment_id, 'A test equipment')
        self._login()

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url_file)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 0, msg='Expected the JSON response to include zero links in results')

        url = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        module_dir = os.path.dirname(__file__)
        f = SimpleUploadedFile(module_dir + '/test.jpg', b'file_content', content_type='image/jpeg')

        post = {'entity_id': self.equipment_id, 'comments': 'example file'}
        post['uploaded_file'] = f

        response = self.client.post(url, post)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data['success'], 1)

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url_file)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        items = data['items']
        self.assertEquals(len(items), 1, msg='Expected the JSON response to include 1 links in results')

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        delete = {'id': items[0]['id'], 'entity_id': self.equipment_id, 'delete': 1}
        response = self.client.post(url, delete)
        self.assertEquals(response.status_code, 200)

        url_file = reverse('core:entity_file_upload', kwargs={'entity_id': self.equipment_id})
        response = self.client.get(url_file)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 0, msg='Expected the JSON response to include zero links in results')

    def test_related_notes_inherit_from_model(self):
        self._create_equipment(self.equipment_id, 'A test equipment')
        self._create_model(self.model_id, 'A test model')
        Tag.objects.get_or_create(tag='modelRef', defaults={'kind': 'Ref'})
        self._login()

        # first add a couple of note to the model
        url = reverse('core:entity_note', kwargs={'entity_id': self.model_id})
        response = self.client.post(url, {'entity_id': self.model_id, 'content': 'A Model test note 1'})
        self.assertEquals(response.status_code, 200)
        response = self.client.post(url, {'entity_id': self.model_id, 'content': 'A Model test note 2'})
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 2, msg='Expected the JSON response to include 2 notes in results')

        # add a note to the equipment
        url = reverse('core:entity_note', kwargs={'entity_id': self.equipment_id})
        response = self.client.post(url, {'entity_id': self.equipment_id, 'content': 'The Equipment test note 1'})
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 1, msg='Expected the JSON response to include 1 note in results')

        # link the model and equipment
        tag_url = reverse('core:entity_tag', kwargs={'entity_id': self.equipment_id})
        response = self.client.post(tag_url, {'entity_id': self.equipment_id,
                                              'tag': 'modelRef',
                                              'value': self.model_id})
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('results' in data, msg='Expected the JSON response to include results')
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')

        # get the notes for the Equipment which should now include the Model notes
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 3, msg='Expected the JSON response to include 3 notes in results')
        self.assertContains(response, 'A Model test note 1')
        self.assertContains(response, 'A Model test note 2')
        self.assertContains(response, 'The Equipment test note 1')

        # unlink the model and equipment
        response = self.client.post(tag_url, {'entity_id': self.equipment_id,
                                              'delete': 1,
                                              'tag': 'modelRef',
                                              'value': self.model_id})
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('success' in data, msg='Expected the JSON response to include success flag')

        # get the notes for the Equipment which should no longer include the Model notes
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertEquals(len(data['items']), 1, msg='Expected the JSON response to include 1 note in results')
        self.assertNotContains(response, 'A Model test note 1')
        self.assertNotContains(response, 'A Model test note 2')
        self.assertContains(response, 'The Equipment test note 1')
