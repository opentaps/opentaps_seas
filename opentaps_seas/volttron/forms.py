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

from .utils import VolttronClient
from ..core.models import Entity
from ..core.services import ServiceForm

logger = logging.getLogger(__name__)


class BaseTopicMismatch(Exception):
    pass


class BaseTopicExhausted(Exception):
    pass


class VolttronServiceForm(ServiceForm):

    def get_volttron_client(self):
        client = VolttronClient()
        if not client.configured:
            raise Exception('VolttronClient not configured')
        return client

    def get_platform(self):
        # platform is optional, in which case we can also auto detect
        # the platform
        client = self.get_volttron_client()
        platforms = client.list_platforms()
        if not platforms:
            raise Exception('no Volttron platform found')
        platform = None
        if 'platform' in self.inputs and self.cleaned_data['platform']:
            # lookup the platform by uuid
            platform = client.find_platform_by_uuid(self.cleaned_data['platform'])
            if not platform:
                raise Exception('Volttron Platform [{}] not found'.format(self.cleaned_data['platform']))
            logger.info('VolttronServiceForm found platform %s', platform)
        else:
            logger.info('VolttronServiceForm no platform specified.')
        return platform

    def get_agent(self):
        # the agent can be optional, if given lookup by uuiid then identity
        # else lookup by the default identity
        client = self.get_volttron_client()

        platform = self.get_platform()

        agent = client.find_agent_by_uuid(self.cleaned_data['agent'], platform=platform)
        if not agent:
            agent = client.find_agent_by_identity(self.cleaned_data['agent'], platform=platform)
        if not agent:
            raise Exception('Volttron Agent [{}] not found'.format(self.cleaned_data['agent']))
        logger.info('VolttronServiceForm found agent %s', agent)
        if not platform:
            # must get the platform from the agent
            platform = agent.get('platform_uuid')
            if not platform:
                raise Exception('Could not determine a platform from the Volttron Agent')
        agent['platform'] = platform
        return agent


class VolttronAppConfigService(VolttronServiceForm):

    def execute(self):
        logger.info('VolttronAppConfigService executing ...')
        if not self.is_valid():
            logger.error('VolttronAppConfigService invalid inputs: %s', self.errors.as_json())
            raise Exception('validation error {}'.format(self.errors.as_data()))

        logger.info('VolttronAppConfigService executing with %s', self.cleaned_data)

        client = self.get_volttron_client()
        agent = self.get_agent()
        platform = agent.get('platform')
        devices = []
        devices_errors = []

        # run for each matching equipments
        for equipment in self.get_matching_equipments():
            try:
                logger.info('VolttronAppConfigService found Equipment %s', equipment)
                points = Entity.objects.filter(kv_tags__equipRef=equipment.kv_tags['id'])

                errors = []

                # first check we can find all the datapoints
                data_points = {}
                for field in self.datapoint_fields:
                    data_points[field['name']] = self._find_data_point(points, errors, field['name'])

                if errors:
                    devices_errors.append({'equipment': equipment.kv_tags['id'], 'errors': errors})
                    # keep processing other equipments
                    continue

                mapping = {}
                base = None

                # prepare the mapping configuration and try to find a common base
                # some equipments may have multiple points matching and multiple topic bases
                # try to explore all possibility
                base = self._guess_devices(data_points, mapping)
                config_topic = base
                base_split = base.split('/', 2)
                if len(base_split) > 2:
                    base = '/'.join(base_split[:2])

                if errors:
                    devices_errors.append({'equipment': equipment.kv_tags['id'], 'errors': errors})
                    # keep processing other equipments
                    continue
            except Exception as e:
                devices_errors.append({'equipment': equipment.entity_id, 'errors': [str(e)]})
                continue

            logger.info('VolttronAppConfigService Topics Mapping %s', mapping)

            # finally add the device configuration to the Economizer Agent
            # note: config_name is prefixed with #equipmentId to allow multiple
            # equipments to use the same topic base (but different sub unit mappings)
            device = {
                'equipment': equipment,
                'base': base,
                'name': 'devices/' + config_topic + '#' + equipment.kv_tags['id'],
                'mapping': mapping
            }
            # this may raise exceptions if the output definition is invalid
            self.create_outputs(device)
            # store the Volttron config
            client.store_agent_config(platform, agent, device['name'], {"point_mapping": device['mapping']})
            devices.append(device)

        return {
            "success": len(devices),
            "errors": len(devices_errors),
            "result": {
                "platform": platform, "agent": agent, "devices": devices, "errors": devices_errors
            }
        }

    def _guess_devices(self, data_points, mapping, ignore_bases=[], depth=1):
        base = None
        mapping.clear()
        for field in self.datapoint_fields:
            f_point = data_points[field['name']]
            if f_point:
                try:
                    b = self._add_mapping(mapping, f_point, field['name'],
                                          base=base, ignore_bases=ignore_bases, depth=depth)
                    if not base:
                        base = b
                except BaseTopicMismatch:
                    if base:
                        ignore_bases.append(base)
                        # try again but ignore this failed topic base
                        return self._guess_devices(data_points, mapping, ignore_bases, depth)
                    else:
                        raise
                except BaseTopicExhausted:
                    # try again with a deeper level
                    return self._guess_devices(data_points, mapping, ignore_bases, depth+1)
        return base

    def _find_data_point(self, points, errors, param_name):
        rule = self.cleaned_data[param_name]
        p = self.apply_entity_rule(rule, points)
        if not p:
            msg = 'Data Point for {} not found using {}'.format(param_name, rule)
            logger.error(msg)
            errors.append(msg)
        else:
            if len(p) > 1:
                logger.info('Found more than one data point for %s using %s ...', param_name, rule)
            logger.info('VolttronAppConfigService found %s -> %s', param_name, p)
        return p

    def _add_mapping(self, mapping, points, volttron_name, base=None, ignore_bases=[], depth=1):
        topic_bases = []
        for point in points:
            # use the first point matching the base
            ts = point.topic.rsplit('/', depth)
            topic_base = ts[0]
            if topic_base in ignore_bases:
                logger.info('VolttronAppConfigService ignore base %s', topic_base)
                continue
            if base and base != topic_base:
                topic_bases.append(topic_base)
                continue
            if depth > 1:
                topic_name = '/'.join(ts[1:])
            else:
                topic_name = ts[-1]
            if topic_name != volttron_name:
                mapping[topic_name] = volttron_name
            logger.info('VolttronAppConfigService for %s using topic %s with base %s',
                        volttron_name, topic_name, topic_base)
            return topic_base
        # not found
        if topic_bases:
            raise BaseTopicMismatch('{} Topic Bases {} did not match the previous topic base {}'.format(
                            volttron_name, topic_bases, base))
        else:
            raise BaseTopicExhausted('{} No more Topic Base to try, ignored {}'.format(volttron_name, ignore_bases))
