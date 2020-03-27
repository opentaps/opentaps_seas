from datetime import datetime
from calendar import monthrange
import logging
import requests
import PySAM.Utilityrate5 as utility
from django.conf import settings
from ..core.models import MeterHistory
from ..core.models import MeterRatePlanHistory

logger = logging.getLogger(__name__)

URL_OPENEI = 'https://api.openei.org/utility_rates'
FORMAT = 'json'
VERSION = '7'
DIRECTION_SORT = 'asc'
DETAIL = 'full'
LIMIT = '500'
ORDER_BY_SORT = 'startdate'


def URDBv7_to_ElectricityRates(urdb_response):
    """
    Formats response from Utility Rate Database API version 7 for use in PySAM
        i.e.
            model = PySAM.UtilityRate5.new()
            rates = PySAM.ResourceTools.URDBv7_to_ElectricityRates(urdb_response)
            model.ElectricityRates.assign(rates)
    :param: urdb_response
        dictionary with response fields following https://openei.org/services/doc/rest/util_rates/?version=7
    :return: dictionary for PySAM.UtilityRate5.UtilityRate5.ElectricityRates
    """

    def try_get_schedule(urdb_name, data_name):
        if urdb_name in urdb_response.keys():
            data[data_name] = urdb_response[urdb_name]
            for i in range(12):
                for j in range(24):
                    data[data_name][i][j] += 1

    def try_get_rate_structure(urdb_name, data_name):
        mat = []
        if urdb_name in urdb_response.keys():
            structure = urdb_response[urdb_name]
            for i, period in enumerate(structure):
                for j, entry in enumerate(period):
                    rate = entry['rate']
                    if 'adj' in entry.keys():
                        rate += entry['adj']
                    tier_max = 1e38
                    if 'max' in entry.keys():
                        tier_max = entry['max']
                    sell = 0
                    if 'sell' in entry.keys():
                        sell = entry['sell']
                    units = ['kwh', 'kw']
                    if 'unit' in entry.keys():
                        if entry['unit'].lower() not in units:
                            raise Exception("UtilityRateDatabase error: unrecognized unit in rate structure")
                    mat.append([i + 1, j + 1, tier_max, 0.0, rate, sell])
            data[data_name] = mat

    def try_get_rate_structure4(urdb_name, data_name):
        mat = []
        if urdb_name in urdb_response.keys():
            structure = urdb_response[urdb_name]
            for i, period in enumerate(structure):
                for j, entry in enumerate(period):
                    rate = entry['rate']
                    if 'adj' in entry.keys():
                        rate += entry['adj']
                    tier_max = 1e38
                    if 'max' in entry.keys():
                        tier_max = entry['max']

                    mat.append([i + 1, j + 1, tier_max, rate])
            data[data_name] = mat

    data = dict()
    data['en_electricity_rates'] = 1
    data['ur_metering_option'] = 0

    if 'dgrules' in urdb_response.keys():
        rules = urdb_response['dgrules']
        if rules == "Net Metering":
            data['ur_metering_option'] = 0
        elif rules == "Net Billing Instantaneous":
            data['ur_metering_option'] = 2
        elif rules == "Net Billing Hourly":
            data['ur_metering_option'] = 3
        elif rules == "Buy All Sell All":
            data['ur_metering_option'] = 4

    if 'fixedchargefirstmeter' in urdb_response.keys():
        fixed_charge = urdb_response['fixedchargefirstmeter']
        fixed_charge_units = urdb_response['fixedchargeunits']
        if fixed_charge_units == "$/day":
            fixed_charge *= 365/30
        elif fixed_charge_units == "$/year":
            fixed_charge /= 12
        data['ur_monthly_fixed_charge'] = fixed_charge

    if 'mincharge' in urdb_response.keys():
        min_charge = urdb_response['mincharge']
        min_charge_units = urdb_response['minchargeunits']
        if min_charge_units == "$/year":
            data['ur_annual_min_charge'] = min_charge
        else:
            if min_charge_units == "$/day":
                min_charge *= 365 / 30
            data['ur_monthly_min_charge'] = min_charge

    try_get_schedule('energyweekdayschedule', 'ur_ec_sched_weekday')
    try_get_schedule('energyweekendschedule', 'ur_ec_sched_weekend')

    if 'flatdemandmonths' in urdb_response.keys():
        data['ur_dc_enable'] = 1
        flat_mat = []
        flat_demand = urdb_response['flatdemandmonths']
        for i in range(12):
            flat_mat.append([i, 1, 1e38, flat_demand[i]])
        data['ur_dc_flat_mat'] = flat_mat

    try_get_rate_structure('energyratestructure', 'ur_ec_tou_mat')
    try_get_rate_structure4('flatdemandstructure', 'ur_dc_flat_mat')
    try_get_rate_structure4('demandratestructure', 'ur_dc_tou_mat')
    try_get_schedule('demandweekdayschedule', 'ur_dc_sched_weekday')
    try_get_schedule('demandweekendschedule', 'ur_dc_sched_weekend')

    return data


def get_openei_util_rate_name(rate_item):
    enddate = None
    if 'enddate' in rate_item.keys():
        enddate = rate_item['enddate']
    startdate = datetime.fromtimestamp(rate_item['startdate']).strftime('%Y-%m-%d')

    if not enddate:
        enddate = ""
    else:
        enddate = datetime.fromtimestamp(enddate).strftime('%Y-%m-%d')

    name = '{} - {}, {} : {}'.format(rate_item['utility'], rate_item['name'], startdate, enddate)

    return name


def get_openei_util_rates(effective_on_date=None, country=None, address=None, page_label=None):
    req_param = {}

    # Request param
    if settings.OPENEI_API_KEY:
        req_param['api_key'] = settings.OPENEI_API_KEY
    else:
        raise NameError('Missing openei API configuration')

    req_param['eia'] = '0'
    req_param['sector'] = 'Commercial'

    req_param['format'] = FORMAT
    req_param['version'] = VERSION

    req_param['direction'] = DIRECTION_SORT
    req_param['detail'] = DETAIL
    req_param['limit'] = LIMIT
    req_param['orderby'] = ORDER_BY_SORT

    if country:
        req_param['country'] = country

    if address:
        req_param['address'] = address

    if effective_on_date:
        req_param['effective_on_date'] = (effective_on_date - datetime(1970, 1, 1)).total_seconds()

    if page_label:
        req_param['getpage'] = page_label

    r = requests.get(URL_OPENEI, params=req_param)
    data_openei = r.json()

    return data_openei['items']


def get_active_rate_plan_history(meter_id, year, month=None):
    from_datetime, thru_datetime = get_period(year, month)

    if month:
        rate_plan_history = MeterRatePlanHistory.objects.raw('''select rate_plan_history_id, from_datetime,
            thru_datetime, rate_details
            from {0}
            where (from_datetime <= %s and (thru_datetime is null or thru_datetime >= %s))
            and (thru_datetime is null or thru_datetime >= %s)
            and meter_id = %s
            order by from_datetime desc '''.format(MeterRatePlanHistory._meta.db_table),
                                                  [from_datetime, from_datetime, thru_datetime, meter_id])
    else:
        rate_plan_history = MeterRatePlanHistory.objects.raw('''select rate_plan_history_id, from_datetime,
            thru_datetime, rate_details
            from {0}
            where (from_datetime <= %s and (thru_datetime is null or thru_datetime >= %s))
            or (thru_datetime is null or thru_datetime >= %s)
            and meter_id = %s
            order by from_datetime desc '''.format(MeterRatePlanHistory._meta.db_table),
                                                  [from_datetime, from_datetime, thru_datetime, meter_id])

    return rate_plan_history


def get_period(year, month=None):
    if not month:
        from_datetime = datetime(year, 1, 1, 0, 0, 1)
        thru_datetime = datetime(year, 12, 31, 23, 59, 59)
    else:
        last_day = monthrange(year, month)[1]
        from_datetime = datetime(year, month, 1, 0, 0, 1)
        thru_datetime = datetime(year, month, last_day, 23, 59, 59)

    return from_datetime, thru_datetime


def run_calculation(meter_id, year, month=None):
    hours = [0, 744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016]
    pysam_array_length = 8760

    from_datetime, thru_datetime = get_period(year, month)

    meter_history = MeterHistory.objects.filter(meter_id=meter_id, as_of_datetime__gte=from_datetime,
                                                as_of_datetime__lte=thru_datetime).order_by('as_of_datetime')

    load_data = [0 for i in range(pysam_array_length)]
    counter = 0
    if month:
        counter = hours[month-1]
    for row in meter_history:
        load_data[counter] = row.value
        counter += 1

    rate_plan_history = get_active_rate_plan_history(meter_id, year, month)
    if not rate_plan_history:
        raise Exception("Cannot find MeterRatePlanHistory for meter {}".format(meter_id))

    rate_plan = rate_plan_history[0].rate_details

    model = utility.new()
    rates = URDBv7_to_ElectricityRates(rate_plan)
    model.ElectricityRates.assign(rates)

    lifetime_data = dict()
    lifetime_data['analysis_period'] = 1
    lifetime_data['system_use_lifetime_output'] = 1
    lifetime_data['inflation_rate'] = 99

    model.Lifetime.assign(lifetime_data)

    model.SystemOutput.degradation = [99]
    gen = [0 for i in range(pysam_array_length)]

    model.SystemOutput.gen = gen
    model.Load.load = load_data

    model.execute()

    if not month:
        return model.Outputs.year1_monthly_utility_bill_w_sys
    else:
        return (model.Outputs.year1_monthly_utility_bill_w_sys[month-1],)
