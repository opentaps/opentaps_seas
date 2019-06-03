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


#  * HStr wraps a java.lang.String as a tag value.
class HStr(HVal):
    #  Construct from java.lang.String value
    @classmethod
    def make(cls, val):
        if val is None:
            return None
        if len(val) == 0:
            return cls.EMPTY
        return HStr(val)

    #  Private constructor
    def __init__(self, val):
        super(HStr, self).__init__()
        self.val = val

    #  Return value string.
    def __str__(self):
        return self.val

    #  Encode using double quotes and back slash escapes
    @classmethod
    def toCode(cls, val):
        s = '"'
        for c in val:
            if c < ' ' or c == '"' or c == '\\':
                s += '\\'
                if c == '\n':
                    s += 'n'
                elif c == '\r':
                    s += 'r'
                elif c == '\t':
                    s += 't'
                elif c == '"':
                    s += '"'
                elif c == '\\':
                    s += '\\'
                else:
                    s += 'u00'
                    if ord(c) <= 0xf:
                        s += '0'
                    s += hex(ord(c))
            else:
                s += c
        s += '"'
        return s

    #  Encode using double quotes and back slash escapes
    def toZinc(self):
        return self.toCode(self.val)


#  Singleton value for empty string ""
HStr.EMPTY = HStr("")
