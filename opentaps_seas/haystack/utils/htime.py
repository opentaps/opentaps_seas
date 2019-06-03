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


# HTime models a time of day tag value.
class HTime(HVal):
    # Construct with all fields
    @classmethod
    def make(cls, hour, minute, sec=0, ms=0):
        if hour < 0 or hour > 23:
            raise Exception("Invalid hour")
        if minute < 0 or minute > 59:
            raise Exception("Invalid min")
        if sec < 0 or sec > 59:
            raise Exception("Invalid sec")
        if ms < 0 or ms > 999:
            raise Exception("Invalid ms")
        return HTime(hour, minute, sec, ms)

    # Parse from string fomat "hh:mm:ss.FF" or raise ParseException */
    @classmethod
    def make_from_string(cls, s):
        err = ParseException(s)
        try:
            hour = int(s[0:2])
        except Exception:
            raise ParseException("Invalid hours: " + s)
        if s[2] != ':':
            raise err
        try:
            minute = int(s[3:5])
        except Exception:
            raise ParseException("Invalid minutes: " + s)
        if s[5] != ':':
            raise err
        try:
            sec = int(s[6:8])
        except Exception:
            raise ParseException("Invalid seconds: " + s)
        if len(s) == len("hh:mm:ss"):
            return HTime.make(hour, min, sec)
        if s[8] != '.':
            raise err
        ms = 0
        pos = 9
        places = 0
        _len = len(s)
        # HTime only stores ms precision, so truncate anything after that
        while (pos < _len and places < 3):
            ms = (ms * 10) + (s[pos] - '0')
            pos += 1
            places += 1
        if places == 1:
            ms *= 100
        elif places == 2:
            ms *= 10
        elif places == 3:
            pass
        else:
            raise Exception("Too much fractional precision: " + s)
        return HTime.make(hour, minute, sec, ms)

    # Private constructor */
    def __init__(self, h, m, s, ms):
        super(HTime, self).__init__()
        self.hour = h
        self.min = m
        self.sec = s
        self.ms = ms

    # Encode as "hh:mm:ss.FFF" */
    def toZinc(self):
        return self.encode()

    # Package private implementation shared with HDateTime */
    def encode(self):
        s = ''
        if self.hour < 10:
            s += '0'
        s += str(self.hour) + ':'
        if self.min < 10:
            s += '0'
        s += str(self.min) + ':'
        if self.sec < 10:
            s += '0'
        s += str(self.sec)
        if self.ms:
            s += '.'
            if self.ms < 10:
                s += '0'
            if self.ms < 100:
                s += '0'
            s += str(self.ms)
