import logging
import requests
import xml.etree.ElementTree as ET
from django.conf import settings

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
    request_name = 'meters/' + meter_uid

    data = utilityapi_get(request_name)

    return data


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
