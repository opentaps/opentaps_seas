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

from django.contrib.postgres.fields import ArrayField as PsqlArrayField

from django.db.models import Lookup

# from django.contrib.postgres import lookups


class ArrayField(PsqlArrayField):
    pass

# Note : we simply redefine the Array lookup to generate the Crate compatible SQL
# see django.contrib.postgres.lookups


@ArrayField.register_lookup
class ArrayContains(Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        # note: RHS will be an array by default, but we want a scalar here
        if isinstance(self.rhs, list):
            self.rhs = self.rhs[0]
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = rhs_params + lhs_params
        # note optimize the query using ignore3vl
        # https://crate.io/docs/crate/reference/en/latest/general/builtins/scalar.html#ignore3vl
        sql = 'IGNORE3VL(%s = ANY(%s))' % (rhs, lhs)
        # Note: in postgres this translates to LHS @> RHS
        # but in crate this should be written: RHS = ANY(LHS)
        # sql, params = super().as_sql(qn, connection)
        # sql = '%s::%s' % (sql, self.lhs.output_field.db_type(connection))
        return sql, params
