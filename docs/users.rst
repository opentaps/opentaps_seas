User Documentation
==================

Signing In
-------------

Open your browser and put ``http://your.ip.address.here:8000`` or the URL opentaps SEAS has been set up on.  You should see the initial login screen here,
or the Sites page if you're already logged in.


Main Sections
==================

Sites
-------------

A site is a particular building or facility with many different pieces of equipment.  The Sites page lists all the sites you've set up, and you can also add new sites here.  

The map displays all your sites with Google Maps.  You will need to set up your Google API key in secrets.json.  It will display the locations with either a geoStreet
or geoStreetAddress tag.  If geoStreet is set, it will use geoStreet, geoCity, geoState, geoPostalCode, geoCountry; otherwise it will use geoStreetAddress.

The Site page shows 

 * tags associated with the site.  The Project Haystack abbreviated tag (i.e., ``site``) is displayed.  If you hover over a tag, it will display the description of the tag.
 * a summary of the current site.  On the left hand side you will see a pie chart of temperature readings from all the equipment sensors' data points which have the tags ``{air, his, point, sensor, temp}``.  You can adjust the temperature ranges (preset to 69 to 75) in the input box below the pie chart.  Green means comfortable, blue means cold, red means hot, and black means no data is available.   On the right hand side is a chart of all the Air Handling Unit equipment with tag ``ahu``.  The data displayed is:

  * Equipment Description: ``dis`` tag
  * Space Air Temp:  ``{air,his,point,zone,sensor,temp}``
  * Return Air Temp: ``{air,his,point,return,sensor,temp}``
  * Supply Fan Speed - ``{air,discharge,fan,his,point,sensor,speed}``
  * Cooling -  ``{cooling,his,point,sensor}``
  * Heating - ``{heat,his,point,sensor}``
  * CO2 - ``{co2,his,point,sensor,zone}``

 * all the equipment of a single site and the number of data points for each equipment.  If you click on the down arrow next to the count of data points, it will display the most recent readings for that equipment.
 * files associated with the site.  Here you can either upload a file, such as a photo or PDF document, or add a link to an external document or even video.  
 * notes associated with the site.  Here you can enter notes about the site.
 * BACNet configs imported from VOLTTRON (see the Users - Topics document.)  This section appears if your site has BACNet configurations.  Each config is listed by the prefix, and you can click on Topics to view the topics (data points) of this prefix or Export to export them again.  Click on Run Rules to run a rule set (see below) to apply tags for topics of this prefix.  From here you can also create an Equipment for this config.  This is helpful if each BACNet config points to a particular machine, rather than a supervisory controller. 
 
Meters
-------------

Each site could be associated with one or more meters, which could be a utility meter or a measuring device to record solar generation, battery charge or discharge, or any other technology’s 
use or production of energy.  Each Meter is associated with a Weather Station.  We currently use the NOAA ISD weather stations and weather data based on OpenEE Weather.
When you add a Meter, you can either enter all the information, or use UtilityAPI.  If you enter all the information yourself, 
the UI uses the location of the Site to get the nearest Weather Station, so all Meters at the same Site will have the same Weather Stations.  If you click on a
Weather Station, you can see detailed information about it and use the Fetch Data button to get historical readings from the station.  

If you add a meter from UtilityAPI, you will need to enter your customer's email address.  If UtilityAPI finds that customer's meter by email address, you will be able to add it to your site.
If not, you will have to create an authorization form in UtilityAPI for the customer to agree to share their meter data with you, and UtilityAPI will give you a link to send to your customer to access
the form.  You can send this link to your customer by email or text.  Once the customer authorizes your access, you can come back to this screen and add their meter.

A meter could be removed from a site, but it is not deleted.  The meter and weather histories are permanently stored in opentaps for you.

Each meter is also associated with a rate plan, which is used to calculate billing for the meter's readings.  You will be prompted to add this rate plan when you add a new meter.  You can choose from a "Simple Rate Plan"
which is a simple flat rate plan used for demo purposes, or you can choose to get your rate plan from OpenEI's utility rate database.  

When you click through to a meter, you will see its past readings (history).  Above the readings are three buttons:

 * You can use the powerplug button to get the latest meter readings from UtilityAPI. If the meter was not set up as a UtilityAPI meter, you can do it here.    
 * You can use the up arrow icon to upload the meter history using either a CSV format or the Green Button XML format.  An example of the CSV file format could be found in the file ``examples/meter.csv``.  Examples of the Green Button XML file could be found at https://www.energy.gov/downloads/green-button-sample-data-pge  
 * You can use the down arrow to download the meter readings in a CSV format. 

Below the readings is the meter's weather station, with the latest temperature data.  You can download the temperature data or click through the weather station to see more details about it.

Below the weather station is the rate plan of the meter.  You can click on this to see the history of this meter's rate plan and get more rate data from OpenEI.  You can have different rate plans associated with a meter
over time for this meter, for example switching from traditional to time of use plans.  Click on one of the plans to see the details from OpenEI.

If your meter is set up with UtilityAPI, it will show the UtilityAPI UUID of the meter.  You can click on Get Bills to get past bills from UtilityAPI.  These will show up as "Financial Values" under the Models.  Click 
on one of them, and you can see the detailed line items of the bill.

Below the Meter is a list of Models.  These models are models of energy usage and can be used for Measurement and Verification (M&V) of energy savings.  Currently we're including the OpenEEMeter 
models, which are IPMVP Option C whole building energy use statistical models that follow the CalTrack 2.0 standard (See https://www.caltrack.org and http://eemeter.openee.io/tutorial.html for more details.)  

You can click on the "Build a Model" button to build a new model for this meter.  This screen is currently based on input needed for OpenEEMeter models and will ask if you want a daily or hourly model and the
ending date of the weather and meter readings used to build the model.  CalTrack requires that exactly a full year (no more, no less) of data be used for model estimation, so your model will be built with data 
from a year before to this ending date.  You can also specify the other parameters of your model, and OpenEEMeter will use these parameters to find the best model fit in the end.  
See https://github.com/openeemeter/eemeter/blob/fc91df2b5fa69125a85b1235d24783c350d5b99a/docs/caltrack_compliance.rst on what the different parameters are.  
In general, for gas only meters, uncheck the `Fit CDD`, `Fit CDD Only`, and `Fit CDD HDD`, and for electric meters when gas is used for heating, unchecked the `Fit HDD Only`
and `Fit CDD HDD`. 

Once it is built, you will see it in the list of Models below.  Because building a model takes a while, you have the option to run it in the background (async.)

Clicking on a Model, you will see the following:

 * View Details - You can see the actual parameters of the model here.  See https://www.caltrack.org/project-updates/week-six-caltrack-update for an explanation of some of the key statistics.  See also https://www.caltrack.org/project-updates/week-eight-caltrack-update and https://evo-world.org/en/news-media/m-v-focus/868-m-v-focus-issue-5/1164-why-r2-doesn-t-matter about ASHRAE standards for the CVRMSE statistic.
 * Calculate Production - Calculate the energy produced, as calculated by this model.  (See below.)
 * A graph of the model if you have a daily model.  Currently OpenEEMeter produces graphs for its daily but not hourly models.  On this graph, the red lines are disqualified or rejected candidate models, green lines are qualified model candidates, and the orange line is the chosen model.  
 * History of the energy produced, as calculated by this model.

The Meter Production shows the actual energy saved, or "produced," as calculated by this particular model for this meter.  It is a time series of kWh and calculated in either hourly or daily increments, depending 
on the type of model you have.  It may be counterintuitive to think that energy savings has produced energy, but remember that we'll ultimately be considering energy efficiency savings, renewable energy production,
and battery stored energy in the same way: More energy for the consumer.  Or, as we like to say, "Energy efficiency is an asset, not an expense."

Below the Meter Production is a history of the financial value of the energy produced (or saved) as calculated by this Model, based on this Meter's rate plan.  It is always aggregated by the billing interval of the 
Meter's rate plan, even if the particular Model was only active during part of the month.


Equipment
---------

This page shows an item of equipment, with all its tags.  You can associate an Equipment with a Model (see below.)

Below the tags are is a section for the data points.  If the equipment is an AHU, there is a Grafana icon on the right of the Data Points section header.
First time clicking on the Grafana icon will create a Grafana dashboard. Clicking on this icon next time will open up the Grafana dashboard in a separate browser window.
If the a Grafana dashboard has been created the embedded dashboard snapshot will be shown up below data points section header.  You must be logged into Grafana for the
embedded dashboard to show up.  The dashboard displays the data points for these tags:

 * Cool Valve CMD - tags ``cool, valve, cmd, his, point``	
 * Heat Valve CMD - tags ``heat, valve, cmd, his, point``
 * OA_Damper_CMD - tags ``outside, air, damper, his, point``
 * ZoneTemp - tags ``temp, zone, air, his, point``
 * ZoneTempSP - tags ``temp, zone, air, sp, his, point``
 * MixedAirTemp - tags ``temp, mixed, air, his point``

Below the dashboard are the data points.  Click on any data point to see its historical values.  Below the data points are files and notes associated with this equipment.

SolarEdge Solar Systems
------------------------

SolarEdge solar systems are a special type of equipment.  If you choose SolarEdge when you create an equpiment, you will be prompted for the API key and site ID.  You can set up as 
many different SolarEdge systems as you'd like, each with their own API key, so you can monitor all your customer sites' systems.

opentaps will then create an equipment and a meter for each SolarEdge system.  On the equipment page, you can click on the "Get Details" button to get you detailed information
about the system from SolarEdge.  The SolarEdge system equipment
is like any other equipment at your site, so you can associate files, notes, and tags with it.  On the meter page, it will show
you the power generated from the system over time.  Instead of the upload icon, there is a cloud icon.  Use this to download more data from SolarEdge.

Data Points
-------------

This page shows a data point, with all its tags.  Then it shows the latest value and a graph of the historical data.  If the a Grafana dashboard has been created for this data point,
there will be a Grafana icon.  Clicking on this icon will open up the Grafana dashboard in a separate browser window.

Below are the files and notes for this data point.


Transactions
-------------

Transactions are payments for the energy produced.  They are automatically created from metered energy production or savings and are related to the specific site, meter, and M&V model.
Once created, they can be in a variety of statuses, such as 

 * Created: Created 
 * Pending Review: Needs review 
 * In Dispute: In dispute between parties 
 * Approved: Approved 
 * Denied: Denied 
 * Completed: Completed (i.e., paid) 
 * Error: Cannot be completed due to technical error 

With each transaction, you can associate files, documents, and notes as part of the payment process.

Transactions related to a particular site or meter are also displayed when you view that site or meter.


