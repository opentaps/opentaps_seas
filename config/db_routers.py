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

class CrateRouter:
    """
    A router to control all database operations on models in the
    crate stored application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read crate models go to crate.
        """
        if hasattr(model, 'Db') and model.Db.cratedb:
            return 'crate'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write crate models go to crate.
        """
        if hasattr(model, 'Db') and model.Db.cratedb:
            return 'crate'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the core app is involved.
        """
        if (hasattr(obj1, 'Db') and obj1.Db.cratedb) or (hasattr(obj2, 'Db') and obj2.Db.cratedb):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return None
