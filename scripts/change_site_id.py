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

from django.db import connections
from opentaps_seas.core.models import Entity


def cleanup_crate(from_id):
    # cleanup Crate DB since hte sync code does not expect the IDs to change
    with connections['crate'].cursor() as c:
        try:
            c.execute("""DELETE FROM "volttron"."topic" WHERE kv_tags['id'] = %s ;""", [from_id])
        except Exception as e:
            print(e)

        try:
            c.execute("""DELETE FROM "volttron"."topic" WHERE kv_tags['siteRef'] = %s ;""", [from_id])
        except Exception as e:
            print(e)

        c.close()


def change_site_id(from_id, to_id):
    site = None
    try:
        site = Entity.objects.get(kv_tags__id=from_id)
    except Entity.DoesNotExist:
        try:
            site = Entity.objects.get(entity_id=from_id)
            if site:
                print('Site not found with ID "{}"" did you mean "{}" ?'.format(from_id, site.kv_tags.get('id')))
                return
        except Entity.DoesNotExist:
            print('Site not found with ID "{}"'.format(from_id))
            return

    print("Found Site {}".format(site))

    with connections['default'].cursor() as c:
        # change the site ID
        try:
            c.execute("""update core_entity set kv_tags = kv_tags || hstore('id', %s)
                where kv_tags->'id' = %s;""", [to_id, from_id])
        except Exception as e:
            print(e)

        # change all related Entities:
        try:
            c.execute("""update core_entity set kv_tags = kv_tags || hstore('siteRef', %s)
                where kv_tags->'siteRef' = %s;""", [to_id, from_id])
        except Exception as e:
            print(e)

        c.close()

    cleanup_crate(from_id)


def print_help():
    print("Usage: python manage.py runscript chnage_site_id from_id to_id")


def run(*args):
    if len(args) == 2:
        change_site_id(args[0], args[1])
    else:
        print_help()
