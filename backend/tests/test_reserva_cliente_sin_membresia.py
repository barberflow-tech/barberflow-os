"""Un cliente (con o sin cuenta) reserva en la barbería del catálogo."""

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


# --- Visitante sin cuenta ----------------------------------------------------


@pytest.fixture(autouse=True)
def _limpiar_throttle():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _payload_visitante(barbero, servicio, **extra):
    inicio = timezone.now() + timedelta(days=2)
    datos = {
        "barber": barbero.pk,
        "service": servicio.pk,
        "start_at": inicio.isoformat(),
        "contact_name": "Laura Gómez",
        "contact_phone": "3001234567",
    }
    datos.update(extra)
    return datos


def test_visitante_ve_la_disponibilidad(barbero):
    respuesta = APIClient().get(
        DISPONIBILIDAD,
        {
            "barber": barbero.pk,
            "date": proximo_lunes().isoformat(),
            "slot_duration": 60,
        },
    )

    assert respuesta.status_code == 200
    assert len(respuesta.data["available_slots"]) == 10


def test_visitante_reserva_con_nombre_y_celular(barbero, servicio):
    respuesta = APIClient().post(
        CITAS, _payload_visitante(barbero, servicio), format="json"
    )

    assert respuesta.status_code == 201
    cita = Cita.objects.get()
    assert cita.client is None
    assert (cita.contact_name, cita.contact_phone) == ("Laura Gómez", "3001234567")
    assert cita.barberia == obtener_barberia_catalogo()


@pytest.mark.parametrize(
    "extra",
    [
        {"contact_name": ""},
        {"contact_phone": ""},
        {"contact_phone": "12345"},
        {"contact_name": "Al"},
    ],
)
def test_visitante_con_contacto_invalido_retorna_400(barbero, servicio, extra):
    respuesta = APIClient().post(
        CITAS, _payload_visitante(barbero, servicio, **extra), format="json"
    )

    assert respuesta.status_code == 400
    assert Cita.objects.count() == 0


def test_visitante_no_puede_tomar_una_franja_ocupada(barbero, servicio):
    datos = _payload_visitante(barbero, servicio)
    APIClient().post(CITAS, datos, format="json")

    respuesta = APIClient().post(CITAS, datos, format="json")

    assert respuesta.status_code == 409


def test_cliente_con_cuenta_no_necesita_contacto(make_user, barbero, servicio):
    datos = _payload_visitante(barbero, servicio)
    del datos["contact_name"], datos["contact_phone"]
    cliente = make_user("cliente")

    respuesta = api_de(cliente).post(CITAS, datos, format="json")

    assert respuesta.status_code == 201
    assert Cita.objects.get().client == cliente


def test_visitante_es_limitado_por_ip(barbero, servicio):
    api = APIClient()
    estados = [
        api.post(
            CITAS,
            _payload_visitante(barbero, servicio, contact_name="x"),
            format="json",
        ).status_code
        for _ in range(21)
    ]

    assert estados[-1] == 429
    assert 429 not in estados[:20]
