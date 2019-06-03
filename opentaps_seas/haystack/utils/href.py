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
from .hstr import HStr


#  * HRef wraps a string reference identifier and optional display name.
class HRef(HVal):
    #  Construct for string identifier and optional display
    @classmethod
    def make(cls, val, dis=None):
        if val is None or not cls.isId(val):
            raise Exception("Invalid id val: \"" + val + "\"")
        return HRef(val, dis)

    # Private constructor
    def __init__(self, val, dis):
        super(HRef, self).__init__()
        self.val = val
        self.dis = dis

    #  Return display string which is dis field if non-null, val field otherwise
    def dis(self):
        if self.dis is not None:
            return self.dis
        return self.val

    #  Return the val string
    def __str__(self):
        return self.val

    #  Encode as "@<id> [dis]"
    def toZinc(self):
        s = '@' + self.val
        if self.dis is not None:
            s += ' ' + HStr.toZinc(self.dis)
        return s

    #  Return if the given string is a valid id for a reference
    @classmethod
    def isId(cls, _id):
        if len(_id) == 0:
            return False

        for c in _id:
            if not cls.isIdChar(c):
                return False
        return True

    #  Is the given character valid in the identifier part
    @classmethod
    def isIdChar(cls, ch):
        print('?? Href::isIdChar ? ', ch)
        if ch is None:
            return False
        if (isinstance(ch, str)):
            ch = ord(ch)
        return cls.idChars.get(ch, False)

    idChars = {}
    for i in range(ord('a'), ord('z') + 1):
        idChars[i] = True
    for i in range(ord('A'), ord('Z') + 1):
        idChars[i] = True
    for i in range(ord('0'), ord('9') + 1):
        idChars[i] = True
    idChars[ord('_')] = True
    idChars[ord(':')] = True
    idChars[ord('-')] = True
    idChars[ord('.')] = True
    idChars[ord('~')] = True
    # allow '@' in id, which are then referenced as @@ID if the id is @ID
    idChars[ord('@')] = True


#  Singleton for the null ref
HRef.nullRef = HRef("null", None)
