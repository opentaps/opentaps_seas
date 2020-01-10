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

import warnings
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.template.base import Node
from .. import utils

register = template.Library()


class JsCsrfTokenNode(Node):
    def render(self, context):
        csrf_token = context.get('csrf_token')
        if csrf_token:
            if csrf_token == 'NOTPROVIDED':
                return mark_safe("")
            else:
                return mark_safe(csrf_token)
        else:
            # It's very probable that the token is missing because of
            # misconfiguration, so we raise a warning
            if settings.DEBUG:
                warnings.warn(
                    "A {% js_csrf_token %} was used in a template, but the context "
                    "did not provide the value.  This is usually caused by not "
                    "using RequestContext."
                )
            return ''


@register.tag
def js_csrf_token(parser, token):
    return JsCsrfTokenNode()


def fmttime_str(value):
    epoch = int(value.timestamp() * 1000)
    t = utils.format_epoch(epoch)
    return t['fmttime']


def time_str(value):
    epoch = int(value.timestamp() * 1000)
    t = utils.format_epoch(epoch)
    return t['time']


register.filter('time_str', time_str)
register.filter('fmttime_str', fmttime_str)