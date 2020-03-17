User Documentation
##################

Signing In
**********

Open your browser and put ``http://your.ip.address.here:8000`` or the URL opentaps SEAS has been set up on.  You should see the initial login screen here,
or the Sites page if you're already logged in.


Main Sections
*************

Sites
=====

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
 * BACNet configs imported from VOLTTRON (see Topics below.)  Each config is listed by the prefix, and you can click on Topics to view the topics (data points) of this prefix or Export to export them again.  Click on Run Rules to run a rule set (see below) to apply tags for topics of this prefix.  From here you can also create an Equipment for this config.  This is helpful if each BACNet config points to a particular machine, rather than a supervisory controller. 
 
Meters
======

Each site could be associated with one or more meters, which could be a utility meter or a measuring device to record solar generation, battery charge or discharge, or any other technology’s 
use or production of energy.  Each Meter is associated with a Weather Station.  We currently use the NOAA ISD weather stations and weather data based on OpenEE Weather.
When you add a Meter, the UI uses the location of the Site to get the nearest Weather Station, so all Meters at the same Site will have the same Weather Stations.  If you click on a
Weather Station, you can see detailed information about it and use the Fetch Data button to get historical readings from the station.  

A meter could be removed from a site, but it is not deleted.  The meter and weather histories are permanently stored in opentaps for you.

Each meter is also associated with a rate plan, which is used to calculate billing for the meter's readings.  You will be prompted to add this rate plan when you add a new meter.  You can choose from a "Simple Rate Plan"
which is a simple flat rate plan used for demo purposes, or you can choose to get your rate plan from OpenEI's utility rate database.  

When you click through to a meter, you will see its past readings (history).  You can use the up arrow icon to upload the meter history using either a CSV format or the Green Button XML format.  An example of the
CSV file format could be found in the file ``examples/meter.csv``.  Examples of the Green Button XML file could be found at https://www.energy.gov/downloads/green-button-sample-data-pge     

Below the readings is the meter's weather station, with the latest temperature data.  You can download the temperature data or click through the weather station to see more details about it.

Below the weather station is the rate plan of the meter.  You can click on this to see the history of this meter's rate plan and get more rate data from OpenEI.  You can have different rate plans associated with a meter
over time for this meter, for example switching from traditional to time of use plans.  Click on one of the plans to see the details from OpenEI.

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


Equipments
==========

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
^^^^^^^^^^^^^^^^^^^^^^^

SolarEdge solar systems are a special type of equipment.  If you choose SolarEdge when you create an equpiment, you will be prompted for the API key and site ID.  You can set up as 
many different SolarEdge systems as you'd like, each with their own API key, so you can monitor all your customer sites' systems.

opentaps will then create an equipment and a meter for each SolarEdge system.  On the equipment page, you can click on the "Get Details" button to get you detailed information
about the system from SolarEdge.  The SolarEdge system equipment
is like any other equipment at your site, so you can associate files, notes, and tags with it.  On the meter page, it will show
you the power generated from the system over time.  Instead of the upload icon, there is a cloud icon.  Use this to download more data from SolarEdge.

Data Points
===========

This page shows a data point, with all its tags.  Then it shows the latest value and a graph of the historical data.  If the a Grafana dashboard has been created for this data point,
there will be a Grafana icon.  Clicking on this icon will open up the Grafana dashboard in a separate browser window.

Below are the files and notes for this data point.


Topics
======

This page shows a list of the topics that are in the time series database.  By default, it will show the object name, present value, and units from BACNet to help you determine what
the topics are.  You can customize which values are displayed for your topics by clicking on the gear box icon to the right.  This will bring up a menu for configuring the display:
You can remove fields, change the labels of the fields, or add new fields to display.  You can also click on "Reset to Default" to go back to the default values.  

If the topic has been mapped to a data point, you can click on the View button to see it.
Otherwise, click on Add to add this topic as a new data point.  At the top, you can filter the list of topics to show only those which have not been mapped to a data point, or show
those which have the Haystack ``his`` tag, which means that the topics is being trended from the BAS. 

You can also use the Import Topics button import to import your topics.  Here you can choose to import from either a CSV file or from the BACNet scans from VOLTTRON.  

The CSV file import allows you to import the topics in the same format as the CSV file that the topics were exported as a Report (see below.)  When importing the topics, you can 
choose to "Clear existing tags", which would remove all the existing tags for all your topics and then set only the tags in your CSV file.  If you do not choose this, then
the tags in your CSV file would only be added or modified, and whatever tags are already on your topics will still be there.  Tags which begin with "__" will be ignored.  For example,
topic names are usually downloaded as "__topic", so they cannot be changed by importing from the spreadsheet.

You can also import from VOLTTRON BACNet scans, which is a combination of CSV and JSON files as new topics.  The CSV and JSON files should be 
in the format of .csv and .config files in the 
``/examples/configurations/drivers/`` directory of the VOLTTRON repository.  If coming from the VOLTTRON BACNet scans, the CSV file would be from the ``registry_configs`` directory,
and the JSON file would be from the ``devices`` directory.  

When importing, you must associate it with a Site and add a prefix to all the topics so that they match the data points from VOLTTRON.
By default, the CSV files from VOLTTRON only have the file portion of the full data point name, so if a data point's full name is
``campus_A/building_2/controller_3/equipment_4/status``, it will be ``equipment_4/status`` in the VOLTTRON CSV.  In that case, you will need to
put ``campus_A/building_2/controller_3`` here.  
They will be added to your topics with a ``/`` between your prefix and the topic name.  
The import will add them as topics and data points, with a reference to the site ID.  The BACNET configuration and Additional BACNET data will be stored with the data point as tags with
prefix ``bacnet_``.  

After importing the data points, they will need to be associated with equipment and site.  You can do this by clicking on the data point, then edit tags, and adding the equipRef
and siteRef tags.  

To tag your topics, please see "Tagging Rules" section below.

Tagging Rules
-------------

Tagging data points is ultimately very helpful in understanding your data, and tags are required for running services on your data.  However, tagging has always been a very manual and time
consuming process.  We've tried to help streamline this process by introducing "Tagging Rules", which allow you to create sets of rules that could be used to tag all your topics.  This works
like this:

 * Topics could be filtered by several conditions.  For example, we can filter our topics to those that contain "SP" and "ZoneTemp".
 * We can then apply tags to our filtered list of topics.  For example, for all topics which contain "ZoneTemp" and "SP", we can apply the tags sp, temp, zone.  This is called a **rule**.
 * We can then group many rules together in to a **rule set**.  Rule sets could be used to organize rules by equipment manufacturer or building owner, so they can be used to tag topics with similar syntax. 

The rules and filters can be run for either the topic name (Topic) or any tag associated with the topic, including all the ``bacnet_`` tags acquired when the topic was originally imported.  
The options for the rules and filters are:

 * ``Equals``, ``Not Equals`` - value must be strictly equal or not equal condition.  This is not case sensitive.
 * ``Contains``, ``Not Contains`` - value must contain or not contain condition.  The condition could be in beginning, middle, or end of the value.  This is also not case sensitive.
 * ``Is Present``, ``Is Absent`` - used to check if the tag is present or absent on the topic.  
 * ``Matches`` - used to specify a regular expression matching

The filters can be joined by AND or OR conditions.  If there is an OR between two filter conditions, then it is strictly an OR between those conditions.  So A OR B AND C means (A OR B) AND C, not
A OR (B AND C); A OR B AND C OR D OR E AND F means (A OR B) AND (C OR D OR E) AND F.

**IMPORTANT!** The rules are just run once in the sequence given, so if you rely on tags to apply other tags, the sequence of the rules will affect the final output.

There are a couple of ways to do this in the user interface.  First, from the Topics page, you can start filtering the topics by selecting Contains or Not Contains and putting text 
into the "Filter Topics" input box.  You can use wildcards and regex here.  This will show you a list of filtered topics.

Click on "Show unmapped topics only." to see only the topics which have not been mapped to data points.  Then you can click on "Show all topics." to see all the topics again.    
You can also click "Select all topics matching the filters on all pages."  If you choose this, it will check all the topics that match your filters on all the pages of results, 
not just what you see on the current page.  

Then you can choose the topics you want to add tags.  Once you've selected some topics, you can click on "Select all that match the filters on all pages" to select
all the topics on all the pages that match your filter conditions.  You can later click "Clear selection" to uncheck this option.

Next, go below to the "Tag Selected Topics" section to specify what to do for these topics.  You can choose to add individual tags or add tags from a Model (see below.)  If you choose to add tags
from a Model, it will ask you to choose from top level Models first.  Then, it will show you the tags from the top level Model, and then ask you to select from any child Models of your Model.
You can choose to add either the current Model's tags or choose a child Model.  Click on "Add these Tags"
to add the tags of the Model you've chosen.  This adds the tags of the currently selected model to the list of tags that could be applied.  
At any one time, you can only choose to add tags from one Model.  Tags from parent models are not added at the same time.  

You can also choose to remove tags, which means that the topics matching the conditions will have the tags removed.  If you do this, also remember that the rules are just run once in their
specified sequence, so the tags would have to exist or been added by other rules before they could be removed. 
 
Then click "Apply Tags" to apply these tags to the topics.

Rule can be used to create new equipment based on the topics.  For example, we can create a series of VAV equipment based on names that contain VAV-*.
To do this, the rule filter should contain Topic 'Matches' regex expression, for example '.*vav-(.*)'.
Then a rule with create equipment action fields should be set, for example:

 * equipment_name: "{group[1]} test equip name"
 * site_object_id: ref to a site
 * model_object_id: ref to a model

Regex will then matche group[1] value as part of the new equipment name.
When the rule is run, we should have one or more new equipment, and models tags should be added to those equipment and data points should be linked to appropriate equipment.

From here you can also click on "Save as a Rule", and it will open a dialog box below.  Here you can choose to save to a new rule set or an existing one, then put a name for your rule, and save
the filter/tags as a rule.  

The second way is to click on the "Tagging Rules" button.  Then you will see all the tagging rules created so far.  Click on one to see the rules inside.  Click on the rule, and you will be taken
to the filter page, where you can change the tags and update it.  You can also create new rule sets and rules in these screens.

From this page, you can also click on "Run" to run this rule set.  You can put in a prefix so that your rules are only run for topics of that prefix, so you can run different rule sets for different
buildings and equipment.  Before you run the rules, you can use the Preview feature to see the result of running your rules on the existing topics.  This can be displayed on screen or downloaded in
a CSV file format.  The standard format is to show all the topics with their tags if the rules had been run.  However, you can also choose to "Preview in diff format", which would show the difference
in tags before and after running the rules.  Each topic would be listed in a row, and for each tag that is changed, there is a before and an after column to show the effect of the rules:

 * If previous is empty and new is X - this means it was added
 * If previous is X and new is empty - this means it was removed
 * If previous is X and new is X - this means it was set before and after (ie no change)
 * If previous is empty and new is empty - this means it was empty before and after (ie no change)
 * If previous is X and new is Y - this means it was changed (for kv tags)

You can use the Export and Import features to save your tagging rules as a JSON file download and then upload it again.

Using SQL Scripts
^^^^^^^^^^^^^^^^^

Another way to tag your topics is to use a SQL script to update these tags in bulk based on their naming patterns.  See the file ``data/ahu/demo/tag_entities.sql`` for an example of how to do this. 

Topics Report
^^^^^^^^^^^^^

To see how you're doing with the tagging, use this report.  It provides you a CSV file of all the topics and their current tags.  
The topics are in rows and the tags are in columns, and the value will be in the
cells.  If the tags is a marker tag, there will be an X.  

This CSV file can then be modified and imported back into the system (see above.)  Tags which start with "__" should not be modified, as they will be ignored when you import the CSV file again. 

Exporting Topics
^^^^^^^^^^^^^^^^

Topics can be exported either to a CSV file like the one used for importing topics or to the VOLTTRON BACNet configuration files.  The CSV file has all the topics and their current tags.  
The topics are in rows and the tags are in columns, and the value will be in the
cells.  If the tags is a marker tag, there will be an X.  

This CSV file can then be modified and imported back into the system (see above.)  Tags which start with "__" should not be modified, as they will be ignored when you import the CSV file again. 

The VOLTTRON BACNet configuration files are the CSV and JSON configuration files VOLTTRON uses to configure which topics to trend or set different intervals for your topics.
To use this feature, first set the ``interval`` tag to the interval in minutes for your topics, as
part of your Tagging Rules or applying tags to your filtered topics.  Then, click on Export from the Topics page or from the BACNet Configs section of your Site.  If you come from
the Topics page, you will have to choose the Site and the BACNet Config prefix.

Then you can
choose to only export the topics with Interval set, which means only the topics with ``interval`` set will be exported, or uncheck this to export all the topics with this prefix.  
You can also choose to export only the topics with the Haystack ``his`` tag set, which is used to denote that the topic is being trended from the BAS system.

You will get a zip file with CSV and JSON for each distinct ``interval`` tag value for this BACNet Config prefix.  For example, if you set some topics to trend at 5 minutes, some at
15 minutes, and some at 60 minutes, you will get CSV and JSON files for 5, 15, and 60 minutes with _5, _15, and _60 in their file names.  If you unchecked "Only export the topics with
Interval set", then you will get a CSV and JSON file combination for all the other topics that do not have interval set as well.  These config files can then be loaded into your 
on site VOLTTRON instance. 

Transactions
============

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

Models
======

Models are standard templates of tags, content, and notes.  They can be used to standardize tags, content, and notes for commoonly used equipment.  If you put tags, files or links, and notes 
on a Model, and then tag the Equipment of a Site as that Model, the Equipment gets all the tags, files, links, and notes of your Model.  This is a one time inheritance: If you change them on 
the Model again, they will not automatically be changed on the Equipment that already has been linked to the Model. 

For example, you can create a Model called "Siemens Standard RTU" and then put all
the information common to that model.  Then for all the machines like your "Siemens Standard RTU", you can just set their Model, and they can all get the same tags and data from the model. 

They can also be used to group tags together for tagging topics.  You can create a Model with several tags together, then apply them to topics which fit a filter or rule.  This is also one
time: The tags are added to your topics when you apply them or add them to the rule.  If later you change the Model, your topics' or rule's tags will not automatically change.

On the Models page, you will see the "top level" Models that do not have any child models.  Click on a top level Model, and you will see a list of its children.  Models can be nested as 
deeply as you want.  When you create a new Model, you can choose any other Model to be its parent.

You can duplicate a Model, which creates a copy of the original Model with all the same tags.  

Tags
====

Tags are for any metadata information.  They could be your custom tags or the tags from Project Haystack.  By default, the Project Haystack 3.0 tags are loaded as part of the seed data.  There are also
some other tags which are not part of the Haystack standard, but which are useful to opentaps SEAS.  They are loaded from a separate tag seed data file.

For boolean or marker tags, (the entity.kv_tags with type=Bool), a value of 0 in the time series database represents False and anything else represents True.
