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


from django.test import TestCase
from opentaps_seas.eemeter import utils
from opentaps_seas.eemeter import models


class EEMeterTests(TestCase):

    def test_hourly_model_serialization(self):
        d = utils.get_hourly_sample_data()
        m = utils.get_hourly_model(d)
        i = utils.save_model(m)
        m2 = utils.load_model(i)

        s = utils.get_savings(d, m)
        s2 = utils.get_savings(d, m2)

        self.assertEquals(s, s2)

        i2 = models.BaselineModel.objects.get(id=i.id)
        m2 = utils.load_model(i2)
        s2 = utils.get_savings(d, m2)

        self.assertEquals(s, s2)

    def test_daily_model_serialization(self):
        d = utils.get_daily_sample_data()
        m = utils.get_daily_model(d)
        i = utils.save_model(m)
        m2 = utils.load_model(i)

        s = utils.get_savings(d, m)
        s2 = utils.get_savings(d, m2)

        self.assertEquals(s, s2)

        i2 = models.BaselineModel.objects.get(id=i.id)
        m2 = utils.load_model(i2)
        s2 = utils.get_savings(d, m2)

        self.assertEquals(s, s2)
