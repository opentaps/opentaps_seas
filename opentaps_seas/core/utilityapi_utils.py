import logging
import requests
from datetime import timedelta
from datetime import timezone

from ..core.models import MeterHistory
from ..core.models import MeterFinancialValue

import xml.etree.ElementTree as ET
from django.conf import settings
from greenbutton import resources
from greenbutton import enums

logger = logging.getLogger(__name__)

URL_UTILITYAPI = 'https://utilityapi.com/api/v2'
URL_ESPI = 'https://utilityapi.com/DataCustodian/espi/1_1/resource'


def get_authorizations():
    data = utilityapi_get("authorizations")

    return data['authorizations']


def get_meters(auth_uids=None):
    params = None
    if auth_uids:
        params = 'authorizations=' + auth_uids
    data = utilityapi_get('meters', params)

    return data['meters']


def get_meter(meter_uid):
    return utilityapi_get('meters/' + meter_uid)


def get_bills(meter_uid):
    return utilityapi_get('bills?meters=' + meter_uid)


def utilityapi_get(request_name, params=None):
    url = URL_UTILITYAPI + '/' + request_name
    if params:
        url += '?' + params

    headers = prepare_headers()
    r = requests.get(url, headers=headers)

    utilityapi_data = r.json()
    return utilityapi_data


def prepare_headers():
    if settings.UTILITY_API_KEY:
        api_key = settings.UTILITY_API_KEY
    else:
        raise NameError('Missing UtilityAPI configuration')

    headers = {'Authorization': 'Bearer ' + api_key}

    return headers


def get_usage_point(auth_uid, meter_uid):
    request_name = 'Subscription/' + auth_uid + '/UsagePoint/' + meter_uid
    return espi_get(request_name)


def get_meter_reading(auth_uid, meter_uid):
    request_name = 'Subscription/' + auth_uid + '/UsagePoint/' + meter_uid + '/MeterReading'
    return espi_get(request_name)


def espi_get(request_name):
    url = URL_ESPI + '/' + request_name

    return espi_get_by_url(url)


def espi_get_by_url(url):
    headers = prepare_headers()
    r = requests.get(url, headers=headers)

    tree = ET.fromstring(r.text)

    return tree


def import_meter_readings(u_meter, meter_uid, meter_id, user):
    count = 0
    count_existing = 0
    from_datetime = None
    thru_datetime = None
    authorization_uid = u_meter.get('authorization_uid')

    # 1. UsagePoint
    usage_point = get_usage_point(authorization_uid, meter_uid)

    local_time_url = None
    for child in usage_point:
        if 'link' in child.tag and child.attrib['rel'] == 'related':
            if 'LocalTimeParameters' in child.attrib['href']:
                local_time_url = child.attrib['href']

    # 2. LocalTimeParameters
    tzOffset = 0
    if local_time_url:
        ltptree = espi_get_by_url(local_time_url)
        if ltptree:
            ltp = resources.LocalTimeParameters(ltptree, usagePoints=[])
            if ltp:
                tzOffset = ltp.tzOffset

    # 3. MeterReading
    meter_reading = get_meter_reading(authorization_uid, meter_uid)

    reading_type_url = None
    interval_block_url = None
    if meter_reading:
        meter_reading_entry = meter_reading.find('atom:entry', resources.ns)
        if meter_reading_entry:
            for child in meter_reading_entry:
                if 'link' in child.tag and child.attrib['rel'] == 'related':
                    if 'ReadingType' in child.attrib['href']:
                        reading_type_url = child.attrib['href']
                    elif 'IntervalBlock' in child.attrib['href']:
                        interval_block_url = child.attrib['href']

    if not reading_type_url:
        raise ValueError('Cannot get meter reading type url')

    if not interval_block_url:
        raise ValueError('Cannot get meter interval block url')

    # 3.1. ReadingType
    reading_type = None
    rttree = espi_get_by_url(reading_type_url)
    if rttree:
        reading_type = resources.ReadingType(rttree, meterReadings=[])

    if not reading_type:
        raise ValueError('Cannot get meter reading type')

    reading_type_uom = enums.UOM_IDS[reading_type.uom]
    if not reading_type_uom:
        raise ValueError('Cannot get meter reading type uom')

    # 3.2. IntervalBlock
    interval_blocks = []
    ibtree = espi_get_by_url(interval_block_url)
    if ibtree:
        for entry in ibtree.findall('atom:entry/atom:content/espi:IntervalBlock/../..', resources.ns):
            ib = resources.IntervalBlock(entry, meterReadings=[])
            interval_blocks.append(ib)

    for interval_block in interval_blocks:
        for ir in interval_block.intervalReadings:
            as_of_datetime = ir.timePeriod.start
            if tzOffset:
                tz = timezone(timedelta(seconds=tzOffset))
                as_of_datetime = as_of_datetime.replace(tzinfo=tz)

            if not from_datetime:
                from_datetime = as_of_datetime

            thru_datetime = as_of_datetime
            mh = MeterHistory.objects.filter(meter_id=meter_id, uom_id=reading_type_uom, source='utilityapi',
                                             as_of_datetime=as_of_datetime)

            if not mh:
                v = MeterHistory(meter_id=meter_id, uom_id=reading_type_uom)
                v.source = 'utilityapi'
                v.value = ir.value
                v.duration = int(ir.timePeriod.duration.total_seconds())
                v.as_of_datetime = as_of_datetime
                v.created_by_user = user

                v.save()
                count += 1
            else:
                count_existing += 1

    return count, count_existing, from_datetime, thru_datetime


def import_meter_bills(u_bills, meter_uid, meter_id, user):
    count_existing = 0
    from_datetime = None
    thru_datetime = None

    currency_uom_id = 'currency_USD'
    # collect created MeterFinancialValues
    results = []

    bills = u_bills.get('bills', [])
    for bill in bills:
        uid = bill.get('uid')
        ref = {'meter_uid': meter_uid, 'uid': uid}
        # CLeanup any previous entries we had for the same reference (meter/bill ids)
        existing = MeterFinancialValue.objects.filter(meter_id=meter_id, meter_production_reference=ref)
        count_existing = count_existing + existing.count()
        existing.delete()
        # base = bill.get('base', {})
        line_items = bill.get('line_items', [])
        # the bill period and volume and cost
        # eg: '2020-02-29T16:00:00.000000-08:00'
        #  bill_start_date = base.get('bill_start_date')
        #  bill_end_date = base.get('bill_end_date')
        #  bill_total_cost = base.get('bill_total_cost')
        #  bill_total_volume = base.get('bill_total_volume')
        # eg: 'kwh'
        #  bill_total_unit = base.get('bill_total_unit')

        # NOTE: those numbers do not necessarily match the line items dates (?)
        for line in line_items:
            l_cost = line.get('cost')
            l_name = line.get('name')
            l_start = line.get('start')
            l_end = line.get('end')
            # l_unit = line.get('unit')
            # l_volume = line.get('volume')
            # Record those as MeterFinancialValues
            m = MeterFinancialValue.objects.create(
                    meter_id=meter_id,
                    from_datetime=l_start,
                    thru_datetime=l_end,
                    source=l_name,
                    meter_production_type='UtilityApi Bill',
                    meter_production_reference=ref,
                    amount=l_cost,
                    uom_id=currency_uom_id,
                    created_by_user=user
                    )
            # auto convert the types (like date from string to date objects)
            m.refresh_from_db()
            results.append(m)
            if not from_datetime or from_datetime > m.from_datetime:
                from_datetime = m.from_datetime
            if not thru_datetime or thru_datetime < m.thru_datetime:
                thru_datetime = m.thru_datetime

    return results, count_existing, from_datetime, thru_datetime
