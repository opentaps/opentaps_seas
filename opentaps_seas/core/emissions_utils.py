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

import logging
import requests
from django.conf import settings
import json

logger = logging.getLogger(__name__)


def get_emissions_data(
    user_id, user_org, utility_id, account_number, from_date, thru_date
):
    emissions_data = None
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")
    # api_url = ""
    headers = {"Accept": "application/json"}
    api_url += f"/emissionscontract/getEmissionsData/{user_id}/{user_org}/{utility_id}/{account_number}/{from_date}/{thru_date}"
    try:
        r = requests.get(api_url)
        if r.status_code == 200:
            emissions_data = [r.json()]
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    return emissions_data


def record_emissions(utility_id, account_number, from_date, thru_date, amount, uom):
    # /emissionscontract/recordEmissions
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    api_url += "/emissionscontract/recordEmissions"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {
        "utilityId": utility_id,
        "partyId": account_number,
        "fromDate": from_date,
        "thruDate": thru_date,
        "energyUseAmount": amount,
        "energyUseUom": uom,
    }

    emissions_data = None
    try:
        r = requests.post(api_url, headers=headers, json=data)
        if r.status_code == 201:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    return emissions_data
