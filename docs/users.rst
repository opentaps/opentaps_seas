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
  * Space Air Temp:  ``{air,his,point,sensor,temp}``
  * Return Air Temp: ``{air,his,point,return,sensor,temp}``
  * Supply Fan Speed - ``{air,discharge,fan,his,point,sensor,speed}``
  * Cooling -  ``{cooling,his,point,sensor}``
  * Heating - ``{heat,his,point,sensor}``
  * CO2 - ``{co2,his,point,sensor,zone}``

 * all the equipment of a single site and the number of data points for each equipment.  If you click on the down arrow next to the count of data points, it will display the most recent readings for that equipment.
 * files associated with the site.  Here you can either upload a file, such as a photo or PDF document, or add a link to an external document or even video.  
 * notes associated with the site.  Here you can enter notes about the site.


Equipment
^^^^^^^^^

This page shows an item of equipment, with all its tags.  You can associate an Equipment with a Model (see below.)

Below the tags are all the data points of the Equipment.  Click on any data point to see its historical values.  Below the data points are files and notes associated with this equipment.

Data Points
^^^^^^^^^^^

This page shows a data point, with all its tags.  Then it shows the latest value and a graph of the historical data.  If the a Grafana dashboard has been created for this data point,
there will be a Grafana icon.  Clicking on this icon will open up the Grafana dashboard in a separate browser window.

Below are the files and notes for this data point.


Topics
^^^^^^

This page shows a list of the topics that are in the time series database.  If the topic has been mapped to a data point, the data point will be shown next to it.
Otherwise, click on Add to add this topic as a new data point.

You can also use the Import Topics button import a CSV file of new topics.  This CSV file should be in the format of the BACNET.csv file that VOLTTRON's BACNet scan
generates (see ``/examples/configurations/drivers/bacnet.csv`` for an example.)  When importing, you can add a prefix all the BACNET points, for example ``campus_A/building_2/``, 
and they will be added to your topics.  The import will add them as topics and data points, and the additional BACNET data will be stored with the data point.  

After
importing the data points, they will need to be associated with equipment and site.  You can do this by clicking on the data point, then edit tags, and adding the equipRef
and siteRef tags.  Or this could be done by using SQL in PostgreSQL to update these tags in bulk based on their naming patterns.  See the file ``data/ahu/demo/tag_entities.sql`` for an example of how to do this. 

Models
^^^^^^

Models are standard templates of tags, content, and notes.  If you put tags, files or links, and notes on a Model, and then tag the Equipment of a Site as that Model, the Equipment inherits all the tags, files, links, and notes of your Model.  The inherited information is not changeable for the Equipment.  They can only be changed at the Model level.

This feature is to help you standardize tags, content, and notes for your commonly used equipment.  For example, you can create a Model called "Siemens Standard RTU" and then put all
the information common to that model.  Then for all the machines like your "Siemens Standard RTU", you can just set their Model, and they will 


Tags
^^^^

Tags are for any metadata information.  They could be your custom tags or the tags from Project Haystack.  By default, the Project Haystack 3.0 tags are loaded as part of the seed data.

For boolean or marker tags, (the entity.kv_tags with type=Bool), a value of 0 in the time series database represents False and anything else represents True.
