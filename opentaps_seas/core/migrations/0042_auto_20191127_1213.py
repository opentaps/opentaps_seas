# Generated by Django 2.1.11 on 2019-11-27 18:13

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
        ('core', '0041_auto_20191127_1211'),
    ]

    operations = [
        migrations.RenameField(
            model_name='weatherhistory',
            old_name='id',
            new_name='weather_history_id',
        ),
    ]
