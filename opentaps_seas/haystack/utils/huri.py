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


#  * HUri models a URI as a string.
class HUri(HVal):
    #  Construct from string value
    @classmethod
    def make(cls, val):
        if len(val) == 0:
            return cls.EMPTY
        return HUri(val)

    #  Private constructor
    def __init__(self, val):
        super(HUri, self).__init__()
        self.val = val

    #  Return value string.
    def __str__(self):
        return self.val

    #  Encode using "`" back ticks
    def toZinc(self):
        s = '`'
        for c in self.val:
            if c < ' ':
                raise Exception("Invalid URI char '" + self.val + "', char='" + c + "'")
            if c == '`':
                s += '\\'
            s += c
        s += '`'
        return s


#  Singleton value for empty URI
HUri.EMPTY = HUri("")
