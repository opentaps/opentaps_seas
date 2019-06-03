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

from django.contrib import admin

from .forms import EntityFileUploadForm
from .forms import TagChangeForm
from .models import EntityFile
from .models import EntityNote
from .models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):

    form = TagChangeForm
    add_form = TagChangeForm
    fieldsets = (("Tag", {"fields": ("tag", "kind", "description", "details")}),)
    list_display = ["tag", "kind", "description", "details"]


@admin.register(EntityFile)
class EntityFileAdmin(admin.ModelAdmin):

    form = EntityFileUploadForm
    add_form = EntityFileUploadForm
    fieldsets = (("EntityFile", {"fields": ("entity_id", "uploaded_file")}),)
    list_display = ["id", "entity_id", "uploaded_file"]


admin.site.register(EntityNote)
