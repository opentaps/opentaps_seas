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


# HBool defines singletons for true/false tag values.
class HBool(HVal):
    #  Construct from boolean value
    @classmethod
    def make(cls, val):
        return cls.TRUE if val else cls.FALSE

    # Private constructor
    def __init__(self, val):
        super(HBool, self).__init__()
        self.val = val

    #  Encode as "true" or "false"
    def __str__(self):
        return "true" if self.val else "false"

    #  Encode as "T" or "F"
    def toZinc(self):
        return "T" if self.val else "F"


#  Singleton value for true
HBool.TRUE = HBool(True)
HBool.FALSE = HBool(False)
