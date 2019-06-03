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
import requests
import uuid

from django.conf import settings


logger = logging.getLogger(__name__)


class InvalidPlatformException(Exception):
    pass


class InvalidAgentException(Exception):
    pass


class InvalidResponseException(Exception):
    pass


class AuthenticationException(Exception):
    pass


class VolttronClient():

    __instance = None

    def __new__(cls):
        if not VolttronClient.__instance:
            VolttronClient.__instance = VolttronClient.__VolttronClient()
        return VolttronClient.__instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)

    class __VolttronClient():

        def __init__(self):
            self.vc_url = settings.VOLTTRON_VC_URL
            self.vc_login = settings.VOLTTRON_VC_USER_NAME
            self.vc_password = settings.VOLTTRON_VC_PASSWORD
            logger.info('VolttronClient: init url = %s, login = %s', self.vc_url, self.vc_login)
            self.configured = self.vc_url and self.vc_login and self.vc_password
            self.connected = False
            self.auth_token = None
            self.platforms = []
            self.platform_dict = {}
            self.agent_dict = {}
            self.agent_uuid_dict = {}

        def __read_platform_id(self, platform):
            if isinstance(platform, dict):
                platform_uuid = platform.get("uuid")
            else:
                platform_uuid = platform
            if not platform_uuid:
                logger.error('VolttronClient: invalid platform %s', platform)
                raise InvalidPlatformException('invalid platform {}'.format(platform))
            return platform_uuid

        def __read_agent_id(self, agent):
            if isinstance(agent, dict):
                agent_id = agent.get("identity")
            else:
                agent_id = agent
            if not agent_id:
                logger.error('VolttronClient: invalid agent %s', agent)
                raise InvalidAgentException('invalid agent {}'.format(agent))
            return agent_id

        def __read_agent_uuid(self, agent):
            if isinstance(agent, dict):
                agent_id = agent.get("uuid")
            else:
                agent_id = agent
            if not agent_id:
                logger.error('VolttronClient: invalid agent %s', agent)
                raise InvalidAgentException('invalid agent {}'.format(agent))
            return agent_id

        def __read_json_response(self, data, r):
            if r.status_code == 200:
                r_json = r.json()
                if r_json.get('id') == data.get('id') and 'result' in r_json:
                    return r_json
                else:
                    if r_json.get('id') != data.get('id'):
                        raise InvalidResponseException('response ID did not match the request ID')
                    elif 'result' not in r_json:
                        if 'error' in r_json:
                            raise InvalidResponseException(r_json.get('error'))

                        raise InvalidResponseException('response did not include a "result" field')
            elif r.status_code == 401:
                raise AuthenticationException()
            else:
                raise InvalidResponseException('unexpected response code {} -> {}'.format(r.status_code, r.text))

        def prepare_data(self, data={}):
            d = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4())
            }
            d.update(data)
            return d

        def prepare_data_with_auth(self, data={}):
            d = self.prepare_data(data)
            if not self.connected:
                self.connect()
            if not self.connected:
                raise Exception('Volttron authentication required')
            d.update({"authorization": self.auth_token})
            return d

        def post(self, data):
            logger.info('VolttronClient: post data %s', data)
            r = requests.post(self.vc_url, verify=False, json=data)
            logger.info('VolttronClient: response %s -> %s', r, r.text)
            return r

        def post_and_read(self, data, retry_auth=True):
            try:
                return self.__read_json_response(data, self.post(data))
            except AuthenticationException:
                if not retry_auth:
                    raise
                else:
                    self.disconnect()
                    self.connect()
                    data.update({"authorization": self.auth_token})
                    return self.__read_json_response(data, self.post(data))

        def connect(self):
            logger.info('VolttronClient: connecting to %s with %s / %s', self.vc_url, self.vc_login, '****')
            data = self.prepare_data({
                "method": "get_authorization",
                "params": {
                    "username": self.vc_login,
                    "password": self.vc_password
                }
            })
            r_json = self.post_and_read(data, retry_auth=False)
            self.connected = True
            self.auth_token = r_json.get('result')
            logger.info('VolttronClient: Connected with auth token %s', self.auth_token)

        def disconnect(self):
            self.connected = False
            self.auth_token = None

        def find_platform_by_uuid(self, uuid):
            if not self.platform_dict:
                self.list_platforms()
            if self.platform_dict and uuid in self.platform_dict:
                return self.platform_dict[uuid]
            return None

        def find_agent_by_uuid(self, uuid, platform=None):
            if not self.platform_dict:
                self.list_platforms()
            if platform:
                agents = platform.get('agents', [])
                for agent in agents:
                    if uuid == agent.get('uuid'):
                        return agent
            elif self.platform_dict:
                for k, platform in self.platform_dict.items():
                    agents = platform.get('agents', [])
                    for agent in agents:
                        if uuid == agent.get('uuid'):
                            return agent
            return None

        def find_agent_by_identity(self, identity, platform=None):
            if not self.platform_dict:
                self.list_platforms()
            if platform:
                agents = platform.get('agents', [])
                for agent in agents:
                    if identity == agent.get('identity'):
                        return agent
            elif self.platform_dict:
                for k, platform in self.platform_dict.items():
                    agents = platform.get('agents', [])
                    for agent in agents:
                        if identity == agent.get('identity'):
                            return agent
            return None

        def list_platforms(self, with_agents=True):
            logger.info('VolttronClient: list_platforms ...')
            data = self.prepare_data_with_auth({
                "method": "list_platforms"
            })
            r_json = self.post_and_read(data)
            self.platforms = r_json.get('result')
            if self.platforms:
                for platform in self.platforms:
                    if 'uuid' in platform:
                        self.platform_dict[platform['uuid']] = platform
                        if with_agents:
                            self.list_platform_agents(platform)
            logger.info('VolttronClient: Found platforms %s', self.platforms)
            return self.platforms

        def list_platform_agents(self, platform):
            platform_uuid = self.__read_platform_id(platform)

            logger.info('VolttronClient: list_agents for platform %s', platform_uuid)
            data = self.prepare_data_with_auth({
                "method": "list_agents",
                "params": {
                    "platform_uuid": platform_uuid
                }
            })
            r_json = self.post_and_read(data)
            agents = r_json.get('result')
            logger.info('VolttronClient: Found agents %s', agents)
            if platform_uuid in self.platform_dict:
                platform = self.platform_dict[platform_uuid]
                for agent in agents:
                    agent['platform_uuid'] = platform_uuid
                platform.update({'agents': agents})
                for agent in agents:
                    self.agent_dict[platform_uuid + agent.get('identity')] = agent
                    self.agent_uuid_dict[platform_uuid + agent.get('uuid')] = agent
                logger.info('VolttronClient: Added to known platform %s', platform)
            return agents

        def start_agent(self, platform, agent):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_uuid(agent)

            logger.info('VolttronClient: start_agent platform %s agent %s',
                        platform_uuid, agent_id)
            data = self.prepare_data_with_auth({
                "method": "platforms.uuid.{}.start_agent".format(platform_uuid),
                "params": [agent_id]
            })
            r_json = self.post_and_read(data)
            process_result = r_json.get('result')
            logger.info('VolttronClient: Start agent %s = %s', agent_id, process_result)
            return process_result

        def stop_agent(self, platform, agent):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_uuid(agent)

            logger.info('VolttronClient: stop_agent platform %s agent %s',
                        platform_uuid, agent_id)
            data = self.prepare_data_with_auth({
                "method": "platforms.uuid.{}.stop_agent".format(platform_uuid),
                "params": [agent_id]
            })
            r_json = self.post_and_read(data)
            process_result = r_json.get('result')
            logger.info('VolttronClient: Stop agent %s = %s', agent_id, process_result)
            return process_result

        def list_agent_configs(self, platform, agent):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_id(agent)

            logger.info('VolttronClient: list_agent_configs for platform %s agent %s', platform_uuid, agent_id)
            data = self.prepare_data_with_auth({
                "method": "list_agent_configs",
                "params": {
                    "platform_uuid": platform_uuid,
                    "agent_identity": agent_id
                }
            })
            r_json = self.post_and_read(data)
            agent_config = r_json.get('result')
            logger.info('VolttronClient: Found agent config %s', agent_config)
            if platform_uuid in self.platform_dict:
                agent = self.agent_dict.get(platform_uuid + agent_id)
                if agent:
                    agent.update({'config': agent_config})
                    logger.info('VolttronClient: Added to known agent %s', agent)
            return agent_config

        def get_agent_config(self, platform, agent, config_name):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_id(agent)

            logger.info('VolttronClient: get_agent_config %s for platform %s agent %s',
                        config_name, platform_uuid, agent_id)
            data = self.prepare_data_with_auth({
                "method": "get_agent_config",
                "params": {
                    "platform_uuid": platform_uuid,
                    "agent_identity": agent_id,
                    "config_name": config_name
                }
            })
            r_json = self.post_and_read(data)
            agent_config = r_json.get('result')
            logger.info('VolttronClient: Found config %s = %s', config_name, agent_config)
            return agent_config

        def delete_agent_config(self, platform, agent, config_name):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_id(agent)

            logger.info('VolttronClient: delete_agent_config %s for platform %s agent %s',
                        config_name, platform_uuid, agent_id)
            data = self.prepare_data_with_auth({
                "method": "delete_agent_config",
                "params": {
                    "platform_uuid": platform_uuid,
                    "agent_identity": agent_id,
                    "config_name": config_name
                }
            })
            r_json = self.post_and_read(data)
            delete_result = r_json.get('result')
            logger.info('VolttronClient: Deleted config %s result = %s', config_name, delete_result)
            return delete_result

        def store_agent_config(self, platform, agent, config_name, value, config_type="json", raw=False):
            platform_uuid = self.__read_platform_id(platform)
            agent_id = self.__read_agent_id(agent)

            logger.info('VolttronClient: store_agent_config %s for platform %s agent %s',
                        config_name, platform_uuid, agent_id)
            if not raw and 'json' == config_type:
                raw_contents = json.dumps(value)
            else:
                raw_contents = value
            data = self.prepare_data_with_auth({
                "method": "store_agent_config",
                "params": {
                    "platform_uuid": platform_uuid,
                    "agent_identity": agent_id,
                    "config_type": config_type,
                    "config_name": config_name,
                    "raw_contents": raw_contents
                }
            })
            r_json = self.post_and_read(data)
            store_result = r_json.get('result')
            logger.info('VolttronClient: Store config %s result %s', config_name, store_result)
            return store_result
