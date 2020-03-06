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

from .base import OpentapsSeasTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from opentaps_seas.core.models import Entity, EntityNote, Tag


class ModelAPITests(OpentapsSeasTestCase):

    @classmethod
    def setUpTestData(cls):
        Tag.objects.get_or_create(tag='id', defaults={
            'kind': 'Ref',
            'description': 'ID'
            })
        Tag.objects.get_or_create(tag='modelRef', defaults={
            'kind': 'Ref',
            'description': 'Model Ref'
            })
        Tag.objects.get_or_create(tag='model', defaults={
            'kind': 'Marker',
            'description': 'Model'
            })
        Tag.objects.get_or_create(tag='dis', defaults={
            'kind': 'Str',
            'description': 'Display name'
            })

        Entity.objects.get_or_create(entity_id='@A', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'VA',
            'area': '1000ft²',
            'geoAddr': 'Richmond,VA',
            'tz': 'New_York',
            'id': '@A',
            'geoCity': 'Richmond',
            'dis': 'A'
        }})

    def setUp(self):
        self._cleanup_data()
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        Entity.objects.filter(entity_id__startswith='_test').delete()

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_list_requires_login(self):
        url = reverse('core:model_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_search(self):
        self._login()
        model_id = '_test/mymodel'

        create_url = reverse('core:model_create')
        data = {
            'entity_id': model_id + '1',
            'description': 'this is a test 2011 model 1'
            }
        self.client.post(create_url, data)
        data = {
            'entity_id': model_id + '2',
            'description': 'this is a better test small 2012 model 2'
            }
        self.client.post(create_url, data)
        data = {
            'entity_id': model_id + '3',
            'description': 'this is a worse test big 2013 model 2'
            }
        self.client.post(create_url, data)

        url = reverse('core:model_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(url + '?query=test')
        self.assertContains(response, model_id + '1')
        self.assertContains(response, model_id + '2')
        self.assertContains(response, model_id + '3')
        self.assertContains(response, '2011')
        self.assertContains(response, '2012')
        self.assertContains(response, '2013')

        response = self.client.get(url + '?query=better')
        self.assertNotContains(response, model_id + '1')
        self.assertContains(response, model_id + '2')
        self.assertNotContains(response, model_id + '3')
        self.assertNotContains(response, '2011')
        self.assertContains(response, '2012')
        self.assertNotContains(response, '2013')

        response = self.client.get(url + '?query=2013')
        self.assertNotContains(response, model_id + '1')
        self.assertNotContains(response, model_id + '2')
        self.assertContains(response, model_id + '3')
        self.assertNotContains(response, '2011')
        self.assertNotContains(response, '2012')
        self.assertContains(response, '2013')

    def test_list_json_requires_login(self):
        url = reverse('core:model_list_json')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_json(self):
        url = reverse('core:model_list_json')
        self._login()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')

    def test_create_requires_login(self):
        url = reverse('core:model_create')
        data = {'entity_id': '_test/mymodel', 'description': 'this is a test model'}
        response = self.client.post(url, data)
        self.assertEquals(response.status_code, 302)

    def test_create(self):
        model_id = '_test/mymodel'
        entity_id = slugify(model_id)
        note_content = 'test model note'
        create_url = reverse('core:model_create')
        view_url = reverse('core:model_detail', kwargs={"entity_id": entity_id})
        note_url = reverse('core:entity_note', kwargs={"entity_id": entity_id})
        self._login()

        data = {'entity_id': model_id, 'description': 'this is a test 2000 model'}
        response = self.client.post(create_url, data)
        self.assertRedirects(response, view_url)
        response = self.client.get(view_url, data)
        self.assertContains(response, 'this is a test 2000 model')

        data = {}
        response = self.client.post(create_url, data)
        self.assertFormError(response, 'form', 'entity_id', 'This field is required.')

        data = {'entity_id': model_id, 'description': 'another model ?'}
        response = self.client.post(create_url, data)
        self.assertFormError(response, 'form', 'entity_id', 'Model with this Model ID already exists.')

        data = {'entity_id': entity_id, 'content': note_content}
        response = self.client.post(note_url, data)
        self.assertEquals(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEquals(body['success'], 1)
        note = EntityNote.objects.filter(entity_id=entity_id).first()
        self.assertIsNotNone(note)
        self.assertEquals(note.content, note_content)

    def test_delete_requires_login(self):
        model_id = '_test/mymodel'
        entity_id = slugify(model_id)
        delete_url = reverse('core:model_delete', kwargs={"entity_id": entity_id})
        data = {'entity_id': model_id, 'description': 'this is a test model'}
        response = self.client.post(delete_url, data)
        self.assertEquals(response.status_code, 302)

    def test_delete(self):
        model_id = '_test/mymodel'
        entity_id = slugify(model_id)
        note_content = 'test model note'
        list_url = reverse('core:model_list')
        delete_url = reverse('core:model_delete', kwargs={"entity_id": entity_id})
        create_url = reverse('core:model_create')
        view_url = reverse('core:model_detail', kwargs={"entity_id": entity_id})
        note_url = reverse('core:entity_note', kwargs={"entity_id": entity_id})
        self._login()

        data = {'entity_id': model_id, 'description': 'this is a test model to delete'}
        response = self.client.post(create_url, data)
        self.assertRedirects(response, view_url)

        response = self.client.get(view_url, data)
        self.assertContains(response, 'Model {0}'.format(model_id))
        self.assertContains(response, 'this is a test model to delete')

        data = {'entity_id': entity_id, 'content': note_content}
        response = self.client.post(note_url, data)
        self.assertEquals(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEquals(body['success'], 1)
        note = EntityNote.objects.filter(entity_id=entity_id).first()
        self.assertIsNotNone(note)
        self.assertEquals(note.content, note_content)

        response = self.client.get(delete_url)
        self.assertContains(response, 'Model {0}'.format(model_id))
        self.assertContains(response, 'Are you sure you want to delete this Model?')

        response = self.client.post(delete_url)
        self.assertRedirects(response, list_url)
        response = self.client.get(list_url)
        self.assertNotContains(response, model_id)
        self.assertNotContains(response, 'this is a test model to delete')

        response = self.client.get(view_url, data)
        self.assertEquals(response.status_code, 404)

        note = EntityNote.objects.filter(entity_id=entity_id).first()
        self.assertIsNone(note)

    def test_model_apply_create_equipment(self):
        model_id = '_test/mymodel'
        equipment_id = '_test/myequipment'
        self._login()

        # create tags
        tag_create_url = reverse('core:tag_create')
        tag1 = {'tag': '_test/mytag1', 'description': 'this is a test tag', 'kind': 'Marker'}
        tag2 = {'tag': '_test/mytag2', 'description': 'this is a test tag', 'kind': 'Marker'}
        self.client.post(tag_create_url, tag1)
        self.client.post(tag_create_url, tag2)

        # create model
        model_data = {'entity_id': model_id, 'description': 'This is a test model'}
        model_create_url = reverse('core:model_create')
        self.client.post(model_create_url, model_data)
        # update created model's tags
        model_update_url = reverse('core:entity_tag', kwargs={'entity_id': slugify(model_id)})
        self.client.post(model_update_url, {'tag': '_test/mytag1'})
        self.client.post(model_update_url, {'tag': '_test/mytag2'})

        # create equipment with created model
        eq_data = {'entity_id': equipment_id, 'description': 'This is a test equipment',
                   'model': model_id, 'equipment_type': 'GENERIC'}
        eq_create_url = reverse('core:equipment_create', kwargs={'site': '@A'})
        self.client.post(eq_create_url, eq_data)

        # check model's tags applied to equipment's tags
        equipment = Entity.objects.get(entity_id=slugify(equipment_id))
        self.assertIn('_test/mytag1', equipment.m_tags)
        self.assertIn('_test/mytag2', equipment.m_tags)

    def test_model_apply_update_equipment(self):
        model_id = '_test/mymodel'
        equipment_id = '_test/myequipment'
        self._login()

        # create tags
        tag_create_url = reverse('core:tag_create')
        tag1 = {'tag': '_test/mytag1', 'description': 'this is a test tag', 'kind': 'Marker'}
        tag2 = {'tag': '_test/mytag2', 'description': 'this is a test tag', 'kind': 'Marker'}
        self.client.post(tag_create_url, tag1)
        self.client.post(tag_create_url, tag2)

        # create model
        model_data = {'entity_id': model_id, 'description': 'This is a test model'}
        model_create_url = reverse('core:model_create')
        self.client.post(model_create_url, model_data)
        # update created model's tags
        model_update_url = reverse('core:entity_tag', kwargs={'entity_id': slugify(model_id)})
        self.client.post(model_update_url, {'tag': '_test/mytag1'})
        self.client.post(model_update_url, {'tag': '_test/mytag2'})

        # create equipment without model
        eq_data = {'entity_id': equipment_id, 'description': 'This is a test equipment', 'equipment_type': 'GENERIC'}
        eq_create_url = reverse('core:equipment_create', kwargs={'site': '@A'})
        self.client.post(eq_create_url, eq_data)
        # update created equipment's model
        eq_update_url = reverse('core:entity_tag', kwargs={'entity_id': slugify(equipment_id)})
        eq_update_data = {
            'update': 1,
            'tag': 'modelRef',
            'value': model_id
        }
        self.client.post(eq_update_url, eq_update_data)

        # check model's tags applied to equipment's tags
        equipment = Entity.objects.get(entity_id=slugify(equipment_id))
        self.assertIn('_test/mytag1', equipment.m_tags)
        self.assertIn('_test/mytag2', equipment.m_tags)
