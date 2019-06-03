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

import math
import re
from .hval import HVal


# HNum wraps a 64-bit floating point number and optional unit name.
class HNum(HVal):

    @classmethod
    def make(cls, val, unit=None):
        val = cls.to_num(val)
        if (val == 0 and unit is None):
            return cls.ZERO
        return HNum(val, unit)

    @classmethod
    def to_num(cls, val, error=False):
        if val is None:
            return math.nan
        if isinstance(val, str):
            try:
                val = float(re.sub("[^0-9-]", "", val))
            except Exception:
                if error:
                    raise
                pass
        return val

    # Private constructor */
    def __init__(self, val, unit):
        if not self.isUnitName(unit):
            raise Exception("Invalid unit name: " + unit)
        self.val = self.to_num(val)
        self.unit = unit

    # Encode as floating value followed by optional unit string */
    def toZinc(self):
        return self.encode(False)

    def encode(self, spaceBeforeUnit):
        if self.val == math.inf:
            return "INF"
        elif self.val == -math.inf:
            return "-INF"
        elif math.isnan(self.val):
            return "NaN"
        else:
            # don't encode huge set of decimals if over 1.0
            s = ''
            if math.fabs(self.val) > 1.0:
                s = "%.4f" % self.val
            else:
                s = str(self.val)

            if self.unit is not None:
                if spaceBeforeUnit:
                    s += ' '
                s += self.unit
        return s

    # default implementations compare the string values
    # so here we compare the numeric (float) values if possible
    def __eq__(self, other):
        try:
            return self.val == self.to_num(other, True)
        except Exception:
            return str(self) == str(other)

    def __ne__(self, other):
        try:
            return self.val != self.to_num(other, True)
        except Exception:
            return str(self) != str(other)

    def __lt__(self, other):
        try:
            return self.val < self.to_num(other, True)
        except Exception:
            return str(self) < str(other)

    def __le__(self, other):
        try:
            return self.val <= self.to_num(other, True)
        except Exception:
            return str(self) <= str(other)

    def __gt__(self, other):
        try:
            return self.val > self.to_num(other, True)
        except Exception:
            return str(self) > str(other)

    def __ge__(self, other):
        try:
            return self.val >= self.to_num(other, True)
        except Exception:
            return str(self) >= str(other)

    # Return true if the given string is null or contains only valid unit
    # chars.  If the unit name contains invalid chars return false.  This
    # method does *not* check that the unit name is part of the standard
    # unit database.
    @classmethod
    def isUnitName(cls, unit):
        if unit is None:
            return True
        if len(unit) == 0:
            return False
        for c in unit:
            i = ord(c)
            if not cls.unitChars.get(i, False):
                return False
        return True

    unitChars = {}
    for i in range(ord('a'), ord('z') + 1):
        unitChars[i] = True
    for i in range(ord('A'), ord('Z') + 1):
        unitChars[i] = True
    unitChars[ord('_')] = True
    unitChars[ord('$')] = True
    unitChars[ord('%')] = True
    unitChars[ord('/')] = True


HNum.ZERO = HNum(0.0, None)
HNum.POS_INF = HNum(math.inf, None)
HNum.NEG_INF = HNum(-math.inf, None)
HNum.NaN = HNum(math.nan, None)
