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
from django.db import models
from django.db.models import AutoField
from django.db.models import CharField
from django.contrib.postgres.fields import HStoreField
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class BaselineModel(models.Model):
    id = AutoField(_("Baseline Model ID"), primary_key=True, auto_created=True)
    model_class = CharField(_("Model Class"), blank=False, null=False, max_length=512)
    data = HStoreField(blank=True, null=True)
