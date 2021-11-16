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

from django.contrib.auth.decorators import login_required
from .common import WithBreadcrumbsMixin
from .. import fabric_registry_utils, web_socket_utils

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
        is_admin = self.request.user.is_superuser
        already_enrolled = False
        sec_type = self.kwargs["sec_type"]

        if is_admin:
            if self.request.user.org_name:
                already_enrolled = True
        else:
            if self.request.user.department:
                already_enrolled = True

        context["sec_type"] = sec_type
        context["already_enrolled"] = already_enrolled
        context["is_admin"] = is_admin

        return context


fabric_enroll = FabricEnrollView.as_view()


class FabricWebsocketkeyView(LoginRequiredMixin, WithBreadcrumbsMixin, TemplateView):
    model = User
    template_name = 'core/fabric_websocketkey.html'

    def get_context_data(self, **kwargs):
        context = super(FabricWebsocketkeyView, self).get_context_data(**kwargs)
        context["user_name"] = self.request.user.username

        return context


fabric_websocketkey = FabricWebsocketkeyView.as_view()


@login_required()
@api_view(["POST"])
def fabric_enroll_json(request):
    if request.method == "POST":
        data = request.data
        sec_type = data.get("sec_type")
        if not sec_type or sec_type not in ['vault', 'websocket']:
            return JsonResponse({"error": "Unknown security type"})

        if not request.user.is_superuser:
            return JsonResponse({"error": "Only admin is allowed to enroll users"})

        department = data.get("department")
        username = data.get("username")
        enroll_user = data.get("enroll_user")
        user = None
        if not enroll_user:
            if request.user.org_name:
                return JsonResponse({"error": "Admin is already enrolled"})
        else:
            if not department:
                return JsonResponse({"error": "Department is required"})
            if not username:
                return JsonResponse({"error": "User Name is required"})
            # find user by name and check if it is already enrolled
            user = User.objects.filter(username=username).first()
            if not user:
                return JsonResponse({"error": f"Cannot find user {username}"})
            if user.department:
                return JsonResponse({"error": "User is already enrolled"})

        admin_vault_token = None
        admin_web_socket_key = None
        if enroll_user:
            # check if admin user already has web_socket_key in session
            admin_web_socket_key = request.session.get("web_socket_key")
            if not admin_web_socket_key:
                return JsonResponse({"error": "Please, get web socket key first"})

        error = None
        try:
            if not enroll_user:
                if sec_type == 'vault':
                    vault_token, org_name = fabric_registry_utils.enroll_admin_vault()
                else:
                    web_socket_key, org_name = fabric_registry_utils.enroll_admin_web_socket()
                    request.session["web_socket_key"] = web_socket_key

                request.user.org_name = org_name
                request.user.save()
            else:
                if sec_type == 'vault':
                    if not admin_vault_token:
                        return JsonResponse({"error": "Admin vault_token is required"})
                    vault_token, org_name = fabric_registry_utils.enroll_user_vault()
                else:
                    if not admin_web_socket_key:
                        return JsonResponse({"error": "Admin web_socket_key is required"})
                    web_socket_key, org_name = fabric_registry_utils.enroll_user_web_socket(
                        username, department, admin_web_socket_key)

                user.org_name = org_name
                user.department = department
                user.save()
        except (NameError, ValueError) as e:
            error = e

        if error:
            return JsonResponse({"error": str(error)})
        else:
            return JsonResponse({"success": 1})


@login_required()
@api_view(["POST"])
def fabric_websocketkey_json(request):
    if request.method == "POST":
        data = request.data
        username = data.get("username")

        try:
            new_session = web_socket_utils.create_new_session(username)
            web_socket_key = json.dumps(new_session)
            if web_socket_key:
                request.session["web_socket_key"] = web_socket_key
            else:
                return JsonResponse({"error": "Cannot get web socket key"})

        except (NameError, ValueError) as e:
            return JsonResponse({"error": str(e)})

        return JsonResponse({"success": 1})
