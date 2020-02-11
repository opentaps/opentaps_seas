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

from datetime import timedelta
from django.db import connections
from opentaps_seas.eemeter import utils as eemeter_utils
from opentaps_seas.core import utils as core_utils
from opentaps_seas.core.models import FinancialTransaction
from opentaps_seas.party.models import Party


def clean():
    print('Deleting data ...')
    with connections['default'].cursor() as c:
        c.execute("""DELETE FROM core_weather_history WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_weather_history WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_meter_history WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_meter_production WHERE source = 'eemeter_sample';""")
        c.execute("""DELETE FROM core_site_weather_stations WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_meter_financial_value WHERE meter_id IN
                     (SELECT meter_id FROM core_meter WHERE weather_station_id = 'eemeter_ws');""")
        c.execute("""DELETE FROM core_meter_production WHERE meter_id IN
                     (SELECT meter_id FROM core_meter WHERE weather_station_id = 'eemeter_ws');""")
        c.execute("""DELETE FROM eemeter_baselinemodel WHERE meter_id IN
                     (SELECT meter_id FROM core_meter WHERE weather_station_id = 'eemeter_ws');""")
        c.execute("""DELETE FROM core_meter WHERE weather_station_id = 'eemeter_ws';""")
        c.execute("""DELETE FROM core_weather_station WHERE weather_station_id = 'eemeter_ws';""")
        c.close()


def demo():
    import_data('demo')


def seed():
    import_data('seed')


def import_data(which):
    print('Importing {} data...'.format(which))
    is_demo = which == 'demo'

    if is_demo:
        # setup a sample meter and calcualte the savings
        site, meter, model = eemeter_utils.setup_demo_sample_models('demo-site-1', calc_savings=True)
        # setup a demo rate plan and calculate the financial values
        rp = core_utils.setup_sample_rate_plan(meter, price=0.2)
        results = core_utils.calc_meter_financial_values(meter.meter_id, rp.rate_plan_id)
        # ensure we have parties
        p1 = Party.objects.filter(party_external_id='party1').first()
        if not p1:
            p1 = Party.objects.create(party_external_id='party1', source='example')
        p2 = Party.objects.filter(party_external_id='party2').first()
        if not p2:
            p2 = Party.objects.create(party_external_id='party2', source='example')
        for result in results:
            # create financial transaction which from Party1 to Party2 the meter financial
            # value 21 days after the ending of the billing cycle if the meter financial
            # value is positive, or Party2 pay to Party1 if it negative.
            amount = result.amount
            if not amount:
                continue
            amount = round(amount, 2)
            if not amount:
                continue
            from_party = p1
            to_party = p2
            if amount < 0:
                from_party = p2
                to_party = p1
                amount = -amount
            FinancialTransaction.objects.create(
                from_party=from_party,
                to_party=to_party,
                transaction_datetime=result.thru_datetime + timedelta(days=21),
                amount=amount,
                uom=result.uom,
                meter=meter,
                source=result.source,
                transaction_type='Meter Financial Value',
                status_id='transaction_created',
                from_datetime=result.from_datetime,
                thru_datetime=result.thru_datetime
                )


def print_help():
    print("Usage: python manage.py runscript setup_sample_meter --script-args [all|seed|demo] [clean]")
    print("  note: table managed by DJANGO, make sure the migrations are run so the table exists")
    print("  all|seed|demo: which data to import")
    print("  clean: optional, delete data first")


def run(*args):
    if len(args) > 0:
        if 'clean' in args:
            clean()
        if 'all' in args or 'clean' in args or 'seed' in args:
            seed()
        if 'all' in args or 'demo' in args:
            demo()
    else:
        print_help()
