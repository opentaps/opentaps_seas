import warnings
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.template.base import Node

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
