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

from .hnum import HNum
from .hstr import HStr
from .href import HRef
from .hdate import HDate
from .hdatetime import HDateTime
from .htime import HTime
from .huri import HUri
from .htoken import HaystackToken


#  * Stream based tokenizer for Haystack formats such as Zinc and Filters
class HaystackTokenizer(object):
    # ////////////////////////////////////////////////////////////////////////
    #  Construction
    # ////////////////////////////////////////////////////////////////////////
    def __init__(self, in_):
        self.cur = None
        self.peek = None
        self.char_index = 0
        self.line = 1
        self.eof = None
        self.in_ = in_
        self.tok = HaystackToken.eof
        self.consume()
        self.consume()

    def close(self):
        try:
            return True
        except Exception:
            return False

    # ////////////////////////////////////////////////////////////////////////
    #  Tokenizing
    # ////////////////////////////////////////////////////////////////////////
    def next(self):
        #  reset
        self.val = None
        #  skip non-meaningful whitespace and comments
        while True:
            #  treat space, tab, non-breaking space as whitespace
            if self.cur == ' ' or self.cur == '\t' or self.cur == 0xa0:
                self.consume()
                continue
            #  comments
            if self.cur == '/':
                if self.peek == '/':
                    self.skipCommentsSL()
                    continue
                if self.peek == '*':
                    self.skipCommentsML()
                    continue
            break
        #  newlines
        if self.cur == '\n' or self.cur == '\r':
            if self.cur == '\r' and self.peek == '\n':
                self.consume('\r')
            self.consume()
            self.line += 1
            self.tok = HaystackToken.nl
            return self.tok
        #  handle various starting chars
        if self.isIdStart(self.cur):
            self.tok = self.id()
        elif self.cur == '"':
            self.tok = self.str_()
        elif self.cur == '@':
            self.tok = self.ref()
        elif self.isDigit(self.cur):
            self.tok = self.num()
        elif self.cur == '`':
            self.tok = self.uri()
        elif self.cur == '-' and self.isDigit(self.peek):
            self.tok = self.num()
        else:
            self.tok = self.symbol()
        return self.tok

    # ////////////////////////////////////////////////////////////////////////
    #  Token Productions
    # ////////////////////////////////////////////////////////////////////////
    def id(self):
        s = ''
        while self.isIdPart(self.cur):
            s += self.cur
            self.consume()
        self.val = s
        return HaystackToken.id

    @classmethod
    def isIdStart(cls, cur):
        if cur and 'a' <= cur and cur <= 'z':
            return True
        if cur and 'A' <= cur and cur <= 'Z':
            return True
        return False

    @classmethod
    def isIdPart(cls, cur):
        if cls.isIdStart(cur):
            return True
        if cls.isDigit(cur):
            return True
        if cur and cur == '_':
            return True
        return False

    @classmethod
    def isDigit(cls, cur):
        return cur and '0' <= cur and cur <= '9'

    def num(self):
        #  hex number (no unit allowed)
        isHex = self.cur == '0' and self.peek == 'x'
        s = ''
        if isHex:
            self.consume('0')
            self.consume('x')
            while True:
                if isHex(self.cur):
                    s += self.cur
                    self.consume()
                    continue
                if self.cur == '_':
                    self.consume()
                    continue
                break
            self.val = HNum.make(int(s, 16))
            return HaystackToken.num
        #  consume all things that might be part of this number token
        s = self.cur
        self.consume()
        colons = 0
        dashes = 0
        unitIndex = 0
        exp = False
        while True:
            if not self.cur:
                break
            if not self.cur.isdigit():
                if exp and (self.cur == '+' or self.cur == '-'):
                    pass
                elif self.cur == '-':
                    dashes += 1
                elif self.cur == ':' and self.peek.isdigit():
                    colons += 1
                elif (exp or colons >= 1) and self.cur == '+':
                    pass
                elif self.cur == '.':
                    if not self.peek.isdigit():
                        break
                elif (self.cur == 'e' or self.cur == 'E') and (self.peek == '-' or self.peek == '+' or self.peek.isdigit()):
                    exp = True
                elif self.cur.isalpha() or self.cur == '%' or self.cur == '$' or self.cur == '/' or self.cur > 128:
                    if unitIndex == 0:
                        unitIndex = len(s)
                elif self.cur == '_':
                    if unitIndex == 0 and self.peek.isdigit():
                        self.consume()
                        continue
                    else:
                        if unitIndex == 0:
                            unitIndex = len(s)
                else:
                    break
            s += self.cur
            self.consume()
        if dashes == 2 and colons == 0:
            return self.date(s)
        if dashes == 0 and colons >= 1:
            return self.time(s, colons == 1)
        if dashes >= 2:
            return self.dateTime(s)
        return self.number(s.__str__(), unitIndex)

    @classmethod
    def isHex(cls, cur):
        if not cur:
            return False
        cur = cur.lower()
        if 'a' <= cur and cur <= 'f':
            return True
        if cls.isDigit(cur):
            return True
        return False

    def date(self, s):
        try:
            self.val = HDate.make_from_string(s)
            return HaystackToken.date
        except Exception as e:
            raise self.err(str(e))

    #  we don't require hour to be two digits and we don't require seconds 
    def time(self, s, addSeconds):
        try:
            if s[1] == ':':
                s = '0' + s
            if addSeconds:
                s += ":00"
            self.val = HTime.make_from_string(s)
            return HaystackToken.time
        except Exception as e:
            raise self.err(str(e))

    def dateTime(self, s):
        #  xxx timezone
        if self.cur != ' ' or not self.peek.isupper():
            if s[-1] == 'Z':
                s += " UTC"
            else:
                raise self.err("Expecting timezone")
        else:
            self.consume()
            s += ' '
            while self.isIdPart(self.cur):
                s += self.cur
                self.consume()
            #  handle GMT+xx or GMT-xx
            if (self.cur == '+' or self.cur == '-') and s.endswith("GMT"):
                s += self.cur
                self.consume()
                while self.isDigit(self.cur):
                    s += self.cur
                    self.consume()
        try:
            self.val = HDateTime.make_from_string(s)
            return HaystackToken.dateTime
        except Exception as e:
            raise self.err(str(e))

    def number(self, s, unitIndex):
        try:
            if unitIndex == 0:
                self.val = HNum.make(float(s))
            else:
                doubleStr = s[0:unitIndex]
                unitStr = s[unitIndex:]
                self.val = HNum.make(float(doubleStr), unitStr)
        except Exception:
            raise self.err("Invalid Number literal: " + s)
        return HaystackToken.num

    def str_(self):
        self.consume('"')
        s = ''
        while True:
            if self.cur == self.eof:
                raise self.err("Unexpected end of str")
            if self.cur == '"':
                self.consume('"')
                break
            if self.cur == '\\':
                s += self.escape()
                continue
            s += self.cur
            self.consume()
        self.val = HStr.make(s)
        return HaystackToken.str_

    def ref(self):
        self.consume('@')
        s = ''
        while True:
            if HRef.isIdChar(self.cur):
                s += self.cur
                self.consume()
            else:
                break
        self.val = HRef.make(s, None)
        return HaystackToken.ref

    def uri(self):
        self.consume('`')
        s = ''
        while True:
            if self.cur == '`':
                self.consume('`')
                break
            if self.cur == self.eof or self.cur == '\n':
                raise self.err("Unexpected end of uri")
            if self.cur == '\\':
                if self.peek == ':':
                    pass
                elif self.peek == '/':
                    pass
                elif self.peek == '?':
                    pass
                elif self.peek == '#':
                    pass
                elif self.peek == '[':
                    pass
                elif self.peek == ']':
                    pass
                elif self.peek == '@':
                    pass
                elif self.peek == '\\':
                    pass
                elif self.peek == '&':
                    pass
                elif self.peek == '=':
                    pass
                elif self.peek == ';':
                    s += self.cur
                    s += self.peek
                    self.consume()
                    self.consume()
                else:
                    s += self.escape()
            else:
                s += self.cur
                self.consume()
        self.val = HUri.make(s)
        return HaystackToken.uri

    def escape(self):
        self.consume('\\')
        if self.cur == 'b':
            self.consume()
            return '\b'
        elif self.cur == 'f':
            self.consume()
            return '\f'
        elif self.cur == 'n':
            self.consume()
            return '\n'
        elif self.cur == 'r':
            self.consume()
            return '\r'
        elif self.cur == 't':
            self.consume()
            return '\t'
        elif self.cur == '"':
            self.consume()
            return '"'
        elif self.cur == '$':
            self.consume()
            return '$'
        elif self.cur == '\'':
            self.consume()
            return '\''
        elif self.cur == '`':
            self.consume()
            return '`'
        elif self.cur == '\\':
            self.consume()
            return '\\'
        #  check for uxxxx
        esc = ''
        if self.cur == 'u':
            self.consume('u')
            esc += self.cur
            self.consume()
            esc += self.cur
            self.consume()
            esc += self.cur
            self.consume()
            esc += self.cur
            self.consume()
            try:
                return int(esc, 16)
            except Exception:
                raise Exception("Invalid unicode escape: " + esc)
        raise self.err("Invalid escape sequence: " + self.cur)

    def symbol(self):
        c = self.cur
        self.consume()
        if c == ',':
            return HaystackToken.comma
        elif c == ':':
            return HaystackToken.colon
        elif c == ';':
            return HaystackToken.semicolon
        elif c == '[':
            return HaystackToken.lbracket
        elif c == ']':
            return HaystackToken.rbracket
        elif c == '{':
            return HaystackToken.lbrace
        elif c == '}':
            return HaystackToken.rbrace
        elif c == '(':
            return HaystackToken.lparen
        elif c == ')':
            return HaystackToken.rparen
        elif c == '<':
            if self.cur == '<':
                self.consume('<')
                return HaystackToken.lt2
            if self.cur == '=':
                self.consume('=')
                return HaystackToken.ltEq
            return HaystackToken.lt
        elif c == '>':
            if self.cur == '>':
                self.consume('>')
                return HaystackToken.gt2
            if self.cur == '=':
                self.consume('=')
                return HaystackToken.gtEq
            return HaystackToken.gt
        elif c == '-':
            if self.cur == '>':
                self.consume('>')
                return HaystackToken.arrow
            return HaystackToken.minus
        elif c == '=':
            if self.cur == '=':
                self.consume('=')
                return HaystackToken.eq
            return HaystackToken.assign
        elif c == '!':
            if self.cur == '=':
                self.consume('=')
                return HaystackToken.notEq
            return HaystackToken.bang
        elif c == '/':
            return HaystackToken.slash
        if c == self.eof:
            return HaystackToken.eof
        raise self.err("Unexpected symbol: '" + str(c) + "'")

    # ////////////////////////////////////////////////////////////////////////
    #  Comments
    # ////////////////////////////////////////////////////////////////////////
    def skipCommentsSL(self):
        self.consume('/')
        self.consume('/')
        while True:
            if self.cur == '\n' or self.cur == self.eof:
                break
            self.consume()

    def skipCommentsML(self):
        self.consume('/')
        self.consume('*')
        depth = 1
        while True:
            if self.cur == '*' and self.peek == '/':
                self.consume('*')
                self.consume('/')
                depth -= 1
                if depth <= 0:
                    break
            if self.cur == '/' and self.peek == '*':
                self.consume('/')
                self.consume('*')
                depth += 1
                continue
            if self.cur == '\n':
                self.line += 1
            if self.cur == self.eof:
                raise self.err("Multi-line comment not closed")
            self.consume()

    # ////////////////////////////////////////////////////////////////////////
    #  Error Handling
    # ////////////////////////////////////////////////////////////////////////
    def err(self, msg):
        return Exception(msg + " [line " + str(self.line) + "]")

    # ////////////////////////////////////////////////////////////////////////
    #  Char
    # ////////////////////////////////////////////////////////////////////////
    def consume(self, expected=None):
        if expected:
            if self.cur != expected:
                raise self.err("Expected " + expected)
            self.consume()
        else:
            try:
                self.cur = self.peek
                if self.char_index >= len(self.in_):
                    self.peek = None
                else:
                    self.peek = self.in_[self.char_index]
                    self.char_index += 1
            except Exception as e:
                print('htokenizer::consume error', str(e))
                self.cur = self.eof
                self.peek = self.eof
