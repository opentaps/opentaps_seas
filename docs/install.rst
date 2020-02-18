Installation Instructions
=========================

Getting Started
^^^^^^^^^^^^^^^

You will need the following::

 * Linux
 * python3
 * pip
 * virtualenv

Then create the virtualenv::

    $ virtualenv venv --python=`which python3`
    $ source venv/bin/activate
    $ pip install -r requirements/local.txt

Databases
^^^^^^^^^

We use two databases: a relational database to store application data and, optionally, a time series database to store IOT data trended by VOLTTRON (see below.) 
The relational database we use is PostgreSQL, and the time series database is Crate.  The names of the databases and their connections setup are configured in ``config/settings/base.py``: 

 DATABASES = {
     'default': env.db('DATABASE_URL', default='postgres:///opentaps_seas'),
     'crate': env.db('CRATE_DATABASE_URL', default='postgres://crate@127.0.0.1:5433/volttron'),
 }  

Postgres
^^^^^^^^

Note: You may need to switch to postgres user to run those commands (eg: sudo su - postgres)

You will need to set up your PostgreSQL database properly so that you can use your <unixuser> as the user that would run the server so it authenticates in postgres using ident. 
Postgres Extensions must be installed, which means in some distributions installing the `postgresql-contrib` package.  The HSTORE extension must be setup which requires running this in postgres as the superuser::

    $ psql -d template1 -c 'create extension hstore;'

Then create your databases::

    $ createuser <unixuser>
    $ createdb -O <unixuser> opentaps_seas
    $ createdb -O <unixuser> test_opentaps_seas

If you find you're still missing the HSTORE extension, it must be setup for each database, again as the postgres superuser::

    $ psql opentaps_seas -U postgres
    opentaps_seas=# CREATE EXTENSION IF NOT EXISTS hstore
    $ psql test_opentaps_seas -U postgres
    test_opentaps_seas=# CREATE EXTENSION IF NOT EXISTS hstore

Then initialize your database by running the migrations::

    $ python manage.py migrate


Redis
^^^^^

You will need to install Redis for use with Celery. Simply install and make sure Redis is running.
https://redis.io/download 

If you want to use a different broker (like RabbitMQ, see http://docs.celeryproject.org/en/latest/getting-started/brokers/) or use a different redis port make sure
to adapt the configuration in ``settings/base.py``::

    # Celery settings
    CELERY_BROKER_URL = 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'

Celery
^^^^^^

Celery is installed as part of the requirements in the virtual-env, but you will need to run the worker thread.

For development and testing, you can run it manually::
    
    /home/myuser/opentaps_seas/venv/bin/celery -A opentaps_seas.core worker -l info

For production, you can use supervisor to manage it as a service and ensure it will be running in the background. See http://supervisord.org/  Here is a sample of the config::

    [program:opentaps_seas_celery]
    command=/home/myuser/opentaps_seas/venv/bin/celery -A opentaps_seas.core  worker -l info
    directory=/home/myuser/opentaps_seas
    numprocs=1
    stdout_logfile=/home/myuser/opentaps_seas/celery-worker-stdout.log
    stderr_logfile=/home/myuser/opentaps_seas/celery-worker.log
    autostart=true
    autorestart=true
    startsecs=10
    user=myuser

Important: remember that if the opentaps_seas code is updated the celery worker must be restarted as well or it will keep running the old version.

VOLTTRON
^^^^^^^^

VOLTTRON can be used to get data from buildings and energy systems with standard protocols such as BACNet and MODBUS, then store them in a time series database
such as Crate.  There are also many applications developed for VOLTTRON under a separate VOLTTRON-applications repository. 

We have made some enhancements to VOLTTRON for opentaps SEAS, which have been contributed back to the VOLTTRON project.  Meanwhile you can get our enhanced versions from
github at https://github.com/opentaps/VOLTTRON (use the develop branch) and https://github.com/opentaps/VOLTTRON-applications (use the master branch.) 

Please follow https://volttron.readthedocs.io/en/develop/setup/index.html to install VOLTTRON.  You may want to have one or more VOLTTRON instances collecting data from devices
and forwarding them to a master instance.  opentaps SEAS should then connect to the master instance and the database it is using to store the data.  
After installing and starting VOLTTRON, you will need to install the following agents::

 $ python scripts/install-agent.py -s services/core/VOLTTRONCentral -c services/core/VOLTTRONCentral/config -t vc
 $ python scripts/install-agent.py -s services/core/VOLTTRONCentralPlatform -t vcp
 $ python scripts/install-agent.py -s services/core/CrateHistorian -c services/core/CrateHistorian/config -i crate-historian -t crate
 $ python scripts/install-agent.py -s services/core/MasterDriverAgent/ -t master

The VOLTTRON Central and VOLTTRON Central Platform agents need to be configured and running to connect with opentaps SEAS.  Configure them by editing ``~/.VOLTTRON/config``, or
create a new one if you do not have one, and put in the following::

 [VOLTTRON]
 vip-address = tcp://127.0.0.1:22916
 instance-name = "VOLTTRON_Instance"
 bind-web-address = http://your.external.ip.address:8080
 VOLTTRON-central-address = http://your.external.ip.address:8080
  
Now edit your ``secrets.json`` file and put in the username, password, and ip address of your VOLTTRON Central instance.

Verify the following: 
 * Your VOLTTRON instance is there with at http://VOLTTRON.central.ip.address:8080/vc/jsonrpc  You should see a response
 * Go to the VOLTTRON tab of opentaps SEAS web interface.  It should show you the agents that are running in VOLTTRON.  You should see a VOLTTRON central agent and a VOLTTRON central platform agent running.


Crate
^^^^^

Crate is a time series database which is specialized in storing time series databases from machines, such as BACNet and MODBUS data from VOLTTRON.  If you wish to use VOLTTRON to get this data for your sites and work with them in opentaps, then please follow these instructions to set up Crate.

As of Crate 4.0, the open source edition of Crate must be installed following directions in https://crate.io/docs/crate/reference/en/latest/editions.html#community-edition

You will also need `crash`, the CrateDB shell,  See directions from https://crate.io/docs/clients/crash/en/latest/index.html

Note that the CrateDB postgres connection is by default done on port 5433 instead of 5432 to avoid conflict. This should be at the end of the ``crate/config/crate.yml``::

    psql.enabled: true
    psql.port: 5433

You should then initialize your Crate database with::

 $ cat cratedb/init_schema.sql | crash

This creates a couple of other tables in addition to the ones created by VOLTTRON CrateDBHistorian, ``volttron.data`` and ``volttron.topic``, which we use as well.

Load seed data
^^^^^^^^^^^^^^

opentaps SEAS comes with two sets of data: seed and demo.  Seed data is needed to run the application.  Demo data can be used to show how the application
works.  

Before loading your data, you must initialize your database::

 $ python manage.py migrate

To init the data::

 $ ./import_data.sh all_data all

To init just the seed data::

 $ ./import_data.sh all_data seed

To init just the demo data::

 $ ./import_data.sh all_data demo

To reset the data and **delete all previous data** add **clean**::

 $ ./import_data.sh all_data all clean

To reset the data and **delete all previous data** add **clean** and run demo rules::

 $ ./import_data.sh all_data all clean run_rules

These are equivalent::

 $ ./import_data.sh all_data clean
 $ ./import_data.sh all_data seed clean

Notes about the seed data:
 * Time zones are linked to country in the ``data/timezone/seed/timezone.csv`` file.  They are currently pre-defined for USA and Canada.
 * Haystack tags are defined in the file ``data/seed/tags.csv`` file.  They currently implement the Project Haystack 3.0 spec.

There is also a set of time series demo data based on "Long-term data on 3 office Air Handling Units" from https://openei.org/datasets/dataset/long-term-data-on-3-office-air-handling-units  This data can be loaded into your time series database (currently Crate) with::

 $ ./import_data.sh all_data tsdemo

You can also delete this demo data from your time series database::

 $ ./import_data.sh clean tsdemo

This time series demo data can also be loaded as part of loading all demo data:

 $ ./import_data.sh all_data all clean

and deleted with the other data as well:
 
 $ ./import_data.sh all_data all clean tsdemo


Syncing PostgreSQL and Crate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, entity data such as sites, equipment, data points, and their tags are stored in PostgreSQL.  We do this because PostgreSQL is transactional.
To make querying your data easier, you can also sync your sites, equipment, and points (topics) data to Crate DB's ``volttron.topic`` table by configuring 
your ``secrets.json`` and setting ``CRATE_TAG_AUTOSYNC`` to ``true``.  For site or equipment, the key in ``volttron.topic.topic`` will be the value of the
``id`` key-value tag (``kv_tags``.)  

You can also run a script to sync all existing data to Crate::

    $ python manage.py runscript sync_tags_to_crate


Basic Commands
--------------

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

If you load the demo data, an admin user with username ``admin`` and pasword ``opentaps`` will be created for you.

* To create a **user account** from the command line you can use the following script which will skip the need for email verification. Note: the admin flag sets a superuser::

    $ utility/create_user <username> <password> <email> [admin]

* The following script for convenience removes a user and his email address::

    $ utility/delete_user <username>

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ mypy django_opentaps_seas

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ coverage erase
    $ coverage run manage.py test --settings=config.settings.test -v 2 opentaps_seas/tests/ --with-html
    $ coverage html
    $ open htmlcov/index.html
    $ open nosetests.html

It also could be run with -k (keep test database) option. In that case test database will not be recreated.

Setting Up Amazon S3
^^^^^^^^^^^^^^^^^^^^

Amazon S3 is used to store files and content in the cloud. You need to set up Amazon S3 to store your files.  Get these Amazon S3 access credentials and set them in your secrets.json file::

 AWS_ACCESS_KEY_ID
 AWS_SECRET_ACCESS_KEY
 AWS_STORAGE_BUCKET_NAME

Setting Up Grafana
^^^^^^^^^^^^^^^^^^^^

Grafana is used to create dashboards.  It must be set up with Crate DB as a PostgreSQL datasource with these characteristics::

 name CrateDB
 port localhost:5433
 database VOLTTRON
 username crate
 no password

To embed Grafana dashboards in opentaps SEAS, add ``allow_embedding = true`` into the ``grafana.ini`` under Security section.  (In Ubuntu, ``grafana.ini`` is in the ``/etc/grafana/`` directory.)

We will automatically create Grafana dashboards for your data points.  You need to set up Grafana and then put the access credentials in your secrets.json::

 GRAFANA_USER_NAME
 GRAFANA_USER_PASSWORD
 GRAFANA_BASE_URL

The last one is the URL of your Grafana server.

To create dashboards for all existing data points, run the script::

 $ python manage.py runscript create_dashboards

The dashboards are based on the template JSON file in ``data/dashboard/point-dashboard.json``. 

There is also a template for summary dashboards for AHU's in ``data/dashboard/ahu-dashboard.json`` (see the user docs for more information about this dashboard.)

To delete the dashboards, use the script ``scripts/remove_dashboards.py``::

 $ python manage.py runscript remove_dashboards all

This will delete all the dashboards we have created for you, based on the dashboard_uid of your data points and entities stored in PostgreSQL.

Testing It
^^^^^^^^^^

By default the webapp is only available at localhost:8000.  To make it available at an IP address,
Edit ``config/settings/local.py`` and set::

 ALLOWED_HOSTS = [
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
    "my.ip.address.here",
 ]

Then::

 $ python manage.py runserver my.ip.address.here:8000

If this runs, then go to ``http://my.ip.address.here:8000``.  You should see the splash screen.
