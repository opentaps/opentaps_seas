.. _user_doc:

User Documentation
==================

Signing In
^^^^^^^^^^

Open your browser and put ``http://your.ip.address.here:8000`` or the URL opentaps SEAS has been set up on.  You should see the initial login screen here,
or the Sites page if you're already logged in.


Sites
^^^^^

A site is a particular building or facility with many different pieces of equipment.  The Sites page lists all the sites you've set up, and you can also add new sites here.  

The map displays all your sites with Google Maps.  You will need to set up your Google API key in secrets.json.  It will display the locations with either a geoStreet
or geoStreetAddress tag.  If geoStreet is set, it will use geoStreet, geoCity, geoState, geoPostalCode, geoCountry; otherwise it will use geoStreetAddress.

Site
^^^^

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
 

Equipment
^^^^^^^^^

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

Data Points
^^^^^^^^^^^

This page shows a data point, with all its tags.  Then it shows the latest value and a graph of the historical data.  If the a Grafana dashboard has been created for this data point,
there will be a Grafana icon.  Clicking on this icon will open up the Grafana dashboard in a separate browser window.

Below are the files and notes for this data point.


Topics
^^^^^^

This page shows a list of the topics that are in the time series database.  If the topic has been mapped to a data point, the data point will be shown next to it.
Otherwise, click on Add to add this topic as a new data point.

You can also use the Import Topics button import the BACNet scans from VOLTTRON.  This imports a combination of CSV and JSON files as new topics.  The CSV and JSON files should be 
in the format of .csv and .config files in the 
``/examples/configurations/drivers/`` directory of the VOLTTRON repository.  If coming from the VOLTTRON BACNet scans, the CSV file would be from the ``registry_configs`` directory,
and the JSON file would be from the ``devices`` directory.  

When importing, you must associate it with a Site and add a prefix to all the topics so that they match the data points from VOLTTRON.
By default, the CSV files from VOLTTRON only have the file portion of the full data point name, so if a data point's full name is
``campus_A/building_2/controller_3/equipment_4/status``, it will be ``equipment_4/status`` in the VOLTTRON CSV.  In that case, you will need to
put ``campus_A/building_2/controller_3`` here.  
They will be added to your topics with a ``/`` between your prefix and the topic name.  
The import will add them as topics and data points, with a reference to the site ID, and the additional BACNET data will be stored with the data point.  

After importing the data points, they will need to be associated with equipment and site.  You can do this by clicking on the data point, then edit tags, and adding the equipRef
and siteRef tags.  

To tag your topics, please see "Tagging Rules" section below.

Tagging Rules
#############

Tagging data points is ultimately very helpful in understanding your data, and tags are required for running services on your data.  However, tagging has always been a very manual and time
consuming process.  We've tried to help streamline this process by introducing "Tagging Rules", which allow you to create sets of rules that could be used to tag all your topics.  This works
like this:

 * Topics could be filtered by several conditions.  For example, we can filter our topics to those that contain "SP" and "ZoneTemp".
 * We can then apply tags to our filtered list of topics.  For example, for all topics which contain "ZoneTemp" and "SP", we can apply the tags sp, temp, zone.  This is called a **rule**.
 * We can then group many rules together in to a **rule set**.  Rule sets could be used to organize rules by equipment manufacturer or building owner, so they can be used to tag topics with similar syntax. 

There are a couple of ways to do this in the user interface.  First, from the Topics page, you can start filtering the topics by selecting Contains or Not Contains and putting text 
into the "Filter Topics" input box.  You can use wildcards and regex here.  This will show you a list of filtered topics.

Click on "Show unmapped topics only." to see only the topics which have not been mapped to data points.  Then you can click on "Show all topics." to see all the topics again.    
You can also click "Select all topics matching the filters on all pages."  If you choose this, it will check all the topics that match your filters on all the pages of results, 
not just what you see on the current page.  

Then you can choose the topics you want to add tags.  Once you've selected some topics, you can click on "Select all that match the filters on all pages" to select
all the topics on all the pages that match your filter conditions.  You can later click "Clear selection" to uncheck this option.

Next, go below to the "Tag Selected Topics" section to add tags for these topics.  You can choose either to add individual tags or add tags from a Model (see below.)  If you choose to add tags
from a Model, it will ask you to choose from top level Models first.  Then, it will show you the tags from the top level Model, and then ask you to select from any child Models of your Model.
You can choose to add either the current Model's tags or choose a child Model.  Click on "Add these Tags"
to add the tags of the Model you've chosen.  This adds the tags of the currently selected model to the list of tags that could be applied.  
At any one time, you can only choose to add tags from one Model, and not its parents at the same time.  
Then click "Apply Tags" to apply these tags to the topics.   

From here you can also click on "Save as a Rule", and it will open a dialog box below.  Here you can choose to save to a new rule set or an existing one, then put a name for your rule, and save
the filter/tags as a rule.  

The second way is to click on the "Tagging Rules" button.  Then you will see all the tagging rules created so far.  Click on one to see the rules inside.  Click on the rule, and you will be taken
to the filter page, where you can change the tags and update it.  You can also create new rule sets and rules in these screens.

From this page, you can also click on "Run" to run this rule set.  You can put in a prefix so that your rules are only run for topics of that prefix, so you can run different rule sets for different
buildings and equipment.

You can use the Export and Import features to save your tagging rules as a JSON file download and then upload it again.

Using SQL Scripts
#################

Another way to tag your topics is to use a SQL script to update these tags in bulk based on their naming patterns.  See the file ``data/ahu/demo/tag_entities.sql`` for an example of how to do this. 

Topics Report
#############

To see how you're doing with the tagging, use this report.  It provides you a CSV file of all the topics and their current tags.  
The topics are in rows and the tags are in columns, and the value will be in the
cells.  If the tags is a marker tag, there will be an X.

Exporting Topics
################

This can be used to create VOLTTRON BACNet CSV and JSON configuration files, so you can choose which topics to trend or set different trending intervals for your topics.
To use this feature, first set the ``trending`` tag to the trending interval in minutes for your topics, as
part of your Tagging Rules or applying tags to your filtered topics.  Then, click on Export from the Topics page or from the BACNet Configs section of your Site.  If you come from
the Topics page, you will have to choose the Site and the BACNet Config prefix.

Then you can
choose to only export the topics with Trending set, which means only the topics with ``trending`` set will be exported, or uncheck this to export all the topics with this prefix.  
You will get a zip file with CSV and JSON for each distinct ``trending`` tag value for this BACNet Config prefix.  For example, if you set some topics to trend at 5 minutes, some at
15 minutes, and some at 60 minutes, you will get CSV and JSON files for 5, 15, and 60 minutes with _5, _15, and _60 in their file names.  If you unchecked "Only export the topics with
Trending set", then you will get a CSV and JSON file combination for all the other topics that do not have trending set as well.  These config files can then be loaded into your 
on site VOLTTRON instance. 

Models
^^^^^^

Models are standard templates of tags, content, and notes.  They can be used to standardize tags, content, and notes for commoonly used equipment.  If you put tags, files or links, and notes 
on a Model, and then tag the Equipment of a Site as that Model, the Equipment gets all the tags, files, links, and notes of your Model.  This is a one time inheritance: If you change them on 
the Model again, they will not automatically be changed on the Equipment that already has been linked to the Model. 

For example, you can create a Model called "Siemens Standard RTU" and then put all
the information common to that model.  Then for all the machines like your "Siemens Standard RTU", you can just set their Model, and they can all get the same tags and data from the model. 

They can also be used to group tags together for tagging topics.  You can create a Model with several tags together, then apply them to topics which fit a filter or rule.  This is also one
time: The tags are added to your topics when you apply them or add them to the rule.  If later you change the Model, your topics' or rule's tags will not automatically change.

On the Models page, you will see the "top level" Models that do not have any child models.  Click on a top level Model, and you will see a list of its children.  Models can be nested as 
deeply as you want.  When you create a new Model, you can choose any other Model to be its parent.
  

Tags
^^^^

Tags are for any metadata information.  They could be your custom tags or the tags from Project Haystack.  By default, the Project Haystack 3.0 tags are loaded as part of the seed data.  There are also
some other tags which are not part of the Haystack standard, but which are useful to opentaps SEAS.  They are loaded from a separate tag seed data file.

For boolean or marker tags, (the entity.kv_tags with type=Bool), a value of 0 in the time series database represents False and anything else represents True.
