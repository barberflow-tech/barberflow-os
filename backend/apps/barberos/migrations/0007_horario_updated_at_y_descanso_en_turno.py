"""HU-08 / SCRUM-72: auditoria del horario y descanso siempre dentro del turno.

1. `updated_at`: columna nueva con valor por defecto, sin bloqueo largo. Las
   filas existentes quedan con la fecha de esta migracion.
2. CHECK `horario_descanso_dentro_del_turno`: hasta ahora solo `clean()` lo
   validaba, y `clean()` no se ejecuta con `save()` ni con DRF. Se crea
   `NOT VALID` (no revisa las filas viejas mientras toma el bloqueo) y luego
   se valida, que es lo que falla si algun horario existente ya lo viola. La
   comparacion exige ademas `inicio + duracion > inicio`, porque `time +
   interval` da la vuelta a medianoche (23:30 + 60 min = 00:30).

Reversible: borra el CHECK y la columna.
"""

import django.utils.timezone
from django.db import migrations, models

TABLA = "barberos_horariobarbero"
RESTRICCION = "horario_descanso_dentro_del_turno"

AGREGAR_RESTRICCION = f"""
ALTER TABLE {TABLA} ADD CONSTRAINT {RESTRICCION} CHECK (
    break_start IS NULL
    OR (
        break_start >= open_time
        AND break_start + make_interval(mins => break_duration_minutes) <= close_time
        AND break_start + make_interval(mins => break_duration_minutes) > break_start
    )
) NOT VALID;
"""
VALIDAR_RESTRICCION = f"ALTER TABLE {TABLA} VALIDATE CONSTRAINT {RESTRICCION};"
QUITAR_RESTRICCION = f"ALTER TABLE {TABLA} DROP CONSTRAINT IF EXISTS {RESTRICCION};"


class Migration(migrations.Migration):

    dependencies = [
        ("barberos", "0006_servicios_por_barbero_y_nota"),
    ]

    operations = [
        migrations.AddField(
            model_name="horariobarbero",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql=[AGREGAR_RESTRICCION, VALIDAR_RESTRICCION],
            reverse_sql=QUITAR_RESTRICCION,
        ),
    ]
