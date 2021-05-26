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

from django.conf import settings
from django.db import models, migrations
from django.db.models import deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_auto_20210211_1444'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntityPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True)),
                ('entity_id', models.CharField(max_length=255, verbose_name='Entity ID')),
                ('user', models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
