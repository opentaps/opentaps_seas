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
from . import web_socket_utils

logger = logging.getLogger(__name__)


def check_configs():
    if not settings.EMISSIONS_API_URL:
        raise NameError("Missing Emissions API configuration")

    if not settings.EMISSIONS_API_ORGNAME:
        raise NameError("Missing Organization Name configuration")

    if not settings.VAULT_IDENTITY_API_URL:
        raise NameError("Missing Vault Identity API configuration")

    if not settings.VAULT_TOKEN:
        raise NameError("Missing Vault Token configuration")

    if not settings.FABRIC_ADMIN_NAME:
        raise NameError("Missing Fabric Admin Name configuration")

    if not settings.FABRIC_ADMIN_PASSWORD:
        raise NameError("Missing Fabric Admin Password configuration")


def enroll_admin_vault():
    try:
        check_configs()
    except (NameError, ValueError) as e:
        raise e

    enroll_url = settings.EMISSIONS_API_URL + "/registerEnroll/enroll"
    vault_identity_url = settings.VAULT_IDENTITY_API_URL + "/identity"
    vault_token_url = settings.VAULT_IDENTITY_API_URL + "/token"
    vault_key_url = settings.VAULT_IDENTITY_API_URL + "/key?kty=ecdsa-p256"

    headers = {"Content-type": "application/json",
               "Accept": "application/json",
               "Authorization": "Bearer " + settings.VAULT_TOKEN
               }

    data = {"username": settings.FABRIC_ADMIN_NAME, "identity_type": "MANAGER"}

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
               "username": settings.FABRIC_ADMIN_NAME,
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

    data = {"enrollmentID": settings.FABRIC_ADMIN_NAME, "enrollmentSecret": settings.FABRIC_ADMIN_PASSWORD}

    try:
        r = requests.post(enroll_url, data=json.dumps(data), headers=headers)
        if not r.status_code == 201:
            raise ValueError("Cannot enroll admin")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return token, settings.EMISSIONS_API_ORGNAME


def enroll_user_vault():
    return None, settings.EMISSIONS_API_ORGNAME


def enroll_admin_web_socket():
    try:
        check_configs()
        new_session = web_socket_utils.create_new_session(settings.FABRIC_ADMIN_NAME)
    except (NameError, ValueError) as e:
        raise e

    if not new_session:
        raise ValueError("Cannot create web socket session")

    enroll_url = settings.EMISSIONS_API_URL + "/registerEnroll/enroll"
    web_socket_key = json.dumps(new_session)
    headers = {"Content-type": "application/json",
               "Accept": "*/*",
               "web_socket_key": web_socket_key
               }

    data = {"enrollmentID": settings.FABRIC_ADMIN_NAME, "enrollmentSecret": settings.FABRIC_ADMIN_PASSWORD}

    try:
        r = requests.post(enroll_url, data=json.dumps(data), headers=headers)
        if not r.status_code == 201:
            raise ValueError("Cannot enroll admin")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return web_socket_key, settings.EMISSIONS_API_ORGNAME


def enroll_user_web_socket(user_name, department, admin_web_socket_key):
    try:
        check_configs()
        identity = register_user_web_socket(user_name, department, admin_web_socket_key)
        new_session = web_socket_utils.create_new_session(user_name)
    except (NameError, ValueError) as e:
        raise e

    enroll_url = settings.EMISSIONS_API_URL + "/registerEnroll/enroll"
    web_socket_key = json.dumps(new_session)
    headers = {"Content-type": "application/json",
               "Accept": "*/*",
               "web_socket_key": web_socket_key
               }

    data = {"enrollmentID": user_name, "enrollmentSecret": identity["enrollmentSecret"]}

    try:
        r = requests.post(enroll_url, data=json.dumps(data), headers=headers)
        if not r.status_code == 201:
            raise ValueError("Cannot enroll user")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return web_socket_key, settings.EMISSIONS_API_ORGNAME


def register_user_web_socket(user_name, department, admin_web_socket_key):
    try:
        check_configs()
    except (NameError, ValueError) as e:
        raise e

    register_url = settings.EMISSIONS_API_URL + "/registerEnroll/register?userId=" + settings.FABRIC_ADMIN_NAME
    headers = {"Content-type": "application/json",
               "Accept": "application/json",
               "web_socket_key": admin_web_socket_key
               }

    affiliation = settings.EMISSIONS_API_ORGNAME + "." + department
    data = {"enrollmentID": user_name, "affiliation": affiliation}

    try:
        r = requests.post(register_url, data=json.dumps(data), headers=headers)
        if r.status_code == 201:
            identity = r.json()
        elif r.status_code == 409:
            raise ValueError("User is already registered")
        else:
            raise ValueError("Cannot register user")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return identity
