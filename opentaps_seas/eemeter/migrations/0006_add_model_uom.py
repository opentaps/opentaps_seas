from django.db import migrations, models
from django.db.models.deletion import DO_NOTHING


def set_uoms(apps, schema_editor):
    M = apps.get_model('eemeter', 'baselinemodel')
    for model in M.objects.all().iterator():
        model.uom_id = 'energy_kWh'
        model.save()


class Migration(migrations.Migration):

    dependencies = [
        ('eemeter', '0005_add_model_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='baselinemodel',
            name='uom',
            field=models.ForeignKey(on_delete=DO_NOTHING, related_name='+', to='core.UnitOfMeasure', null=True, blank=True),
        ),
        migrations.RunPython(set_uoms, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='baselinemodel',
            name='uom',
            field=models.ForeignKey(on_delete=DO_NOTHING, related_name='+', to='core.UnitOfMeasure', null=True, blank=True),
        ),
    ]
