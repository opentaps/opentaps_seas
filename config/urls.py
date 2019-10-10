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
from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from django.views import defaults as default_views
from .views import home_page_view


urlpatterns = [
    path("", view=home_page_view, name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path(
        "users/",
        include("opentaps_seas.users.urls", namespace="users"),
    ),
    # Our Apps
    path(
        "opentaps_seas/",
        include("opentaps_seas.core.urls", namespace="core"),
    ),
    path(
        "haystack/",
        include("opentaps_seas.haystack.urls", namespace="haystack"),
    ),
    path(
        "volttron/",
        include("opentaps_seas.volttron.urls", namespace="volttron"),
    ),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
] + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

if 'opentaps_seas.opentaps_seas_addons.apps.AddonsAppConfig' in settings.INSTALLED_APPS:
    from django.conf.urls import url
    from rest_framework_simplejwt import views as jwt_views

    urlpatterns += [
        path(
            "api/v1/",
            include("opentaps_seas.opentaps_seas_addons.urls", namespace="opentaps_seas_addons")
        ),

        url(r'^api/v1/token/?$', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
        url(r'^api/v1/token/refresh/?$', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    ]
