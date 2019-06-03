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

from datetime import datetime
from datetime import timezone
from dateutil.parser import parse as parse_datetime

from .hval import HVal


# HDateTime models a timestamp with a specific timezone.
class HDateTime(HVal):

    # Parse from string fomat "YYYY-MM-DD'T'hh:mm:ss.FFFz zz
    @classmethod
    def make(cls, date):
        return HDateTime(date)

    # Parse from string fomat "YYYY-MM-DD'T'hh:mm:ss.FFFz zz
    @classmethod
    def make_from_string(cls, s):
        date = parse_datetime(s)
        return HDateTime.make(date)

    # Get HDateTime for current time in default timezone
    @classmethod
    def now(cls):
        t = datetime.utcnow().replace(tzinfo=timezone.utc)
        return cls.make(t)

    # Encode as "YYYY-MM-DD'T'hh:mm:ss.FFFz zzzz"
    def toZinc(self):
        return self.encode()

    def encode(self):
        return self.date.isoformat()
