import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("barberos", "0004_barbero_user"),
        ("citas", "0002_cita_visitante"),
    ]

    operations = [
        migrations.CreateModel(
            name="BloqueoAgenda",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("reason", models.CharField(max_length=255)),
                (
                    "barber",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bloqueos_agenda",
                        to="barberos.barbero",
                    ),
                ),
            ],
            options={
                "ordering": ["start_at", "pk"],
                "indexes": [
                    models.Index(
                        fields=["barber", "start_at"],
                        name="bloqueo_barbero_inicio_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(end_at__gt=models.F("start_at")),
                        name="bloqueo_fin_posterior_inicio",
                    ),
                ],
            },
        ),
        # Los bloqueos se gestionan por Django y no por la API de Supabase.
        migrations.RunSQL(
            "ALTER TABLE citas_bloqueoagenda ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE citas_bloqueoagenda DISABLE ROW LEVEL SECURITY",
        ),
    ]
