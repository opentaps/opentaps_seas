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
import eemeter
from io import StringIO
from eemeter import io as eeio
from ..core.models import SiteView
from ..core.models import SiteWeatherStations
from ..core.models import Meter
from ..core.models import MeterHistory
from ..core.models import WeatherStation
from ..core.models import WeatherHistory
from .models import BaselineModel

logger = logging.getLogger(__name__)


def setup_demo_sample_models(site_id, meter_id=None, description=None):
    # this create a test sample meter with both hourly and daily model
    # using sample meter and temperature data for the given site id

    # use the hourly sample data
    meter_data, temperature_data, sample_metadata = (
        eemeter.load_sample("il-electricity-cdd-hdd-hourly")
    )

    source = 'eemeter_sample'
    # throw an exception is Site is not found
    try:
        site = SiteView.objects.get(object_id=site_id)
    except SiteView.DoesNotExist:
        site = SiteView.objects.get(entity_id=site_id)

    # create a dummy weather station for the sample data if it did not alredy exist
    try:
        ws = WeatherStation.objects.get(weather_station_id='eemeter_ws')
    except WeatherStation.DoesNotExist:
        ws = WeatherStation.objects.create(
            weather_station_id='eemeter_ws', source=source, elevation_uom_id='length_m')
        # associate it to the site
        SiteWeatherStations.objects.create(
            weather_station=ws,
            site_id=site.entity_id,
            source=source,
            station_name='Sample Station')
        # load the temperature data, this is given in F
        for d, t in temperature_data.iteritems():
            tc = (t - 32.0) * 5 / 9
            WeatherHistory.objects.create(weather_station=ws, as_of_datetime=d, temp_f=t, temp_c=tc, source=source)

    if not meter_id:
        meter_id = '{}-sample_meter'.format(site_id)
    if not description:
        description = 'Sample Meter'

    # cleanup previous entries as needed
    MeterHistory.objects.filter(meter_id=meter_id).delete()
    Meter.objects.filter(meter_id=meter_id).delete()
    # create the meter
    meter = Meter.objects.create(
        meter_id=meter_id,
        site_id=site.entity_id,
        description=description,
        weather_station_id='eemeter_ws')
    # setup the meter data (note this is slightly different format than temps)
    for d, v in meter_data.iterrows():
        MeterHistory.objects.create(meter=meter, as_of_datetime=d, value=v.value, uom_id='energy_kWh', source=source)

    # create both models
    frequency = 'hourly'
    data = read_meter_data(meter, freq=frequency)
    model = get_model_for_freq(data, frequency)
    save_model(model, meter_id=meter.meter_id, frequency=frequency)

    frequency = 'daily'
    data = read_meter_data(meter, freq=frequency)
    model = get_model_for_freq(data, frequency)
    return save_model(model, meter_id=meter.meter_id, frequency=frequency)


def get_daily_sample_data():
    meter_data, temperature_data, sample_metadata = (
        eemeter.load_sample("il-electricity-cdd-hdd-daily")
    )
    return read_sample_data(meter_data, temperature_data, sample_metadata)


def get_hourly_sample_data():
    meter_data, temperature_data, sample_metadata = (
        eemeter.load_sample("il-electricity-cdd-hdd-hourly")
    )
    return read_sample_data(meter_data, temperature_data, sample_metadata)


def read_sample_data(meter_data, temperature_data, sample_metadata):
    # the dates if an analysis "blackout" period during which a project was performed.
    blackout_start_date = sample_metadata["blackout_start_date"]
    blackout_end_date = sample_metadata["blackout_end_date"]

    # get meter data suitable for fitting a baseline model
    baseline_meter_data, warnings = eemeter.get_baseline_data(
        meter_data, end=blackout_start_date, max_days=365
    )

    return {
        'meter_data': meter_data,
        'temperature_data': temperature_data,
        'sample_metadata': sample_metadata,
        'blackout_start_date': blackout_start_date,
        'blackout_end_date': blackout_end_date,
        'baseline_meter_data': baseline_meter_data
    }


def read_meter_data(meter, blackout_start_date=None, blackout_end_date=None, freq=None, start=None, end=None):
    # get the meter data from the meter history
    logger.info('read_meter_data: freq %s', freq)
    out = StringIO()
    meter.write_meter_data_csv(out, columns=[{'as_of_datetime': 'start'}, {'value': 'value'}], start=start, end=end)
    out.seek(0)
    if freq not in ("hourly", "daily"):
        freq = None
    meter_data = eeio.meter_data_from_csv(out, freq=freq)
    logger.info('read_meter_data: meter_data %s', meter_data)

    # get the temperature data from the meter linked weather stations
    out = StringIO()
    meter.write_weather_data_csv(out, columns=[{'as_of_datetime': 'dt'}, {'temp_f': 'tempF'}], start=start, end=end)
    out.seek(0)
    temperature_data = eeio.temperature_data_from_csv(out, freq="hourly")
    logger.info('read_meter_data: temperature_data %s', temperature_data)

    # get meter data suitable for fitting a baseline model
    baseline_meter_data, warnings = eemeter.get_baseline_data(
        meter_data, end=blackout_start_date, max_days=365
    )

    return {
        'meter_data': meter_data,
        'temperature_data': temperature_data,
        'blackout_start_date': blackout_start_date,
        'blackout_end_date': blackout_end_date,
        'baseline_meter_data': baseline_meter_data
    }


def get_model_for_freq(data, freq):
    if freq == 'hourly':
        return get_hourly_model(data)
    elif freq == 'daily':
        return get_daily_model(data)
    else:
        raise Exception("Model frequency must be hourly or daily")


def get_daily_model(data):
    # create a design matrix (the input to the model fitting step)
    baseline_design_matrix = eemeter.create_caltrack_daily_design_matrix(
        data['baseline_meter_data'], data['temperature_data'],
    )

    # build a CalTRACK model
    baseline_model = eemeter.fit_caltrack_usage_per_day_model(
        baseline_design_matrix,
    )

    return baseline_model


def get_hourly_model(data):
    # create a design matrix for occupancy and segmentation
    preliminary_design_matrix = (
        eemeter.create_caltrack_hourly_preliminary_design_matrix(
            data['baseline_meter_data'], data['temperature_data'],
        )
    )

    # build 12 monthly models - each step from now on operates on each segment
    segmentation = eemeter.segment_time_series(
        preliminary_design_matrix.index,
        'three_month_weighted'
    )

    # assign an occupancy status to each hour of the week (0-167)
    occupancy_lookup = eemeter.estimate_hour_of_week_occupancy(
        preliminary_design_matrix,
        segmentation=segmentation,
    )

    # assign temperatures to bins
    temperature_bins = eemeter.fit_temperature_bins(
        preliminary_design_matrix,
        segmentation=segmentation,
    )

    # build a design matrix for each monthly segment
    segmented_design_matrices = (
        eemeter.create_caltrack_hourly_segmented_design_matrices(
            preliminary_design_matrix,
            segmentation,
            occupancy_lookup,
            temperature_bins,
        )
    )

    # build a CalTRACK hourly model
    baseline_model = eemeter.fit_caltrack_hourly_model(
        segmented_design_matrices,
        occupancy_lookup,
        temperature_bins,
    )

    return baseline_model


def save_model(model, meter_id=None, frequency=None):
    # persist the given model in the DB
    return BaselineModel.objects.create(
        data=model.json(),
        model_class=model.__class__.__name__,
        meter_id=meter_id,
        frequency=frequency)


def load_model(model):
    # load a model from a persisted instance
    # check that the model class exists and supports from_json
    # this throws an exeption if the class does not exist
    clazz = getattr(eemeter, model.model_class)
    # this throws an exeption if the class does not have a from_json method
    m = clazz.from_json(model.data)
    return m


def get_savings(data, baseline_model):
    # get a year of reporting period data
    reporting_meter_data, warnings = eemeter.get_reporting_data(
        data['meter_data'], start=data['blackout_end_date'], max_days=365
    )

    # compute metered savings for the year of the reporting period we've selected
    metered_savings_dataframe, error_bands = eemeter.metered_savings(
        baseline_model, reporting_meter_data,
        data['temperature_data'], with_disaggregated=True
    )

    # total metered savings
    total_metered_savings = metered_savings_dataframe.metered_savings.sum()

    return {
        'total_savings': total_metered_savings,
        'metered_savings': metered_savings_dataframe,
        'error_bands': error_bands
    }
