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
from base64 import b64decode

logger = logging.getLogger(__name__)


def get_all_emissions_data(user_id, utility_id, account_number, vault_token, web_socket_key):
    emissions_data = None
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    if not web_socket_key and not vault_token:
        return None

    api_url += f"/emissionscontract/getAllEmissionsData/{utility_id}/{account_number}?userId={user_id}"
    headers = {"Accept": "application/json"}
    if web_socket_key:
        headers["web_socket_key"] = web_socket_key
    elif vault_token:
        headers["vault_token"] = vault_token

    try:
        r = requests.get(api_url, headers=headers)
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
            emission_data_set["totalEnergyUsed"] = 0.0
            if emission_data_set["renewableEnergyUseAmount"]:
                emission_data_set["totalEnergyUsed"] = float(emission_data_set["renewableEnergyUseAmount"])
            if emission_data_set["nonrenewableEnergyUseAmount"]:
                emission_data_set["totalEnergyUsed"] += float(emission_data_set["nonrenewableEnergyUseAmount"])

            if emission_data_set["tokenId"]:
                tmp = emission_data_set["tokenId"].split(":")
                if tmp and len(tmp) > 1:
                    emission_data_set["tokenId"] = tmp[1]

    return emissions_data


def get_emissions_data(user_id, emissions_id, vault_token, web_socket_key):
    emissions_data = None
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    if not web_socket_key and not vault_token:
        return None

    api_url += f"/emissionscontract/getEmissionsData/{emissions_id}?userId={user_id}"
    headers = {"Accept": "application/json"}
    if web_socket_key:
        headers["web_socket_key"] = web_socket_key
    elif vault_token:
        headers["vault_token"] = vault_token

    try:
        r = requests.get(api_url, headers=headers)
        if r.status_code == 200:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    # Format dates for display
    if emissions_data:
        emissions_data["fromDate"] = emissions_data["fromDate"].replace(
            "T", " "
        )
        emissions_data["thruDate"] = emissions_data["thruDate"].replace(
            "T", " "
        )
        if emissions_data["tokenId"]:
            tmp = emissions_data["tokenId"].split(":")
            if tmp and len(tmp) > 1:
                emissions_data["tokenId"] = tmp[1]

    return emissions_data


def record_emissions(user_id, utility_id, account_number, from_date, thru_date, amount, uom, document,
                     vault_token, web_socket_key):
    # /emissionscontract/recordEmissions
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    if not web_socket_key and not vault_token:
        return None

    api_url += f"/emissionscontract/recordEmissions?userId={user_id}"
    headers = {"Accept": "application/json"}
    if web_socket_key:
        headers["web_socket_key"] = web_socket_key
    elif vault_token:
        headers["vault_token"] = vault_token
    data = {
        "utilityId": utility_id,
        "partyId": account_number,
        "fromDate": from_date,
        "thruDate": thru_date,
        "energyUseAmount": amount,
        "energyUseUom": uom,
    }
    files = {'emissionsDoc': None}
    if document != 'data:':
        # shave header off
        doc_bytes = b64decode(document[28:])
        files = {'emissionsDoc': doc_bytes}

    emissions_data = None
    try:
        r = requests.post(api_url, files=files, data=data, headers=headers)
        if r.status_code == 201:
            emissions_data = r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(e)

    return emissions_data


def record_emissions_token(
    user_id, user_org, account_number, emissions_id, address_to_issue
):
    # /emissionscontract/recordAuditedEmissionsToken
    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    api_url += "/emissionscontract/recordAuditedEmissionsToken"

    data = {
        "userId": user_id,
        "orgName": user_org,
        "partyId": account_number,
        "emissionsRecordsToAudit": emissions_id,
        "addressToIssue": address_to_issue,
    }

    token_data = None
    timeout = False
    try:
        r = requests.post(api_url, data=data)
        if r.status_code == 201:
            token_data = r.json()
    except requests.exceptions.ConnectTimeout:
        timeout = True
    except requests.exceptions.Timeout:
        timeout = True
    except requests.exceptions.ConnectionError:
        timeout = True
    except Exception as e:
        logger.error("record_emissions_token: request error:", e)

    return token_data, timeout
