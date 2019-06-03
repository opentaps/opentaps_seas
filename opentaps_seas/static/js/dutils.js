/*
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
*/
var dutils = {};
dutils.conf = {};

dutils.urls = function(){

    function _get_path(name, kwargs, urls)
    {

        var path = urls[name] || false;

        if (!path)
        {
            throw('URL not found for view: ' + name);
        }

        var _path = path;

        var key;
        for (key in kwargs)
        {
            if (kwargs.hasOwnProperty(key)) {
                if (!path.match('<' + key +'>'))
                {
                    throw(key + ' does not exist in ' + _path);
                }
                path = path.replace('<' + key +'>', kwargs[key]);
            }
        }

        var re = new RegExp('<[a-zA-Z0-9-_]{1,}>', 'g');
        var missing_args = path.match(re);
        if (missing_args)
        {
            throw('Missing arguments (' + missing_args.join(", ") + ') for url ' + _path);
        }

        return path;

    }

    return {

        resolve: function(name, kwargs, urls) {
            if (!urls)
            {
                urls = dutils.conf.urls || {};
            }

            return _get_path(name, kwargs, urls);
        },

        /* some shortcut methods */
        resolve_tag_linked_value(tag) {
            if (!tag || !tag.tag || !tag.value) return null
            if (tag.tag == 'siteRef') return this.resolve('site_detail', { id: tag.slug||tag.value })
            if (tag.tag == 'modelRef') return this.resolve('model_detail', { id: tag.slug||tag.value })
            if (tag.tag == 'equipRef') return this.resolve('equipment_detail', { id: tag.slug||tag.value })
            return null
        },
        model_link(item) {
            return item ? this.resolve('model_detail', { id: item.entity_id }) : null
        },

    };

}();
