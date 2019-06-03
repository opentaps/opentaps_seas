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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from .utils import VolttronClient
from ..core.models import Entity

logger = logging.getLogger(__name__)


class StatusView(LoginRequiredMixin, TemplateView):
    template_name = 'volttron/status.html'

    def get_context_data(self, **kwargs):
        context = super(StatusView, self).get_context_data(**kwargs)

        client = VolttronClient()

        if not client.configured:
            context['volttron_vc_configuration_needed'] = True
            logger.error('Volttron settings are incomplete')
            return context

        try:
            context['platforms'] = client.list_platforms()
        except Exception as e:
            context['volttron_vc_error'] = str(e)

        return context


status_view = StatusView.as_view()


class AgentView(LoginRequiredMixin, TemplateView):
    template_name = 'volttron/agent_view.html'

    def get_context_data(self, **kwargs):
        context = super(AgentView, self).get_context_data(**kwargs)

        client = VolttronClient()

        if not client.configured:
            context['volttron_vc_configuration_needed'] = True
            logger.error('Volttron settings are incomplete')
            return context

        platform_uuid = self.kwargs['platform']
        agent_uuid = self.kwargs['agent']
        agent_key = platform_uuid + agent_uuid
        context['platform_uuid'] = platform_uuid
        context['agent_uuid'] = agent_uuid
        agent = client.agent_uuid_dict.get(agent_key)
        if not agent:
            logger.warn('Volttron agent %s not found in platform %s', agent_uuid, platform_uuid)
            try:
                context['platforms'] = client.list_platforms()
                agent = client.agent_uuid_dict.get(agent_key)
            except Exception as e:
                logger.exception('AgentView error')
                context['volttron_vc_error'] = str(e)
        if not agent:
            context['volttron_vc_error'] = 'Agent {} not found in platform {}'.format(agent_uuid, platform_uuid)
            logger.error('Volttron agent %s not found in platform %s', agent_uuid, platform_uuid)
            return context
        context['agent'] = agent
        try:
            configs = []
            agent_configs = client.list_agent_configs(platform_uuid, agent)
            for config in agent_configs:
                configs.append({'key': config, 'value': client.get_agent_config(platform_uuid, agent, config)})
            context['agent_configs'] = configs
        except Exception as e:
            logger.exception('AgentView error')
            context['volttron_vc_error'] = str(e)

        logger.info('Volttron config context: %s', context)
        return context


agent_view = AgentView.as_view()


@require_POST
@login_required()
def start_agent(request, platform, agent):
    url = reverse('volttron:status')
    client = VolttronClient()
    try:
        client.start_agent(platform, agent)
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception('start_agent error')
        messages.add_message(request, messages.ERROR, str(e))
        return HttpResponseRedirect(url)


@require_POST
@login_required()
def stop_agent(request, platform, agent):
    url = reverse('volttron:status')
    client = VolttronClient()
    try:
        client.stop_agent(platform, agent)
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception('stop_agent error')
        messages.add_message(request, messages.ERROR, str(e))
        return HttpResponseRedirect(url)


@require_POST
@login_required()
def delete_agent_config(request, platform, agent):
    url = reverse('volttron:agent_view', kwargs={"platform": platform, "agent": agent})
    client = VolttronClient()
    agent_key = platform + agent
    agent_dict = client.agent_uuid_dict.get(agent_key)
    try:
        if not agent_dict:
            logger.warn('Volttron agent %s not found in platform %s', agent, platform)
            client.list_platforms()
            agent_dict = client.agent_uuid_dict.get(agent_key)
        client.delete_agent_config(platform, agent_dict, request.POST.get('config_name'))
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception('delete_agent_config error')
        messages.add_message(request, messages.ERROR, str(e))
        return HttpResponseRedirect(url)


@require_POST
@login_required()
def store_agent_config(request, platform, agent):
    url = reverse('volttron:agent_view', kwargs={"platform": platform, "agent": agent})
    client = VolttronClient()
    agent_key = platform + agent
    agent_dict = client.agent_uuid_dict.get(agent_key)
    # optional config content
    content = request.POST.get('raw_contents')
    if not content:
        content = '{}'
    config_type = request.POST.get('config_type')
    if not config_type:
        config_type = 'json'
    try:
        if not agent_dict:
            logger.warn('Volttron agent %s not found in platform %s', agent, platform)
            client.list_platforms()
            agent_dict = client.agent_uuid_dict.get(agent_key)
        client.store_agent_config(platform, agent_dict, request.POST.get('config_name'),
                                  content, config_type=config_type, raw=True)
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.exception('store_agent_config error')
        messages.add_message(request, messages.ERROR, str(e))
        return HttpResponseRedirect(url)
