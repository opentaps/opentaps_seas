import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

URL_UTILITYAPI = 'https://utilityapi.com/api/v2'


def get_authorizations():
    data = utilityapi_get("authorizations")

    return data['authorizations']


def get_meters(auth_uids=None):
    params = None
    if auth_uids:
        params = 'authorizations=' + auth_uids
    data = utilityapi_get('meters', params)

    return data['meters']


def utilityapi_get(request_name, params=None):
    url = URL_UTILITYAPI + '/' + request_name
    if params:
        url += '?' + params

    # Request param
    if settings.UTILITY_API_KEY:
        api_key = settings.UTILITY_API_KEY
    else:
        raise NameError('Missing utilityapi configuration')

    headers = {'Authorization': 'Bearer ' + api_key}

    r = requests.get(url, headers=headers)

    utilityapi_data = r.json()
    return utilityapi_data
