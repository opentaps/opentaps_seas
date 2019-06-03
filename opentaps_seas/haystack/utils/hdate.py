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

from .hval import HVal
from .common import ParseException


# HDate models a date (day in year) tag value.
class HDate(HVal):

    @classmethod
    def make(cls, year, month, day):
        if year < 1900:
            raise Exception("Invalid year " + year)
        if month < 1 or month > 12:
            raise Exception("Invalid month " + month)
        if day < 1 or day > 31:
            raise Exception("Invalid day " + day)
        return HDate(year, month, day)

    # Parse from string fomat "YYYY-MM-DD" or raise ParseException
    @classmethod
    def make_from_string(cls, s):
        if len(s) != len("YYYY-MM-DD"):
            raise ParseException(s)
        try:
            year = int(s.substring(0, 4))
        except Exception:
            raise ParseException("Invalid year: " + s)
        if s[4] != '-':
            raise ParseException(s)
        try:
            month = int(s.substring(5, 7))
        except Exception:
            raise ParseException("Invalid month: " + s)
        if s[7] != '-':
            raise ParseException(s)
        try:
            day = int(s.substring(8))
        except Exception:
            raise ParseException("Invalid day: " + s)
        return HDate.make(year, month, day)

    def __init__(self, year, month, day):
        super(HDate, self).__init__()
        self.year = year
        self.month = month
        self.day = day

    # Encode as "YYYY-MM-DD"
    def toZinc(self):
        return self.encode()

    # Package private implementation shared with HDateTime
    def encode(self):
        s = str(self.year) + '-'
        if (self.month < 10):
            s += '0'
        s += str(self.month) + '-'
        if (self.day < 10):
            s += '0'
        s += str(self.day)
        return s
