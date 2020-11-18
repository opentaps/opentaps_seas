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
from base64 import b64decode, b64encode

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
    api_url += f"/emissionscontract/getAllEmissionsData/{user_id}/{user_org}/{utility_id}/{account_number}"
    try:
        r = requests.get(api_url)
        if r.status_code == 200:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    # Format dates for display
    if emissions_data:
        for emission_data_set in emissions_data:
            emission_data_set["fromDate"] = emission_data_set["fromDate"].replace(
                "T", " "
            )
            emission_data_set["thruDate"] = emission_data_set["thruDate"].replace(
                "T", " "
            )

    return emissions_data


def record_emissions(
    user_id, org_name, utility_id, account_number, from_date, thru_date, amount, uom, document
):
    # /emissionscontract/recordEmissions
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    api_url += "/emissionscontract/recordEmissions"
    headers = {"Content-Type": "multipart/form-data"}
    data = {
        "userId": user_id,
        "orgName": org_name,
        "utilityId": utility_id,
        "partyId": account_number,
        "fromDate": from_date,
        "thruDate": thru_date,
        "energyUseAmount": amount,
        "energyUseUom": uom,
    }
    files={'emissionsDoc': None}
    if document != 'data:':
        # shave header off
        doc_bytes = b64decode(document[28:])
        files={'emissionsDoc': doc_bytes}

    emissions_data = None
    try:
        r = requests.post(api_url, files=files, data=data)
        if r.status_code == 201:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    return emissions_data
