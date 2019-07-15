# Generated by Django 2.1.10 on 2019-07-15 15:19

from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_rule_sets'),
    ]

    operations = [
        migrations.CreateModel(
            name='BacnetPrefix',
            fields=[
                ('prefix', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('config_file_name', models.CharField(max_length=255)),
                ('config_file', models.TextField()),
            ],
        ),
    ]
