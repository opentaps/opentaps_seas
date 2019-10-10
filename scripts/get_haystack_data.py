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

from datetime import datetime
from datetime import timezone
from opentaps_seas.core.models import Entity
from hsclient.client import HSClient
from crate.client.exceptions import ProgrammingError
from opentaps_seas.core.utils import cleanup_id


def get_crate_connection():
    return connect('localhost:4200', error_trace=True)


def import_data(base_url, range_from):
    client = HSClient(base_url)

    # sites
    content = client.nav(nav_id=None)
    header, data = client.parse_grid(content)
    id_index = header.index('id')
    nav_id_index = header.index('navId')
    try:
        site_tag_id = header.index('site')
    except ValueError:
        site_tag_id = None

    sites_nav_ids = []
    new_sites_ids = []
    new_sites = 0

    if site_tag_id is not None:
        for row in data:
            new_id = cleanup_id(row[id_index])
            site_tag = row[site_tag_id]
            if 'M' == site_tag:
                sites_nav_ids.append(row[nav_id_index])
                entity = Entity.objects.filter(entity_id=new_id, m_tags__contains=['site']).first()
                if not entity:
                    # create new one
                    kv_tags, m_tags = prepare_tags(header, row)
                    new_entity = Entity(entity_id=new_id, kv_tags=kv_tags, m_tags=m_tags)
                    new_entity.save()
                    new_sites = new_sites + 1
                    new_sites_ids.append(new_id)
            else:
                print("There is no 'site' tag in ", row)

    else:
        print("Cannot find 'site' in the response header")

    if new_sites > 0:
        print("New sites ids:", new_sites_ids)

    print("Processed {0} sites, added {1} new.".format(len(data), new_sites))
    # print("sites_nav_ids:", sites_nav_ids)

    # equipments
    total_equips = 0
    new_equips = 0
    new_equips_ids = []
    equips_nav_ids = []
    if len(sites_nav_ids) > 0:
        for nav_id in sites_nav_ids:
            content = client.nav(nav_id=nav_id)
            header, data = client.parse_grid(content)
            total_equips = total_equips + len(data)
            print("{1}: Got {0} equipments".format(len(data), nav_id))
            id_index = header.index('id')
            nav_id_index = header.index('navId')
            try:
                equip_tag_id = header.index('equip')
            except ValueError:
                equip_tag_id = None

            if equip_tag_id is not None:
                for row in data:
                    new_id = cleanup_id(row[id_index])
                    equip_tag = row[equip_tag_id]
                    if 'M' == equip_tag:
                        equips_nav_ids.append(row[nav_id_index])
                        entity = Entity.objects.filter(entity_id=new_id, m_tags__contains=['equip']).first()
                        if not entity:
                            # create new one
                            kv_tags, m_tags = prepare_tags(header, row)
                            new_entity = Entity(entity_id=new_id, kv_tags=kv_tags, m_tags=m_tags)
                            new_entity.save()
                            new_equips = new_equips + 1
                            new_equips_ids.append(new_id)
                    else:
                        print("There is no 'equip' tag in ", row)

            else:
                print("Cannot find 'equip' in the response header")

    else:
        print("Empty sites list")

    if new_equips > 0:
        print("New equipments ids:", new_equips_ids)

    print("Processed {0} equipments, added {1} new.".format(total_equips, new_equips))
    # print("equip_nav_ids:", equips_nav_ids)

    # points
    total_points = 0
    new_points = 0
    new_points_ids = []
    all_points_ids = []
    points_nav_ids = []
    if len(equips_nav_ids) > 0:
        for nav_id in equips_nav_ids:
            content = client.nav(nav_id=nav_id)
            header, data = client.parse_grid(content)
            total_points = total_points + len(data)
            print("{1}: Got {0} points".format(len(data), nav_id))
            try:
                id_index = header.index('id')
            except ValueError:
                print("Cannot get id index")
                continue

            nav_id_index = header.index('navId')
            try:
                point_tag_id = header.index('point')
            except ValueError:
                point_tag_id = None

            if point_tag_id is not None:
                for row in data:
                    new_id = cleanup_id(row[id_index])
                    point_tag = row[point_tag_id]
                    if 'M' == point_tag:
                        points_nav_ids.append(row[nav_id_index])
                        all_points_ids.append(row[id_index])
                        entity = Entity.objects.filter(entity_id=new_id, m_tags__contains=['point']).first()
                        if not entity:
                            # create new one
                            kv_tags, m_tags = prepare_tags(header, row)
                            new_entity = Entity(entity_id=new_id, topic=row[id_index],
                                                kv_tags=kv_tags, m_tags=m_tags)
                            new_entity.save()
                            new_points = new_points + 1
                            new_points_ids.append(new_id)
                    else:
                        print("There is no 'point' tag in ", row)
            else:
                print("Cannot find 'point' in the response header")
    else:
        print("Empty equipments list")

    if new_points > 0:
        print("New points ids:", new_points_ids)

    print("Processed {0} points, added {1} new.".format(total_points, new_points))
    # print("all_points_ids:", all_points_ids)
    # print("points_nav_ids:", points_nav_ids)

    # points data
    topics_counter = 0
    topics_list = []
    crate_connection = get_crate_connection()
    crate_cursor = crate_connection.cursor()

    if len(all_points_ids) > 0:
        for point_id in all_points_ids:
            topic_data_counter = 0

            sql = """INSERT INTO {0} (topic)
            VALUES (%s)""".format("volttron.topic")
            try:
                crate_cursor.execute("""INSERT INTO volttron.topic (topic) VALUES (?)""", (point_id,))
            except ProgrammingError:
                # just make sure the topic exists
                pass

            crate_cursor.execute("""SELECT ts, string_value FROM "volttron"."data"
                WHERE topic = ? ORDER BY ts DESC LIMIT 1;""", (point_id,))
            result = crate_cursor.fetchone()
            his_range = None
            if result:
                ts = result[0]
                t = datetime.utcfromtimestamp(ts // 1000).replace(microsecond=ts %
                                                                  1000 * 1000).replace(tzinfo=timezone.utc)
                his_range = t.strftime('%Y-%m-%d') + ',' + datetime.utcnow().strftime('%Y-%m-%d')
            else:
                if range_from:
                    if range_from != "none":
                        his_range = range_from
                else:
                    his_range = 'today'

            print("Processing :", point_id, ", range: ", his_range)
            content = client.his_read(id=point_id, range=his_range)
            header, data = client.parse_grid(content)
            if header and 'ts' in header and 'val' in header:
                ts_index = header.index('ts')
                val_index = header.index('val')
                for item in data:
                    ts_str_arr = item[ts_index].split(" ")
                    val = item[val_index]
                    sql = """INSERT INTO volttron.data (double_value, source, string_value, topic, ts)
                    VALUES (?, ?, ?, ?, ?)"""
                    try:
                        crate_cursor.execute(sql, (val, 'scrape', val, point_id, ts_str_arr[0],))
                        topic_data_counter = topic_data_counter + 1
                    except ProgrammingError:
                        # that means it already exists
                        pass

            topics_list.append({point_id: topic_data_counter})
            print("Point #{1}: Added {0} data rows.".format(topic_data_counter, topics_counter))
            topics_counter = topics_counter + 1

    crate_cursor.close()
    crate_connection.close()

    print("Processed {0} topics.".format(topics_counter))


def prepare_tags(header, data_row):
    m_tags = []
    kv_tags = {}
    index = 0
    for item in header:
        if data_row[index] != 'M':
            if data_row[index] and data_row[index] != '' and data_row[index] != 'N':
                tag = data_row[index]
                kv_tags[item] = tag
        else:
            m_tags.append(item)

        index = index + 1

    return kv_tags, m_tags


def print_help():
    print("Usage: python manage.py runscript get_haystack_data --script-args haystack_server_url [none|range_from]")


def run(*args):
    if len(args) > 0:
        base_url = args[0]
        range_from = None
        if len(args) > 1:
            range_from = args[1]

        import_data(base_url, range_from)
    else:
        print_help()
