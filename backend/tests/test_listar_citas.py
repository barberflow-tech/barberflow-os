"""Listado de citas del cliente (HU-03): GET /api/v1/appointments.

Alimenta la pantalla de perfil, desde donde el cliente cancela o reprograma.
Solo devuelve las citas activas (PENDING o CONFIRMED) del propio usuario que
aun no terminaron.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

URL = "/api/v1/appointments"


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def cliente(django_user_model):
    return django_user_model.objects.create_user(username="cliente", password="x")


@pytest.fixture
def otro_cliente(django_user_model):
    return django_user_model.objects.create_user(username="otro", password="x")


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Juan")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
        description="Corte con tijera.",
    )


def api_de(usuario) -> APIClient:
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


def cita_de(cliente, barbero, servicio, *, en, estado=Cita.Estado.PENDING) -> Cita:
    inicio = timezone.now() + en
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
        status=estado,
        price=servicio.price,
    )


@pytest.mark.django_db
def test_exigir_sesion_para_listar_citas():
    response = APIClient().get(URL)

    assert response.status_code == 401


@pytest.mark.django_db
def test_listar_citas_activas_del_cliente_con_servicio_y_barbero(
    cliente, barbero, servicio
):
    cita = cita_de(cliente, barbero, servicio, en=timedelta(days=2))

    response = api_de(cliente).get(URL)

    assert response.status_code == 200
    assert len(response.data) == 1
    dato = response.data[0]
    assert dato["id"] == cita.pk
    assert dato["status"] == "PENDING"
    assert dato["price"] == "25000.00"
    assert dato["service"] == {
        "id": servicio.pk,
        "name": "Corte Clasico",
        "price": "25000.00",
        "duration_minutes": 30,
        "description": "Corte con tijera.",
    }
    assert dato["barber"] == {"id": barbero.pk, "name": "Juan", "working_days": []}


@pytest.mark.django_db
def test_listar_citas_confirmadas_tambien(cliente, barbero, servicio):
    cita_de(
        cliente, barbero, servicio, en=timedelta(days=1), estado=Cita.Estado.CONFIRMED
    )

    response = api_de(cliente).get(URL)

    assert [c["status"] for c in response.data] == ["CONFIRMED"]


@pytest.mark.django_db
def test_no_listar_citas_de_otro_cliente(cliente, otro_cliente, barbero, servicio):
    cita_de(otro_cliente, barbero, servicio, en=timedelta(days=2))

    response = api_de(cliente).get(URL)

    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado",
    [Cita.Estado.CANCELLED, Cita.Estado.COMPLETED, Cita.Estado.NO_SHOW],
)
def test_no_listar_citas_que_ya_no_estan_activas(cliente, barbero, servicio, estado):
    cita_de(cliente, barbero, servicio, en=timedelta(days=2), estado=estado)

    response = api_de(cliente).get(URL)

    assert response.data == []


@pytest.mark.django_db
def test_no_listar_citas_que_ya_terminaron(cliente, barbero, servicio):
    cita_de(cliente, barbero, servicio, en=-timedelta(days=1))

    response = api_de(cliente).get(URL)

    assert response.data == []


@pytest.mark.django_db
def test_listar_citas_de_la_mas_proxima_a_la_mas_lejana(cliente, barbero, servicio):
    lejana = cita_de(cliente, barbero, servicio, en=timedelta(days=5))
    proxima = cita_de(cliente, barbero, servicio, en=timedelta(days=1))
    media = cita_de(cliente, barbero, servicio, en=timedelta(days=3))

    response = api_de(cliente).get(URL)

    assert [c["id"] for c in response.data] == [proxima.pk, media.pk, lejana.pk]


@pytest.mark.django_db
def test_incluye_la_hora_limite_para_reprogramar(cliente, barbero, servicio):
    cita = cita_de(cliente, barbero, servicio, en=timedelta(days=2))

    dato = api_de(cliente).get(URL).data[0]

    # El ultimo instante en que aun se puede reprogramar: la antelacion antes del inicio
    assert dato["reschedule_deadline"] == cita.start_at - services.ANTICIPACION_MINIMA
    assert dato["min_notice_hours"] == services.ANTICIPACION_MINIMA_HORAS


@pytest.mark.django_db
def test_la_hora_limite_ya_paso_para_una_cita_dentro_de_la_antelacion(
    cliente, barbero, servicio
):
    # Una cita mas cercana que la antelacion minima: su limite ya quedo atras
    cita_de(cliente, barbero, servicio, en=services.ANTICIPACION_MINIMA / 2)

    dato = api_de(cliente).get(URL).data[0]

    assert dato["reschedule_deadline"] < timezone.now()


def test_la_antelacion_minima_viene_de_la_configuracion():
    from django.conf import settings

    assert services.ANTICIPACION_MINIMA == timedelta(
        hours=settings.CITAS_ANTICIPACION_MINIMA_HORAS
    )
    assert str(settings.CITAS_ANTICIPACION_MINIMA_HORAS) in (
        services.MENSAJE_REPROGRAMACION_TARDIA
    )


@pytest.mark.django_db
def test_el_barbero_de_la_cita_trae_los_dias_que_atiende(cliente, barbero, servicio):
    from datetime import time

    from apps.barberos.models import HorarioBarbero

    for dia in (3, 0, 5):
        HorarioBarbero.objects.create(
            barbero=barbero, weekday=dia, open_time=time(9), close_time=time(18)
        )
    HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=6,
        open_time=time(9),
        close_time=time(12),
        is_active=False,
    )
    cita_de(cliente, barbero, servicio, en=timedelta(days=2))

    dato = api_de(cliente).get(URL).data[0]

    assert dato["barber"]["working_days"] == [0, 3, 5]
