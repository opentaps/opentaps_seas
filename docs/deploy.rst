Deploy
========

Prerequisites
-------------

* installation of requirements/production.txt in the opentaps_seas virtualenv
* apache mod_wsgi
* redis-server (for Django caching get at https://redis.io/)
* a SSL enabled VirtualHost in apache


Production PIP requirements
---------------------------

Install the production requirements in your opentaps_seas virtualenv::
    pip install -r requirements/production.txt


Mod WSGI
--------

The version of mod_wsgi must match your python version and be >=3.7
So if your server distribution does not provide them they can be both built from source.

Get Python from https://www.python.org/downloads/ and install it with::
    tar xzf Python-3.7.x.tgz
    cd /opt/Python-3.7.x/
    ./configure --prefix=/usr/local --enable-shared --with-threads --enable-optimizations
    make altinstall

Make sure python is working by calling::
    /usr/locan/bin/python3.7 -v

If you have an issue with libraries not found make sure to add this to cat /etc/ld.so.conf ::
    /usr/local/lib
    /usr/local/lib64
    ldconfig

Get mod_wsgi from https://pypi.org/project/mod-wsgi/#files ::
    tar xzf mod_wsgi-4.6.x.tar.gz
    cd mod_wsgi-4.6.4.tar.gz
    ./configure --with-python=/usr/local/bin/python3.7
    LD_RUN_PATH=/usr/local/lib make
    make install


Redis Server
------------

Get the latest Redis from your disctribution or straight from their website https://redis.io/ to build it manually ::
    wget http://download.redis.io/releases/redis-5.0.5.tar.gz
    tar xzf redis-5.0.5.tar.gz
    cd redis-5.0.5
    make
    make install
    cd utils
    ./install_server.sh


Example of Apache configuration
-------------------------------

Note, this is a basic template, change to match your server IP and server name and use the SSL configuration
and paths to match your particular setup; and check the unix user running the wsgi process to match your
server config from 'user=opentaps_seas group=opentaps_seas' ::

    <VirtualHost 1.2.3.4:443>
        ServerName opentaps_seas.example.com
        DocumentRoot /path/to/opentaps_seas

        SSLEngine on
        SSLCACertificateFile ...
        SSLCertificateFile ...
        SSLCertificateKeyFile ...

        Alias /static/admin/ /path/to/opentaps_seas/venv/lib/python3.7/site-packages/django/contrib/admin/static/admin/
        Alias /static/ /path/to/opentaps_seas/opentaps_seas/static/
        Alias /media/ /path/to/opentaps_seas/opentaps_seas/static/

        <Directory /path/to/opentaps_seas/opentaps_seas/static/ >
          Require all granted
        </Directory>
        <Directory /path/to/opentaps_seas/venv/lib/python3.7/site-packages/django/contrib/admin/static/admin/ >
          Require all granted
        </Directory>

        WSGIProcessGroup opentaps_seas.example.com
        WSGIApplicationGroup opentaps_seas
        WSGIDaemonProcess opentaps_seas.example.com user=opentaps_seas group=opentaps_seas python-home=/path/to/opentaps_seas/venv python-path=/path/to/opentaps_seas
        WSGIScriptAlias / /path/to/opentaps_seas/config/wsgi.py process-group=opentaps_seas.example.com application-group=opentaps_seas

        <Directory /path/to/opentaps_seas/config/ >
          <Files wsgi.py>
            Require all granted
          </Files>
        </Directory>

        ErrorLog /var/log/httpd/opentaps_seas/error_log
        CustomLog /var/log/httpd/opentaps_seas/access_log combined
    </VirtualHost>


Secrets.json and Configuration
------------------------------

Additonal settings needed in the 'secrets.json' file:

DJANGO_SECRET_KEY you can generate a random value from opentasp_seas virtualenv with::
    python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'

REDIS_URL this should match your REDIS server so for example the default should be::
    redis://127.0.0.1:6379/

In opentaps_seas/config/settings/production.py do the following changes:
 * change ALLOWED_HOSTS from 'demoseas.opentaps.org' to match your server name
 * change DEFAULT_FROM_EMAIL and EMAIL_SUBJECT_PREFIX to match your preferences
 * change the logging file if needed from /var/log/opentaps_seas/info.log

Note: make sure the logging file path exists and is writable by the wsgi process user from the apache configuration.


Disabling the Application
-------------------------

A quick way to disable and re-enable the application without changing the Apache configuration or restarting it is to
switch off the wsgi.py, for example::
    mv /path/to/opentaps_seas/config/wsgi.py /path/to/opentaps_seas/config/wsgi.py.old




