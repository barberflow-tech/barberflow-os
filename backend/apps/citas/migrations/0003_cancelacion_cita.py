# Escrita a mano con el formato de makemigrations (SCRUM-52). Verificar con
# `python manage.py makemigrations --check --dry-run`: no debe detectar cambios.
#
# Aditiva y reversible: dos columnas nuevas (una nullable y otra con default
# constante, instantaneas en PostgreSQL 11+) y un CHECK que ya cumplen todas
# las filas existentes (late_cancellation nace en False). Sin backfill.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0002_cita_visitante"),
    ]

    operations = [
        migrations.AddField(
            model_name="cita",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cita",
            name="late_cancellation",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="cita",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("late_cancellation", False),
                    ("status", "CANCELLED"),
                    _connector="OR",
                ),
                name="cita_tardia_solo_si_cancelada",
            ),
        ),
    ]
