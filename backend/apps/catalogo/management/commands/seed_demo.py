"""Datos de demostración para la base local: python manage.py seed_demo.

Es idempotente: se puede ejecutar varias veces sin duplicar nada. Usa la misma
barbería que el catálogo (`apps.catalogo.context`), de modo que los servicios
sembrados son los que devuelve GET /api/v1/services.
"""

from datetime import time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.usuarios.models import PerfilUsuario, Rol

SERVICIOS = [
    ("Corte clásico", "35000", 40, "Corte a tijera o máquina, con acabado limpio."),
    (
        "Corte + barba premium",
        "55000",
        60,
        "El ritual completo: corte, barba y toalla caliente.",
    ),
    ("Perfilado de barba", "25000", 30, "Líneas definidas y volumen a tu medida."),
    ("Corte infantil", "30000", 30, "Atención paciente para los más pequeños."),
]
BARBEROS = ["Thiago", "Andrés", "Nicolás"]
# Lunes a sábado, 09:00-19:00, con descanso de 60 min a las 13:00 (domingo cerrado).
DIAS_LABORALES = range(0, 6)

# Barbero de la lista BARBEROS que usa la cuenta barbero@barberflow.test para entrar.
BARBERO_CON_CUENTA = "Thiago"

USUARIOS = [
    # (correo, rol, es_staff, tiene_barbería)
    ("admin@barberflow.test", Rol.ADMIN, True, True),
    ("barbero@barberflow.test", Rol.BARBERO, False, True),
    ("cliente@barberflow.test", Rol.CLIENTE, False, False),
]


class Command(BaseCommand):
    help = "Crea barbería, servicios, barberos, horarios y usuarios de demostración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Demo12345!",
            help="Contraseña de los usuarios de demostración.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo solo se puede ejecutar con DEBUG=True.")

        barberia = obtener_barberia_catalogo()

        for nombre, precio, minutos, descripcion in SERVICIOS:
            Servicio.objects.update_or_create(
                barberia=barberia,
                name=nombre,
                defaults={
                    "price": Decimal(precio),
                    "duration_minutes": minutos,
                    "description": descripcion,
                    "is_active": True,
                },
            )

        barberos = {}
        for nombre in BARBEROS:
            barbero, _ = Barbero.objects.get_or_create(
                barberia=barberia, name=nombre, defaults={"is_active": True}
            )
            barberos[nombre] = barbero
            for dia in DIAS_LABORALES:
                HorarioBarbero.objects.update_or_create(
                    barbero=barbero,
                    weekday=dia,
                    defaults={
                        "open_time": time(9, 0),
                        "close_time": time(19, 0),
                        "break_start": time(13, 0),
                        "break_duration_minutes": 60,
                        "is_active": True,
                    },
                )

        User = get_user_model()
        for correo, rol, es_staff, con_barberia in USUARIOS:
            usuario, _ = User.objects.get_or_create(
                username=correo, defaults={"email": correo}
            )
            usuario.email = correo
            usuario.is_staff = es_staff
            usuario.set_password(options["password"])
            usuario.save()
            # La señal ya creó el perfil como cliente; aquí se fija el rol de la demo.
            PerfilUsuario.objects.update_or_create(user=usuario, defaults={"role": rol})
            if rol == Rol.BARBERO:
                # El portafolio (POST /barbers/me/portfolio) resuelve al barbero
                # por esta vinculación cuenta -> Barbero.
                Barbero.objects.filter(user=usuario).update(user=None)
                barbero = barberos[BARBERO_CON_CUENTA]
                barbero.user = usuario
                barbero.save(update_fields=["user", "updated_at"])
            if con_barberia:
                Membresia.objects.get_or_create(
                    user=usuario, defaults={"barberia": barberia}
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo lista en «{barberia.name}»: {len(SERVICIOS)} servicios, "
                f"{len(BARBEROS)} barberos y {len(USUARIOS)} usuarios "
                f"({', '.join(u[0] for u in USUARIOS)})."
            )
        )
