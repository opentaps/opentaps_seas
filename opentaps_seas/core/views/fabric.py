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

from django.contrib.auth.decorators import login_required
from .common import WithBreadcrumbsMixin
from .. import fabric_registry_utils

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView
from opentaps_seas.users.models import User
from rest_framework.decorators import api_view


logger = logging.getLogger(__name__)


class FabricEnrollView(LoginRequiredMixin, WithBreadcrumbsMixin, TemplateView):
    model = User
    template_name = 'core/fabric_enroll.html'

    def get_context_data(self, **kwargs):
        context = super(FabricEnrollView, self).get_context_data(**kwargs)
        user_id = self.request.user.id
        user_name = self.request.user.username
        is_admin = self.request.user.is_superuser
        already_enrolled = False
        sec_type = self.kwargs["sec_type"]

        if sec_type == 'vault':
            if self.request.user.vault_token:
                already_enrolled = True
        elif sec_type == 'websocket':
            if self.request.user.web_socket_key:
                already_enrolled = True

        context["sec_type"] = sec_type
        context["user_id"] = user_id
        context["user_name"] = user_name
        context["already_enrolled"] = already_enrolled
        context["is_admin"] = is_admin

        return context


fabric_enroll = FabricEnrollView.as_view()


@login_required()
@api_view(["POST"])
def fabric_enroll_json(request):
    if request.method == "POST":
        data = request.data
        sec_type = data.get("sec_type")
        if not sec_type or sec_type not in ['vault', 'websocket']:
            return JsonResponse({"error": "Unknown security type"})
        if request.user.vault_token:
            return JsonResponse({"error": "Already enrolled"})

        admin_web_socket_key = None
        admin_vault_token = None
        department = None
        if not request.user.is_superuser:
            department = data.get("department")
            if not department:
                return JsonResponse({"error": "Department is required"})
            # get admin keys
            admin = User.objects.filter(username="admin", is_superuser=True).first()
            if admin:
                admin_web_socket_key = admin.web_socket_key
                admin_vault_token = admin.vault_token

        error = None
        token = None
        web_socket_key = None
        try:
            if request.user.is_superuser:
                if sec_type == 'vault':
                    token = fabric_registry_utils.enroll_admin_vault()
                else:
                    web_socket_key = fabric_registry_utils.enroll_admin_web_socket()
            else:
                if sec_type == 'vault':
                    if not admin_vault_token:
                        return JsonResponse({"error": "Admin vault_token is required"})
                    token = fabric_registry_utils.enroll_user_vault()
                else:
                    if not admin_web_socket_key:
                        return JsonResponse({"error": "Admin web_socket_key is required"})
                    web_socket_key = fabric_registry_utils.enroll_user_web_socket(
                        request.user.username, department, admin_web_socket_key)
        except (NameError, ValueError) as e:
            error = e

        if error:
            return JsonResponse({"error": str(error)})
        elif token or web_socket_key:
            if token:
                request.user.vault_token = token
            if web_socket_key:
                request.user.web_socket_key = web_socket_key
            if department:
                request.user.department = department
            request.user.save()
            return JsonResponse({"success": 1})
        else:
            return JsonResponse({"error": "Cannot enroll"})
