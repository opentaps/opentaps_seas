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
import json
from ..forms.hyperledger import HyperLedgerQueryAdminForm, HyperLedgerEnrollUserForm
from django.shortcuts import render, redirect
from opentaps_seas.users.models import User
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.conf import settings

logger = logging.getLogger(__name__)



API_URL = settings.EMISSIONS_API_URL
ENROLL_ADMIN_URL = API_URL + "/registerEnroll/admin"
ENROLL_USER_URL = API_URL + "/registerEnroll/user"


def hyperledger_query_admin_view(request):
    if request.method == "POST":
        form = HyperLedgerQueryAdminForm(request.POST)
        context = {}
        if form.is_valid():
            name = form.cleaned_data["name"]
            data = {"orgName": name}
            headers = {"Content-type": "application/json", "Accept": "application/json"}
            print("calling url here\n\n\n\n\n\n")
            print(ENROLL_ADMIN_URL)
            response = requests.post(
                ENROLL_ADMIN_URL, data=json.dumps(data), headers=headers
            )
            if response.status_code == 409:
                response_message = response.json()["info"]
                # Handle admin name already exists
                if (
                    response_message
                    == "An identity for the admin user already exists in the wallet"
                ):
                    context["name"] = name
                    context["exists"] = "existing"
                    return HttpResponseRedirect(
                        reverse("core:hyperledger_query_admin_success", kwargs=context)
                    )

                # Handle name not allowed
                else:
                    context[
                        "response"
                    ] = f"The requested organization name {name} is not allowed."
                    return redirect("success/", kwargs=context)

            # Handle admin add success
            elif response.status_code == 201:
                context["name"] = name
                context["exists"] = "new"
                return HttpResponseRedirect(
                    reverse("core:hyperledger_query_admin_success", kwargs=context)
                )
            else:
                return

    form = HyperLedgerQueryAdminForm()
    return render(request, "core/hyperledger_query_admin.html", {"form": form})


def hyperledger_query_admin_success_view(request, **kwargs):
    all_users = User.objects.all()
    context = kwargs
    context["all_users"] = all_users
    return render(request, "core/hyperledger_query_admin_success.html", context,)


def hyperledger_enroll_view(request, **kwargs):
    if request.method == "POST":
        form = HyperLedgerEnrollUserForm(request.POST)
        context = {"user": kwargs["user"], "org_name": kwargs["org_name"]}
        if form.is_valid():
            user = User.objects.filter(username=kwargs["user"]).first()
            user_id = user.username
            affiliation = form.cleaned_data["affiliation"]
            org_name = kwargs["org_name"]
            data = {
                "userId": str(user_id),
                "orgName": org_name,
                "affiliation": f"{org_name}.{affiliation}",
            }
            headers = {"Content-type": "application/json", "Accept": "application/json"}
            response = requests.post(
                ENROLL_USER_URL, data=json.dumps(data), headers=headers
            )
            if response.status_code == 409:
                context["result"] = "failure"
                return HttpResponseRedirect(
                    reverse("core:hyperledger_enroll_result", kwargs=context)
                )
            elif response.status_code == 201:
                user.org_name = org_name
                user.save()
                context["result"] = "success"
                return HttpResponseRedirect(
                    reverse("core:hyperledger_enroll_result", kwargs=context)
                )
            else:
                context["result"] = "failure"
                return HttpResponseRedirect(
                    reverse("core:hyperledger_enroll_result", kwargs=context)
                )

    context = kwargs
    form = HyperLedgerEnrollUserForm(request.POST)
    context["form"] = form
    return render(request, "core/hyperledger_enroll.html", context)


def hyperledger_enroll_result_view(request, **kwargs):
    context = kwargs
    return render(request, "core/hyperledger_enroll_result.html", context,)
