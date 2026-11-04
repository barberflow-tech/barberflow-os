from django.conf import settings
from django.db import migrations


def crear_perfiles_faltantes(apps, schema_editor):
    """Da perfil a los usuarios previos a SUB-06-A.

    Superusuarios -> admin; todos los demas -> cliente (el menor privilegio).
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PerfilUsuario = apps.get_model("usuarios", "PerfilUsuario")

    con_perfil = PerfilUsuario.objects.values("user_id")
    PerfilUsuario.objects.bulk_create(
        [
            PerfilUsuario(user_id=user.pk, role="admin" if user.is_superuser else "cliente")
            for user in User.objects.exclude(pk__in=con_perfil).only("pk", "is_superuser")
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        # Reversible: al deshacer no hay nada que borrar aqui (0001 elimina la tabla).
        migrations.RunPython(crear_perfiles_faltantes, migrations.RunPython.noop),
    ]
