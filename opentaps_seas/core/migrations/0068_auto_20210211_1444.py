# Generated by Django 2.2.13 on 2021-02-11 22:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_auto_20201016_1138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='utility',
            name='utility_id',
            field=models.CharField(max_length=100, primary_key=True, serialize=False, verbose_name='Utility Number'),
        ),
    ]
