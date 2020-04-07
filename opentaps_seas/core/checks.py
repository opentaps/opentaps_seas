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

from django.conf import settings
from django.core.checks import Warning, register


@register()
def check_encryption_key(app_configs, **kwargs):
    errors = []
    if not settings.FIELD_ENCRYPTION_KEY or settings.FIELD_ENCRYPTION_KEY == '_______PLEASE_______CHANGE______THIS_______=':
        errors.append(
            Warning(
                'Unsecure Enryption Key',
                hint='You can generate a key with: "./manage.py generate_encryption_key" then put it in FIELD_ENCRYPTION_KEY in secrets.json',
                obj=settings,
                id='opentaps_seas.W001',
            )
        )
    return errors


@register()
def check_aws_config(app_configs, **kwargs):
    errors = []
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_STORAGE_BUCKET_NAME:
        errors.append(
            Warning(
                'Missing AWS configuration, file storage will be unavailable',
                hint='''Make sure you set AWS_ACCESS_KEY_ID,
                        AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME in secrets.json''',
                obj=settings,
                id='opentaps_seas.W002',
            )
        )
    return errors


@register()
def check_openei_config(app_configs, **kwargs):
    errors = []
    if not settings.OPENEI_API_KEY:
        errors.append(
            Warning(
                'Missing openei API configuration',
                hint='Make sure you set OPENEI_API_KEY in secrets.json',
                obj=settings,
                id='opentaps_seas.W003',
            )
        )
    return errors


@register()
def check_utilityapi_config(app_configs, **kwargs):
    errors = []
    if not settings.UTILITY_API_KEY:
        errors.append(
            Warning(
                'Missing utilityapi configuration',
                hint='Make sure you set UTILITY_API_KEY in secrets.json',
                obj=settings,
                id='opentaps_seas.W004',
            )
        )
    return errors
