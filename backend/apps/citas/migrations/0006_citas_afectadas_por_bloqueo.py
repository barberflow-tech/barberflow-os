# Generada con makemigrations (SCRUM-60). Aditiva y reversible: una FK y una
# fecha, ambas nulas, sin backfill. Depende de 0005 (Realtime, SCRUM-54).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0005_publicar_citas_realtime'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='affected_by_block',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_afectadas', to='citas.bloqueoagenda'),
        ),
        migrations.AddField(
            model_name='cita',
            name='block_notice_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
