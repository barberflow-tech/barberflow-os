"""Un cliente (registrado sin barbería) reserva en la barbería del catálogo."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

pytestmark = pytest.mark.django_db

CITAS = "/api/v1/appointments"
DISPONIBILIDAD = "/api/v1/availability"


@pytest.fixture
def barberia():
    return obtener_barberia_catalogo()


@pytest.fixture
def barbero(barberia):
    barbero = Barbero.objects.create(barberia=barberia, name="Thiago")
    for dia in range(6):
        HorarioBarbero.objects.create(
            barbero=barbero, weekday=dia, open_time=time(9), close_time=time(19)
        )
    return barbero


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte",
        price=Decimal("35000.00"),
        duration_minutes=40,
    )


def api_de(usuario):
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


def proximo_lunes() -> date:
    hoy = date.today()
    return hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)


def test_cliente_sin_membresia_ve_la_disponibilidad(make_user, barbero):
    # Dado un cliente recién registrado (sin membresía)
    cliente = make_user("cliente")

    # Cuando consulta la disponibilidad de un barbero de la barbería del catálogo
    respuesta = api_de(cliente).get(
        DISPONIBILIDAD,
        {
            "barber": barbero.pk,
            "date": proximo_lunes().isoformat(),
            "slot_duration": 60,
        },
    )

    # Entonces recibe las franjas de la jornada (09:00-19:00 en bloques de 60 min)
    assert respuesta.status_code == 200
    assert len(respuesta.json()["available_slots"]) == 10


def test_cliente_sin_membresia_puede_crear_una_cita(make_user, barbero, servicio):
    cliente = make_user("cliente")
    inicio = (timezone.now() + timedelta(days=2)).replace(
        minute=0, second=0, microsecond=0
    )

    respuesta = api_de(cliente).post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": inicio.isoformat()},
        format="json",
    )

    assert respuesta.status_code == 201
    cita = Cita.objects.get()
    assert cita.client == cliente
    assert cita.price == Decimal("35000.00")
    assert cita.end_at - cita.start_at == timedelta(minutes=40)


@pytest.mark.parametrize("rol", ["barbero", "admin"])
def test_personal_sin_membresia_sigue_sin_poder_reservar(make_user, barbero, rol):
    # Solo el cliente tiene el respaldo: el personal necesita su membresía.
    respuesta = api_de(make_user(rol)).get(
        DISPONIBILIDAD,
        {
            "barber": barbero.pk,
            "date": proximo_lunes().isoformat(),
            "slot_duration": 60,
        },
    )

    assert respuesta.status_code == 403
