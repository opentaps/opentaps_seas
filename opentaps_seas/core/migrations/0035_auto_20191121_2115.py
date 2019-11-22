# Generated by Django 2.1.11 on 2019-11-22 03:15

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
        ('core', '0034_auto_20191121_2105'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeatherHistory',
            fields=[
                ('Weather_history_id', models.CharField(max_length=255, primary_key=True, serialize=False, verbose_name='Weather History ID')),
                ('as_of_datetime', models.DateTimeField(default=django.utils.timezone.now, verbose_name='History Date')),
                ('temp_c', models.FloatField(null=True)),
                ('temp_f', models.FloatField(null=True)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('created_datetime', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created Date')),
            ],
            options={
                'db_table': 'core_weather_history',
            },
        ),
        migrations.AlterField(
            model_name='weatherstation',
            name='source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='weatherhistory',
            name='Weather_station_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.WeatherStation'),
        ),
        migrations.AddField(
            model_name='weatherhistory',
            name='created_by_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]
