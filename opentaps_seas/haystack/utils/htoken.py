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


class HaystackToken(object):

    def __init__(self, symbol, literal=False):
        """ generated source for method __init___0 """
        self.symbol = symbol
        self.literal = literal

    def __str__(self):
        """ generated source for method toString """
        return self.symbol


HaystackToken.eof = HaystackToken("eof")
HaystackToken.id = HaystackToken("identifier")
HaystackToken.num = HaystackToken("Number", True)
HaystackToken.str_ = HaystackToken("Str", True)
HaystackToken.ref = HaystackToken("Ref", True)
HaystackToken.uri = HaystackToken("Uri", True)
HaystackToken.date = HaystackToken("Date", True)
HaystackToken.time = HaystackToken("Time", True)
HaystackToken.dateTime = HaystackToken("DateTime", True)
HaystackToken.colon = HaystackToken(":")
HaystackToken.comma = HaystackToken(",")
HaystackToken.semicolon = HaystackToken(";")
HaystackToken.minus = HaystackToken("-")
HaystackToken.eq = HaystackToken("==")
HaystackToken.notEq = HaystackToken("!=")
HaystackToken.lt = HaystackToken("<")
HaystackToken.lt2 = HaystackToken("<<")
HaystackToken.ltEq = HaystackToken("<=")
HaystackToken.gt = HaystackToken(">")
HaystackToken.gt2 = HaystackToken(">>")
HaystackToken.gtEq = HaystackToken(">=")
HaystackToken.lbracket = HaystackToken("[")
HaystackToken.rbracket = HaystackToken("]")
HaystackToken.lbrace = HaystackToken("{")
HaystackToken.rbrace = HaystackToken("}")
HaystackToken.lparen = HaystackToken("(")
HaystackToken.rparen = HaystackToken(")")
HaystackToken.arrow = HaystackToken("->")
HaystackToken.slash = HaystackToken("/")
HaystackToken.assign = HaystackToken("=")
HaystackToken.bang = HaystackToken("!")
HaystackToken.nl = HaystackToken("newline")
