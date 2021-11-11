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


def check_configs():
    if not settings.EMISSIONS_API_URL:
        raise NameError("Missing Emissions API configuration")

    if not settings.WEB_SOCKET_API_URL:
        raise NameError("Missing Emissions API configuration")

    if not settings.FABRIC_ADMIN_NAME:
        raise NameError("Missing Fabric Admin Name configuration")


def create_new_session():
    try:
        check_configs()
    except (NameError, ValueError) as e:
        raise e

    url = settings.WEB_SOCKET_API_URL + "/session/new"
    endpoint = settings.EMISSIONS_API_URL + "/identity/webSocket"

    headers = {"Content-type": "application/json"}

    data = {"key_name": settings.FABRIC_ADMIN_NAME, "endpoint": endpoint}

    try:
        r = requests.post(url, data=json.dumps(data), headers=headers)
        if r.status_code == 200:
            session_signature = r.json()
        else:
            raise ValueError("Cannot create web socket session")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(e)

    return session_signature
