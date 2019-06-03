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

import hszinc
import logging

from django.contrib.sites.models import Site
from django.http import HttpResponse
from django.utils import timezone

from ..core.models import Entity
from ..core.models import PointView
from ..core import utils
from .utils.hfilter import HFilter
from .utils.hfilter import Pather


logger = logging.getLogger(__name__)


def _hzinc_response(data, **kwargs):
    if len(data.column) == 0:
        # trick to get an empty grid without crashing the dumper
        data.column['empty'] = {}
    return HttpResponse(hszinc.dump(data), content_type="text/zinc;charset=utf-8", **kwargs)


def about_view(request):
    g = hszinc.Grid()
    g.column['vendorUri'] = {}
    g.column['productUri'] = {}
    g.column['tz'] = {}
    g.column['serverName'] = {}
    g.column['productName'] = {}
    g.column['haystackVersion'] = {}
    g.column['productVersion'] = {}
    g.column['serverTime'] = {}
    g.column['serverBootTime'] = {}
    g.column['vendorName'] = {}
    g.extend([{
        'vendorUri': 'https://www.opensourcestrategies.com',
        'productUri': 'https://www.opensourcestrategies.com',
        'tz': timezone.get_default_timezone_name(),
        'serverName': Site.objects.get_current().domain,
        'productName': 'Opentaps-SEAS Haystack',
        'haystackVersion': '2.0',
        'productVersion': '1.0',
        'serverTime': timezone.now(),
        'vendorName': 'Opentaps-SEAS Haystack'
    }])
    return _hzinc_response(g)


def ops_view(request):
    g = hszinc.Grid()
    g.column['name'] = {}
    g.column['summary'] = {}
    g.extend([{
        'name': 'about',
        'summary': 'Summary information for server'
    }, {
        'name': 'ops',
        'summary': 'Operations supported by this server'
    }, {
        'name': 'formats',
        'summary': 'Grid data formats supported by this server'
    }, {
        'name': 'read',
        'summary': 'Read entity records in database'
    }, {
        'name': 'hisRead',
        'summary': 'Read time series from historian'
    }, {
        'name': 'nav',
        'summary': 'Navigate record tree'
    }])
    return _hzinc_response(g)


def formats_view(request):
    g = hszinc.Grid()
    g.column['mime'] = {}
    g.column['read'] = {}
    g.column['write'] = {}
    g.extend([{
        'mime': 'text/zinc',
        'read': hszinc.MARKER,
        'write': hszinc.MARKER
    }])
    return HttpResponse(hszinc.dump(g), content_type="text/zinc;charset=utf-8")


def nav_view(request):
    g = hszinc.Grid()
    navId = request.GET.get('navId')
    root = None
    if navId:
        try:
            root = Entity.objects.get(entity_id=navId)
        except Entity.DoesNotExist:
            return _hzinc_response(g, status=404)

    entities = None
    if root:
        eid = root.entity_id
        if 'id' in root.kv_tags:
            eid = root.kv_tags['id']
        # list the entities linked to root
        if 'site' in root.m_tags:
            entities = Entity.objects.filter(kv_tags__contains={'siteRef': eid}).exclude(kv_tags__has_key='equipRef')
        elif 'equip' in root.m_tags:
            entities = Entity.objects.filter(kv_tags__contains={'equipRef': eid})
    else:
        # list the sites
        entities = Entity.objects.filter(m_tags__contains=['site'])

    if not entities or len(entities) == 0:
        return _hzinc_response(g, status=404)

    # stores the entity_id
    added_fields = []
    data = []
    g.column['navId'] = {}
    # read which fields to include
    for e in entities:
        e_data = {'navId': e.entity_id}
        if e.kv_tags:
            for f in e.kv_tags.keys():
                e_data[f] = e.kv_tags[f]
                if f not in added_fields:
                    added_fields.append(f)
                    g.column[f] = {}

        for f in e.m_tags:
            e_data[f] = hszinc.MARKER
            if f not in added_fields:
                added_fields.append(f)
                g.column[f] = {}

        logger.info("nav_view: add data %s", e_data)
        data.append(e_data)

    # set the data
    g.extend(data)
    return _hzinc_response(g)


def hisread_view(request):
    g = hszinc.Grid()
    e_id = request.GET.get('id')
    e_range = request.GET.get('range')
    if not e_id or not e_range:
        return _hzinc_response(g, status=404)

    try:
        e = PointView.objects.get(entity_id=e_id)
    except PointView.DoesNotExist:
        return _hzinc_response(g, status=404)

    values = utils.get_point_values(e, trange=e_range, ts_as_datetime=True)

    g.metadata['id'] = e.entity_id
    g.column['ts'] = {}
    g.column['val'] = {}
    data = []
    for v in values:
        data.append({'ts': v[0], 'val': v[1]})

    g.extend(data)
    return _hzinc_response(g)


def read_view(request):
    g = hszinc.Grid()
    e_id = request.GET.get('id')
    if not e_id:
        r_filter = request.GET.get('filter')
        if not r_filter:
            return _hzinc_response(g, status=404)

        r_limit = request.GET.get('limit')
        if r_limit:
            try:
                r_limit = int(r_limit)
            except Exception:
                logger.exception('read_view: Error parsing limit parameter')
                r_limit = 10000
        else:
            r_limit = 10000

        # currently the filter is based on theJava implementation which
        # parses the filter string and checks each record as Dict of all values
        # eg: {'id': 'AB', 'dis': 'Site A Equip B', 'equip': 'M', 'siteRef': 'A'}
        # NOTE: by convention te haystack parser except all Ref ID to be given as @<id>
        #  eg: siteRef==@A
        # So if the site actually has Id = @A it must be given siteRef==@@A
        # A cleaner way is to quote so those are parsed as strings:
        #  eg: siteRef=="@A"
        try:
            h_filter = HFilter.make(r_filter)
            h_pather = Pather()

            added_fields = []
            data = []
            n = 0
            for e in Entity.objects.all():
                # transform into a dict first
                e_data = {}
                if e.kv_tags:
                    for f in e.kv_tags.keys():
                        e_data[f] = e.kv_tags[f]

                for f in e.m_tags:
                    e_data[f] = hszinc.MARKER

                # by default uses the id tag, but fallback to entity_id
                if 'id' not in e_data:
                    e_data['id'] = e.entity_id

                if h_filter.include(e_data, h_pather):
                    print('++++', e_data)
                    for f in e_data.keys():
                        if f not in added_fields:
                            added_fields.append(f)
                            g.column[f] = {}
                    data.append(e_data)
                    n += 1
                    if (n >= r_limit):
                        break

                else:
                    print('0000', e_data)

            g.extend(data)
            return _hzinc_response(g)
        except Exception:
            logger.exception('read_view: Error filtering')
            return _hzinc_response(g, status=500)

    try:
        e = Entity.objects.get(entity_id=e_id)
    except Entity.DoesNotExist:
        return _hzinc_response(g, status=404)

    e_data = {}
    added_fields = []
    if e.kv_tags:
        for f in e.kv_tags.keys():
            e_data[f] = e.kv_tags[f]
            if f not in added_fields:
                added_fields.append(f)
                g.column[f] = {}

        for f in e.m_tags:
            e_data[f] = hszinc.MARKER
            if f not in added_fields:
                added_fields.append(f)
                g.column[f] = {}

        logger.info("read_view: read data %s", e_data)

    g.extend([e_data])
    return _hzinc_response(g)
