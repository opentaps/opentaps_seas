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

import requests
import csv
import urllib3


class HSClient(object):

    def __init__(self, url, username=None, password=None):
        self.url = url
        self.headers = {}
        self.contentTypeHeaders = {
            'Content-Type': 'text/zinc;charset=utf-8',
            'Accept': 'text/zinc;charset=utf-8',
        }

    def get(self, url):
        """ Perform a GET request"""
        return self.do_url_request(url)

    def do_url_request(self, url, body=None, method='GET'):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        currentHeaders = self.contentTypeHeaders

        try:
            if method == 'GET':
                res = requests.get(url, headers=currentHeaders, verify=False, timeout=2)
            elif method == 'POST':
                res = requests.post(url, data=body, headers=currentHeaders, verify=False)
            else:
                raise ValueError("Method %s is not supported right now." % method)

            self.response = res.status_code
            content = res.text
        except Exception:
            print("Can't perform request to %s" % (url))
            return ""

        return content

    def about(self):
        return self.get(self.url + "/about")

    def ops(self):
        return self.get(self.url + "/ops")

    def formats(self):
        return self.get(self.url + "/formats")

    def read(self, filter=None, limit=None):
        if not filter:
            raise ValueError("filter parameter is required")

        op_url = self.url + "/read?filter=%s" % filter
        if limit:
            op_url = op_url + "&limit=%s" % limit
        return self.get(op_url)

    def nav(self, nav_id=None):
        op_url = self.url + "/nav"
        if nav_id:
            op_url = op_url + "?navId=%s" % nav_id

        return self.get(op_url)

    def his_read(self, id=None, range=None):
        if not id:
            raise ValueError("id is required")

        op_url = self.url + "/hisRead?id=%s" % (id)
        if range:
            op_url = op_url + "&range=%s" % (range)

        return self.get(op_url)

    def parse_grid(self, source):
        header = []
        data = []
        reader = csv.reader(source.splitlines(), delimiter=',', lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        line_number = 0
        for row in reader:
            if line_number == 0:
                line_number = line_number + 1
                continue
            elif line_number == 1:
                # add header
                header = row
            else:
                # add data
                data.append(row)

            line_number = line_number + 1

        return header, data
