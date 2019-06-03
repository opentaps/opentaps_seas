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

from .common import ParseException
from .hbool import HBool
from .href import HRef
from .htoken import HaystackToken
from .htokenizer import HaystackTokenizer


# HFilter models a parsed tag query string.
class HFilter(object):

    def __init__(self):
        self.string = None

    # //////////////////////////////////////////////////////////////////////////
    # // Encoding
    # //////////////////////////////////////////////////////////////////////////

    # Decode a string into a HFilter; return null or throw
    # ParseException if not formatted correctly
    @classmethod
    def make(cls, s, checked=True):
        try:
            return FilterParser(s).parse()
        except Exception as e:
            if not checked:
                return None
            if isinstance(e, ParseException):
                raise
            raise ParseException(s, e)

    # //////////////////////////////////////////////////////////////////////////
    # // Factories
    # //////////////////////////////////////////////////////////////////////////

    # Match records which have the specified tag path defined.
    @classmethod
    def has(cls, path):
        h = Has(Path.make(path))
        return h

    # Match records which do not define the specified tag path.
    @classmethod
    def missing(cls, path):
        return Missing(Path.make(path))

    # Match records which have a tag are equal to the specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def eq(cls, path, val):
        return Eq(Path.make(path), val)

    # Match records which have a tag not equal to the specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def ne(cls, path, val):
        return Ne(Path.make(path), val)

    # Match records which have tags less than the specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def lt(cls, path, val):
        return Lt(Path.make(path), val)

    # Match records which have tags less than or equals to specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def le(cls, path, val):
        return Le(Path.make(path), val)

    # Match records which have tags greater than specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def gt(cls, path, val):
        return Gt(Path.make(path), val)

    # Match records which have tags greater than or equal to specified value.
    # If the path is not defined then it is unmatched.
    @classmethod
    def ge(cls, path, val):
        return Ge(Path.make(path), val)

    # Return a query which is the logical-and of this and that query.
    def a(self, that):
        return And(self, that)

    # Return a query which is the logical-or of this and that query.
    def o(self, that):
        return Or(self, that)

    # //////////////////////////////////////////////////////////////////////////
    # // Access
    # //////////////////////////////////////////////////////////////////////////

    # Return if given tags entity matches this query.
    def include(self, _dict, pather):
        raise NotImplementedError()

    # String encoding
    def toString(self):
        if self.string is None:
            self.string = self.toStr()
        return self.string

    def __str__(self):
        return self.toString()

    # Used to lazily build toString
    def toStr(self):
        raise NotImplementedError()

    # Hash code is based on string encoding
    def hashCode(self):
        return hash(self.toString())

    # Equality is based on string encoding
    def equals(self, that):
        if not isinstance(that, HFilter):
            return False
        return self.toString() == that.toString()

# //////////////////////////////////////////////////////////////////////////
# // HFilter.Path
# //////////////////////////////////////////////////////////////////////////


# Pather is a callback interface used to resolve query paths.
class Pather(object):
    # Given a HRef string identifier, resolve to an entity's
    # HDict respresentation or ref is not found return null.
    def find(self, ref):
        raise NotImplementedError()

# //////////////////////////////////////////////////////////////////////////
# // HFilter.Path
# //////////////////////////////////////////////////////////////////////////


# Path is a simple name or a complex path using the "->" separator
class Path(object):
    # Construct a new Path from string or throw ParseException
    def make(path):
        try:
            # optimize for common single name case
            try:
                dash = path.index('-')
            except ValueError:
                return Path1(path)

            # parse
            s = 0
            acc = []
            while True:
                n = path.substring(s, dash)
                if len(n) == 0:
                    raise Exception()
                acc.append(n)
                if path.charAt(dash+1) != '>':
                    raise Exception()
                s = dash + 2
                try:
                    dash = path.index('-', s)
                except ValueError:
                    n = path.substring(s, len(path))
                    if len(n) == 0:
                        raise Exception()
                    acc.append(n)
                    break
            return PathN(path, acc)
        except Exception as e:
            raise
        raise ParseException("Path: " + path)

    def __len__(self):
        return self.size()

    # Number of names in the path.
    def size(self):
        raise NotImplementedError()

    # Get name at given index.
    def get(self, i):
        raise NotImplementedError()

    # Hashcode is based on string.
    def hashCode(self):
        return hash(self.toString())

    # Equality is based on string.
    def equals(self, that):
        return self.toString() == that.toString()

    # Get string encoding.
    def toString(self):
        raise NotImplementedError()

    def __str__(self):
        return self.toString()


class Path1(Path):
    name = None

    def __init__(self, n):
        self.name = n

    def size(self):
        return 1

    def get(self, i):
        if i == 0:
            return self.name
        raise IndexError(i)

    def toString(self):
        return self.name


class PathN(Path):
    def __init__(self, s, n):
        self.string = s
        self.names = n

    def size(self):
        return len(self.names)

    def get(self, i):
        return self.names[i]

    def toString(self):
        return self.string

# //////////////////////////////////////////////////////////////////////////
# // PathFilter
# //////////////////////////////////////////////////////////////////////////


class PathFilter(HFilter):
    def __init__(self, p):
        super(PathFilter, self).__init__()
        self.path = p

    def include(self, _dict, pather=None):
        # default implementation
        if not pather:
            pather = Pather()
        print('PathFilter::include', _dict)
        print('PathFilter::include get from path', self.path, self.path.size())
        print('PathFilter::include get', self.path.get(0))
        val = _dict.get(self.path.get(0), None)
        print('PathFilter::include got val', val)
        if self.path.size() != 1:
            nt = _dict
            for i in range(self.path.size()):
                if not isinstance(val, HRef):
                    val = None
                    break
                nt = pather.find(val.val)
                if (nt is None):
                    val = None
                    break
                val = nt.get(self.path.get(i), False)
        return self.doInclude(val)

    def doInclude(self, val):
        raise NotImplementedError()

# //////////////////////////////////////////////////////////////////////////
# // Has
# //////////////////////////////////////////////////////////////////////////


class Has(PathFilter):
    def __init__(self, p):
        super(Has, self).__init__(p)

    def doInclude(self, v):
        print('Has::doInclude', v)
        return v is not None

    def toStr(self):
        return self.path.toString()

# //////////////////////////////////////////////////////////////////////////
# // Missing
# //////////////////////////////////////////////////////////////////////////


class Missing(PathFilter):
    def __init__(self, p):
        super(Missing, self).__init__(p)

    def doInclude(self, v):
        print('Missing::doInclude', v)
        return v is None

    def toStr(self):
        return "not " + self.path.toString()

# //////////////////////////////////////////////////////////////////////////
# // CmpFilter
# //////////////////////////////////////////////////////////////////////////


class CmpFilter(PathFilter):
    def __init__(self, p, val):
        super(CmpFilter, self).__init__(p)
        self.val = val

    def toStr(self):
        print('CmpFilter::toStr', type(self.val), self.val, self.path, self.cmpStr())
        return str(self.path) + self.cmpStr() + self.val.toZinc()

    def sameType(self, v):
        return v is not None and isinstance(v, type(self.val))

    def cmpStr(self):
        raise NotImplementedError()

# //////////////////////////////////////////////////////////////////////////
# // Eq
# //////////////////////////////////////////////////////////////////////////


class Eq(CmpFilter):
    def __init__(self, p, v):
        super(Eq, self).__init__(p, v)

    def cmpStr(self):
        return "=="

    def doInclude(self, v):
        print('Eq::doInclude', type(v), v, type(self.val), self.val, v == self.val)
        return v is not None and v == self.val

# //////////////////////////////////////////////////////////////////////////
# // Ne
# //////////////////////////////////////////////////////////////////////////


class Ne(CmpFilter):
    def __init__(self, p, v):
        super(Ne, self).__init__(p, v)

    def cmpStr(self):
        return "!="

    def doInclude(self, v):
        print('Ne::doInclude', v, self.val)
        return v is not None and not v == self.val

# //////////////////////////////////////////////////////////////////////////
# // Lt
# //////////////////////////////////////////////////////////////////////////


class Lt(CmpFilter):
    def __init__(self, p, v):
        super(Lt, self).__init__(p, v)

    def cmpStr(self):
        return "<"

    def doInclude(self, v):
        print('Lt::doInclude', v, self.val)
        return v < self.val

# //////////////////////////////////////////////////////////////////////////
# // Le
# //////////////////////////////////////////////////////////////////////////


class Le(CmpFilter):
    def __init__(self, p, v):
        super(Le, self).__init__(p, v)

    def cmpStr(self):
        return "<="

    def doInclude(self, v):
        print('Le::doInclude', v, self.val)
        return v <= self.val

# //////////////////////////////////////////////////////////////////////////
# // Gt
# //////////////////////////////////////////////////////////////////////////


class Gt(CmpFilter):
    def __init__(self, p, v):
        super(Gt, self).__init__(p, v)

    def cmpStr(self):
        return ">"

    def doInclude(self, v):
        print('Gt::doInclude', type(v), v, type(self.val), self.val, v > self.val)
        return v > self.val

# //////////////////////////////////////////////////////////////////////////
# // Ge
# //////////////////////////////////////////////////////////////////////////


class Ge(CmpFilter):
    def __init__(self, p, v):
        super(Ge, self).__init__(p, v)

    def cmpStr(self):
        return ">="

    def doInclude(self, v):
        print('Ge::doInclude', v, self.val)
        return v >= self.val

# //////////////////////////////////////////////////////////////////////////
# // Compound
# //////////////////////////////////////////////////////////////////////////


class CompoundFilter(HFilter):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def keyword(self):
        raise NotImplementedError()

    def toStr(self):
        s = ''
        if isinstance(self.a, CompoundFilter):
            s += '(' + str(self.a) + ')'
        else:
            s += str(self.a)
        s += ' ' + self.keyword() + ' '
        if isinstance(self.b, CompoundFilter):
            s += '(' + str(self.b) + ')'
        else:
            s += str(self.b)
        return s

    def __str__(self):
        return self.toStr()

# //////////////////////////////////////////////////////////////////////////
# // And
# //////////////////////////////////////////////////////////////////////////


class And(CompoundFilter):
    def __init__(self, a, b):
        super(And, self).__init__(a, b)

    def keyword(self):
        return "and"

    def include(self, _dict, pather):
        print('And::include', self.a, self.b)
        return self.a.include(_dict, pather) and self.b.include(_dict, pather)

# //////////////////////////////////////////////////////////////////////////
# // Or
# //////////////////////////////////////////////////////////////////////////


class Or(CompoundFilter):
    def __init__(self, a, b):
        super(Or, self).__init__(a, b)

    def keyword(self):
        return "or"

    def include(self, _dict, pather):
        print('Or::include', self.a, self.b)
        return self.a.include(_dict, pather) or self.b.include(_dict, pather)

# //////////////////////////////////////////////////////////////////////////
# // FilterParser
# //////////////////////////////////////////////////////////////////////////


class FilterParser:
    def __init__(self, _in):
        self.cur = None
        self.curVal = None
        self.peek = None
        self.peekVal = None
        self.tokenizer = HaystackTokenizer(_in)
        self.consume()
        self.consume()

    def parse(self):
        f = self.condOr()
        self.verify(HaystackToken.eof)
        return f

    def condOr(self):
        lhs = self.condAnd()
        if not self.isKeyword("or"):
            return lhs
        self.consume()
        return lhs.o(self.condOr())

    def condAnd(self):
        lhs = self.term()
        if not self.isKeyword("and"):
            return lhs
        self.consume()
        return lhs.a(self.condAnd())

    def term(self):
        if self.cur == HaystackToken.lparen:
            self.consume()
            f = self.condOr()
            self.consume(HaystackToken.rparen)
            return f

        if self.isKeyword("not") and self.peek == HaystackToken.id:
            self.consume()
            return Missing(self.path())

        p = self.path()
        if self.cur == HaystackToken.eq:
            self.consume()
            return Eq(p, self.val())
        if self.cur == HaystackToken.notEq:
            self.consume()
            return Ne(p, self.val())
        if self.cur == HaystackToken.lt:
            self.consume()
            return Lt(p, self.val())
        if self.cur == HaystackToken.ltEq:
            self.consume()
            return Le(p, self.val())
        if self.cur == HaystackToken.gt:
            self.consume()
            return Gt(p, self.val())
        if self.cur == HaystackToken.gtEq:
            self.consume()
            return Ge(p, self.val())

        h = Has(p)
        return h

    def path(self):
        _id = self.pathName()
        if self.cur != HaystackToken.arrow:
            return Path1.make(_id)

        segments = []
        segments.append(_id)
        s = '' + _id
        while self.cur == HaystackToken.arrow:
            self.consume(HaystackToken.arrow)
            _id = self.pathName()
            segments.append(_id)
            s += str(HaystackToken.arrow) + _id
        return PathN(s, segments)

    def pathName(self):
        if self.cur != HaystackToken.id:
            raise ParseException("Expecting tag name, not " + self.curToStr())
        _id = self.curVal
        self.consume()
        return _id

    def val(self):
        if self.cur.literal:
            val = self.curVal
            self.consume()
            return val

        if self.cur == HaystackToken.id:
            if "true" == self.curVal:
                self.consume()
                return HBool.TRUE
            if "false" == self.curVal:
                self.consume()
                return HBool.FALSE

        raise ParseException("Expecting value literal, not " + self.curToStr())

    def isKeyword(self, n):
        return self.cur == HaystackToken.id and n == self.curVal

    def verify(self, expected):
        if self.cur != expected:
            raise ParseException("Expected " + str(expected) + " not " + self.curToStr())

    def curToStr(self):
        if self.curVal is not None:
            return "" + str(self.cur) + " " + str(self.curVal)
        else:
            return str(self.cur)

    def consume(self, expected=None):
        if expected is not None:
            self.verify(expected)
        self.cur = self.peek
        self.curVal = self.peekVal
        self.peek = self.tokenizer.next()
        self.peekVal = self.tokenizer.val
