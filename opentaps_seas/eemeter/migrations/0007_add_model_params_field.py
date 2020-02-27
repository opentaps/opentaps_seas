from django.db import migrations
from django.contrib.postgres.fields import HStoreField


class Migration(migrations.Migration):

    dependencies = [
        ('eemeter', '0006_add_model_uom'),
    ]

    operations = [
        migrations.AddField(
            model_name='baselinemodel',
            name='model_params',
            field=HStoreField(verbose_name="Model Parameters", blank=True, null=True),
        ),
    ]
