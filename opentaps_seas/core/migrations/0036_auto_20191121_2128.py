# Generated by Django 2.1.11 on 2019-11-22 03:28

import cratedb.fields.array
import cratedb.fields.hstore
from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0035_auto_20191121_2115'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteWeatherStations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_datetime', models.DateTimeField(default=django.utils.timezone.now, verbose_name='From Date')),
                ('thru_datetime', models.DateTimeField(null=True, verbose_name='Thru Date')),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('created_datetime', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created Date')),
                ('created_by_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_site_weather_stations',
            },
        ),
        migrations.RenameField(
            model_name='weatherhistory',
            old_name='Weather_history_id',
            new_name='weather_history_id',
        ),
        migrations.RenameField(
            model_name='weatherhistory',
            old_name='Weather_station_id',
            new_name='weather_station_id',
        ),
        migrations.AddField(
            model_name='siteweatherstations',
            name='site_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Entity'),
        ),
        migrations.AddField(
            model_name='siteweatherstations',
            name='weather_station_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.WeatherStation'),
        ),
    ]
