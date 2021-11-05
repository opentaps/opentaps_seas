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
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def enroll_admin_vault(user):
    if user and user["vault_token"]:
        raise ValueError("Admin user already enrolled")

    if settings.EMISSIONS_API_URL:
        api_url = settings.EMISSIONS_API_URL
    else:
        raise NameError("Missing Emissions API configuration")

    if settings.VAULT_IDENTITY_API_URL:
        vault_api_url = settings.VAULT_IDENTITY_API_URL
    else:
        raise NameError("Missing Vault Identity API configuration")

    if settings.VAULT_TOKEN:
        vault_token = settings.VAULT_TOKEN
    else:
        raise NameError("Missing Vault Token configuration")

    if settings.FABRIC_ADMIN_NAME:
        fabric_admin_name = settings.FABRIC_ADMIN_NAME
    else:
        raise NameError("Missing Fabric Admin Name configuration")

    if settings.FABRIC_ADMIN_PASSWORD:
        fabric_admin_password = settings.FABRIC_ADMIN_PASSWORD
    else:
        raise NameError("Missing Fabric Admin Password configuration")

    enroll_url = api_url + "/registerEnroll/enroll"
    vault_identity_url = vault_api_url + "/identity"
    vault_token_url = vault_api_url + "/token"
    vault_key_url = vault_api_url + "/key?kty=ecdsa-p256"

    headers = {"Content-type": "application/json",
               "Accept": "application/json",
               "Authorization": "Bearer " + vault_token
               }

    data = {"username": fabric_admin_name, "identity_type": "MANAGER"}

    try:
        r = requests.post(vault_identity_url, data=json.dumps(data), headers=headers)
        if r.status_code == 201:
            identity = r.json()
        else:
            raise ValueError("Cannot create admin identity")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    if identity and identity["password"]:
        password = identity["password"]
    else:
        raise ValueError("Cannot get admin identity password")

    headers = {"Accept": "application/json",
               "username": fabric_admin_name,
               "password": password
               }

    try:
        r = requests.post(vault_token_url, headers=headers)
        if r.status_code == 200:
            token_response = r.json()
        else:
            raise ValueError("Cannot create admin token")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    if token_response and token_response["token"]:
        token = token_response["token"]
    else:
        raise ValueError("Cannot get admin token")

    headers = {"Accept": "*/*",
               "Authorization": "Bearer " + token
               }

    try:
        r = requests.post(vault_key_url, headers=headers)
        if not r.status_code == 201:
            raise ValueError("Cannot create transit key ")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    headers = {"Content-type": "application/json",
               "Accept": "*/*",
               "vault_token": token
               }

    data = {"enrollmentID": fabric_admin_name, "enrollmentSecret": fabric_admin_password}

    try:
        r = requests.post(enroll_url, data=json.dumps(data), headers=headers)
        if not r.status_code == 201:
            raise ValueError("Cannot enroll admin")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return token
