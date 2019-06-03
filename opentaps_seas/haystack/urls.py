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
    about_view,
    formats_view,
    ops_view,
    nav_view,
    hisread_view,
    read_view
)

app_name = "haystack"
urlpatterns = [
    path("about", view=about_view, name="about"),
    path("ops", view=ops_view, name="ops"),
    path("formats", view=formats_view, name="formats"),
    path("nav", view=nav_view, name="nav"),
    path("hisRead", view=hisread_view, name="hisRead"),
    path("read", view=read_view, name="read"),
]
