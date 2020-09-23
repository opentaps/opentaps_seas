import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_emissions_data(utility_id, account_number, from_date, thru_date):
    # /emissionscontract/getEmissionsData/{utilityId}/{partyId}/{fromDate}/{thruDate}
    emissions_data = None
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError('Missing Emissions API configuration')

    api_url += "/emissionscontract/getEmissionsData/{0}/{1}/{2}/{3}".format(utility_id, account_number,
                                                                            from_date, thru_date)
    try:
        r = requests.get(api_url)
        if r.status_code == 200:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    return emissions_data
