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

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_entity_views'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('tag', models.CharField(max_length=255, primary_key=True)),
                ('kind', models.CharField(max_length=255, blank=True)),
                ('description', models.CharField(max_length=255, blank=True, null=True)),
                ('details', models.CharField(max_length=512, blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
