Developer Documentation
=======================



Haystack
--------

Note: Haystack id tag values are set by default to be the same as primary key values, but they do not have to be.

Project Haystack 3.0 tags are defined in ``data/tag/seed/tags_haystack.csv``  Additional tags are defined separately in ``data/tag/seed/tags_opentaps.csv``

Haystack Server
^^^^^^^^^^^^^^^

The built-in Haystack server allows you to expore your data points and data in the Haystack Zinc format to other applications.

Example of the implemented Haystack APIs::

 $ curl 'http://localhost:8000/haystack/about'
 $ curl 'http://localhost:8000/haystack/ops'
 $ curl 'http://localhost:8000/haystack/formats'

 $ curl 'http://localhost:8000/haystack/nav'
 $ curl 'http://localhost:8000/haystack/nav?navId=_demo_site'
 $ curl 'http://localhost:8000/haystack/nav?navId=_demo_equipahu1'

 $ curl 'http://localhost:8000/haystack/read?id=_demo_site'
 $ curl 'http://localhost:8000/haystack/read?id=_demo_equipahu1'
 
 $ curl 'http://localhost:8000/haystack/hisRead?id=demo_ahu1/MAT&range=today'


Haystack Client
^^^^^^^^^^^^^^^

The built-in Haystack client is in the get_haystack_data.py script.  It can be used to sync sites, equipments, data points and load historical data
into our time series database.  It works by querying the ?nav operation first to get the top level points, then recursively querying with each point
as navId= until there are no more navigation points returned.  Then it will use hisRead to get the latest historical data for the data point.  There
is also an optional range_from parameter which will be passed to haystack as a range= parameter.

To run the script, use::

 $ python manage.py runscript get_haystack_data --script-args haystack_server_url [none|range_from]

haystack_server_url is the URL of the haystack server
The second parameter is used to set from range for hisRead 'range=from' parameter if point has no data in database.
If the data point already has data in database, the latest row timestamp will be used as range 'from'.  The second paramter will be ignored.
Otherwise, if the data point has no data in the database, second parameter can be
* empty: the script will use 'today' as 'from';  
* 'none': the script will pass no range parameter, and whatever the server returns is what it will store;
* any date in the format of 2019-05-01 could be used.

For example, you can test it with Brian Frank's Java haystack server (See https://bitbucket.org/brianfrank/haystack-java/src/default/)
by running the script like this::

 $ python manage.py runscript get_haystack_data --script-args http://localhost:8080/haystack-java-3.0.2-SNAPSHOT
 $ python manage.py runscript get_haystack_data --script-args http://localhost:8080/haystack-java-3.0.2-SNAPSHOT none
 $ python manage.py runscript get_haystack_data --script-args http://localhost:8080/haystack-java-3.0.2-SNAPSHOT 2019-05-01

Haystack Tag Templates and Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We have implemented some default Project Haystack tag templates as Models, so that you can attach standard combinations of tags to your data points with them.
The Haystack tag templates are from the commonly used points, for example those listed under "Points" on https://project-haystack.org/tag/ahu
They are in the file ``data/entity/demo/models_demo_entities.json``.  You can follow this format to add additional Models.

Services
--------

Think of a service as a wrapper around a program that performs a specific function, so that it's easier for others to discover and use it.

In opentaps SEAS, services wrap around applications so that they could all be run with the data collected by VOLTTRON from BACNet or MODBUS or from another Haystack server
with our Haystack client.  Services use Haystack tags to identify the data they need, so they do not need to be configured to specific data points or topics.  This allows
an application to be configured once and then run on data points for any site or equipment, no matter how they are originally named or set up.

EconomizerRCx Application
^^^^^^^^^^^^^^^^^^^^^^^^^

The EconomizerRCx application is developed by PNNL and described in "Automatic Identification of Retro-Commissioning Measures", PNNL-27338.  It runs as an Economizer agent in VOLTTRON, listening on
the message bus for data, performing analysis, and then writing its results back into the database.  By default, the data points that it listens to for input data are coded in
a config file (``pnnl/EconomizerRCxAgent/config``).  

By running it as a service through opentaps SEAS, you can configure its input with Haystack tags, and opentaps SEAS will
find the data points with those tags and set them up as the input.  opentaps SEAS will also automatically set up the output from EconomizerRCx as data points and associate them
with the equipment it's run.  Finally, opentaps SEAS allows you to configure and run EconomizerRCx on multiple equipment's data points at the same time. 

Configuring the EconomizerRCx as a Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is done in the ``opentaps_seas/servicedef/services.json`` file, which we will go through here:

The services.json file can define many services, and ``economizer_setup`` is the first one::
 
 {
    "economizer_setup": {

This defines what we will do with the service.  In this case, we will be configuring a VOLTTRON application::

        "engine": "opentaps_seas.volttron.forms.VolttronAppConfigService",

Now we define the inputs of the service::

        "input": {

Platform can be the name of the VOLTTRON platform instance.  It can be left empty by default::

            "platform": {
                "type": "string",
                "default": ""
            },

This identifies the agent in VOLTTRON and should match the "tag" of the agent when you do a ``vctl status``:: 

            "agent": {
                "type": "string",
                "default": "economizer"
            },

This is the equipment you are running it for.  As type ``equipment``, it is special: You can run it for one equipment with its id ``'{"equipment":"@Econ-Demo-A-RTU1"}'``,
multiple equipment using tags such as ``'{"equipment":"siteRef:@Econ-Demo-Site-A"}'`` or ``'{"equipment":"tags:rooftop"}'``, or all equipment with ``'{"equipment":"all"}'``::

            "equipment": {
                "type": "equipment"
            },

These define the input data points for the application.  In the file ``pnnl/EconomizerRCxAgent/config`` is a configuration which maps the application's inputs to data points
with names ``MixedAirTemperature``, ``ReturnAirTemperature``, etc.  

By specifying that the default input for ``MixedAirTemperature`` is ``tags:mixed, air, temp``, we are saying
that by default, we will find a data point from the equipment which have all these tags.  This also allows you to override the default tags combination by different tags or a
specific data point, for example ``{"equipment":"siteRef:@Another-Device", "MixedAirTemperature":"@This-Data-Point"}' `` will use ``@This-Data-Point`` as the ``MixedAirTemperature``
input and the other defaults as they are defined here:: 

            "MixedAirTemperature": {
                "type": "datapoint",
                "default": "tags:mixed, air, temp"
            },
            "ReturnAirTemperature": {
                "type": "datapoint",
                "default": "tags:return, air, temp"
            },
            "OutdoorAirTemperature": {
                "type": "datapoint",
                "default": "tags:outside, air, temp"
            },
            "OutdoorDamperSignal": {
                "type": "datapoint",
                "default": "tags:outside, air, damper"
            },
            "SupplyFanStatus": {
                "type": "datapoint",
                "default": "tags:fan, run"
            },
            "SupplyFanSpeed": {
                "type": "datapoint",
                "default": "tags:fan, speed"
            },
            "CoolingValvePosition": {
                "type": "datapoint",
                "default": "tags:cool"
            }
        },

Now we define the outputs::

        "output": {

What we're trying to do is to store the EconomizerRCx's output as data points and associate them with the equipment for which it was run.  
The EconomizerRCx will create and store many data points in Crate with the topics like ``record/Economizer_RCx/econ_demo/building_a/rtu1/Economizing When Unit Should Not Dx/diagnostic message``.  For each one,
we create a separate data point, defined in as the key ``"Economizing When Unit Should Not Dx Message":`` and matched to the topic field in the Crate database.
Then we apply the specified tags to the data point in our database once it's created::

            "Economizing When Unit Should Not Dx Message": {
                "type": "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Economizing When Unit Should Not Dx/diagnostic message",
                "tags": "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, diagnosticMessage"
            },
            "Not Economizing When Unit Should Dx Message": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Not Economizing When Unit Should Dx/diagnostic message",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, diagnosticMessage"
            },
            "Temperature Sensor Dx Message": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Temperature Sensor Dx/diagnostic message",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, diagnosticMessage"
            },
            "Insufficient Outdoor-air Intake Dx Message": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Insufficient Outdoor-air Intake Dx/diagnostic message",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, diagnosticMessage"
            },
            "Excess Outdoor-air Intake Dx Message": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Excess Outdoor-air Intake Dx/diagnostic message",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, diagnosticMessage"
            },

            "Economizing When Unit Should Not Dx Energy Impact": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Economizing When Unit Should Not Dx/energy impact",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, energyImpact"
            },
            "Not Economizing When Unit Should Dx Energy Impact": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Not Economizing When Unit Should Dx/energy impact",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, energyImpact"
            },
            "Temperature Sensor Dx Energy Impact": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Temperature Sensor Dx/energy impact",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, energyImpact"
            },
            "Insufficient Outdoor-air Intake Dx Energy Impact": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Insufficient Outdoor-air Intake Dx/energy impact",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, energyImpact"
            },
            "Excess Outdoor-air Intake Dx Energy Impact": {
                "type" : "datapoint",
                "topic": "record/Economizer_RCx/{base}/{equipment.kv_tags[id]}/Excess Outdoor-air Intake Dx/energy impact",
                "tags" : "appName: Economizer_Rcx, siteRef: {equipment.kv_tags[siteRef]}, equipRef: {equipment.kv_tags[id]}, energyImpact"
            }
        }
    }
 } 


Running the EconomizerRCx as a Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run the EconomizerRcx, install VOLTTRON and VOLTTRON-applications. (Note: we have made some fixes to this application, which have been contributed back to VOLTTRON.  
In the meantime, use the master/ branch from https://github.com/opentaps/volttron-applications)

Start VOLTTRON and make sure that VOLTTRON central, VOLTTRON central platform, master driver, and Crate historian agents are running.  
Then, install the EconomizerRCX agent::

 $ python scripts/install-agent.py -s pnnl/EconomizerRCxAgent/ -i economizer -t economizer -c pnnl/EconomizerRCxAgent/config

The setup for the EconomizerRCx has already been defined in the ``servicedef/services.json`` file.  
To deploy the service, use the ``run_service`` script.  The first argument is the service name, and the second argument is the parameter for the service::

 $ python manage.py runscript run_service --script-args economizer_setup '{"equipment":"@Econ-Demo-A-RTU1"}' 

What this does is configure the VOLTTRON application to run your service based on Haystack tags and your data.  If this works, you should see a message like this::

 Service Results:
 { 'errors': 0,
   'result': { 'agent': { 'error_code': None,
                          'health': {'context': None, 'last_updated': None, 'status': 'UNKNOWN'},
                          'identity': 'economizer',
                          'is_running': False,
                          'name': 'economizeragent-1.0.8',
                          'permissions': {'can_remove': True, 'can_restart': True, 'can_start': True, 'can_stop': True},
                          'platform': 'Vm9sdHRyb25fSW5zdGFuY2UucGxhdGZvcm0uYWdlbnQ=',
                          'platform_uuid': 'Vm9sdHRyb25fSW5zdGFuY2UucGxhdGZvcm0uYWdlbnQ=',
                          'priority': None,
                          'process_id': None,
                          'tag': 'economizer',
                          'uuid': 'bf4eac19-07c4-4ffc-afb4-03776c631539',
                          'version': '1.0.8'},
               'devices': [{'base': 'econ_demo/building_a', 'equipment': <Entity: @Econ-Demo-A-RTU1>, 'mapping': {}, 'name': 'devices/econ_demo/building_a/rtu1#@Econ-Demo-A-RTU1'}],
               'errors': [],
               'platform': 'Vm9sdHRyb25fSW5zdGFuY2UucGxhdGZvcm0uYWdlbnQ='},
   'success': 1}

If there are errors, for example tags that are not found, you should see them here.

You can also run your EconomizerRCx agent for all machines that fit Haystack tags::

 $ python manage.py runscript run_service --script-args economizer_setup '{"equipment":"siteRef:@Econ-Demo-Site-A"}' 
 $ python manage.py runscript run_service --script-args economizer_setup '{"equipment":"tags:rooftop"}' 

Or just run it for all your machines::

 $ python manage.py runscript run_service --script-args economizer_setup '{"equipment":"all"}' 

From VOLTTRON, you can verify that your service has been configured by checking to see if there are entries in the config store for the application's agent::

 $ vctl config list economizer
 devices/econ_demo/building_a/rtu1#@Econ-Demo-A-RTU1

If there are multiple machines that your EconomizerRCx has been configured to run for, a separate configuration would show for each one.  To see the configuration for a 
particular machine::

 $ vctl config get economizer  devices/econ_demo/building_a/rtu1#@Econ-Demo-A-RTU1

The configurations you get here will match what you see for the economizer agent in the VOLTTRON tab of opentaps SEAS user interface.

Once everything is set up, you can start the VOLTTRON application agent, either from the VOLTTRON tab of opentaps SEAS, or from VOLTTRON.  The output data will be stored
as topics in Crate.  opentaps SEAS will automatically create data points for all your configured output as data points associated with the equipment.
