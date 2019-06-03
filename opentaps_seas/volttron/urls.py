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

from django.urls import path

from .views import (
    status_view,
    agent_view,
    start_agent,
    stop_agent,
    delete_agent_config,
    store_agent_config
)

app_name = "volttron"
urlpatterns = [
    path("", view=status_view, name="default"),
    path("status", view=status_view, name="status"),
    path("agents/<str:platform>/<str:agent>/view", view=agent_view, name="agent_view"),
    path("agents/<str:platform>/<str:agent>/start", view=start_agent, name="start_agent"),
    path("agents/<str:platform>/<str:agent>/stop", view=stop_agent, name="stop_agent"),
    path("agents/<str:platform>/<str:agent>/delete_config", view=delete_agent_config, name="delete_agent_config"),
    path("agents/<str:platform>/<str:agent>/store_config", view=store_agent_config, name="store_agent_config")
]
