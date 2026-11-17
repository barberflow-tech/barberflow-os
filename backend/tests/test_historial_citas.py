"""Citas que ya no están activas del cliente (HU-03): GET /api/v1/appointments/history.

Alimenta el apartado «Canceladas» del perfil: las que el cliente canceló y las
que vencieron porque la hora pasó sin que se atendieran.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

URL = "/api/v1/appointments/history"


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


def cita_de(cliente, barbero, servicio, *, en, estado=Cita.Estado.PENDING, **extra):
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
        **extra,
    )


@pytest.mark.django_db
def test_exigir_sesion_para_ver_el_historial():
    assert APIClient().get(URL).status_code == 401


@pytest.mark.django_db
def test_una_cita_cancelada_por_el_cliente_aparece_como_cancelada(
    cliente, barbero, servicio
):
    cita = cita_de(
        cliente,
        barbero,
        servicio,
        en=timedelta(days=3),
        estado=Cita.Estado.CANCELLED,
        cancelled_at=timezone.now(),
        late_cancellation=True,
    )

    response = api_de(cliente).get(URL)

    assert response.status_code == 200
    assert len(response.data) == 1
    dato = response.data[0]
    assert dato["id"] == cita.pk
    assert dato["outcome"] == "cancelled"
    assert dato["status"] == "CANCELLED"
    assert dato["late_cancellation"] is True
    assert dato["cancelled_at"] is not None
    assert dato["service"]["name"] == "Corte Clasico"
    assert dato["barber"]["name"] == "Juan"


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [Cita.Estado.PENDING, Cita.Estado.CONFIRMED])
def test_una_cita_activa_cuya_hora_ya_paso_aparece_como_vencida(
    cliente, barbero, servicio, estado
):
    cita = cita_de(cliente, barbero, servicio, en=timedelta(days=-2), estado=estado)

    response = api_de(cliente).get(URL)

    assert [c["id"] for c in response.data] == [cita.pk]
    assert response.data[0]["outcome"] == "expired"


@pytest.mark.django_db
def test_una_cita_marcada_como_no_asistida_aparece_como_vencida(
    cliente, barbero, servicio
):
    cita_de(
        cliente, barbero, servicio, en=timedelta(days=-1), estado=Cita.Estado.NO_SHOW
    )

    response = api_de(cliente).get(URL)

    assert response.data[0]["outcome"] == "expired"


@pytest.mark.django_db
def test_no_incluye_citas_activas_futuras_en_curso_ni_completadas(
    cliente, barbero, servicio
):
    cita_de(cliente, barbero, servicio, en=timedelta(days=2))  # futura
    cita_de(cliente, barbero, servicio, en=timedelta(minutes=-10))  # en curso
    cita_de(
        cliente, barbero, servicio, en=timedelta(days=-4), estado=Cita.Estado.COMPLETED
    )

    response = api_de(cliente).get(URL)

    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_solo_devuelve_las_citas_del_propio_cliente(
    cliente, otro_cliente, barbero, servicio
):
    cita_de(
        otro_cliente,
        barbero,
        servicio,
        en=timedelta(days=3),
        estado=Cita.Estado.CANCELLED,
        cancelled_at=timezone.now(),
    )

    response = api_de(cliente).get(URL)

    assert response.data == []


@pytest.mark.django_db
def test_ordena_de_la_mas_reciente_a_la_mas_antigua(cliente, barbero, servicio):
    antigua = cita_de(cliente, barbero, servicio, en=timedelta(days=-9))
    reciente = cita_de(
        cliente,
        barbero,
        servicio,
        en=timedelta(days=5),
        estado=Cita.Estado.CANCELLED,
        cancelled_at=timezone.now(),
    )
    media = cita_de(cliente, barbero, servicio, en=timedelta(days=-3))

    response = api_de(cliente).get(URL)

    assert [c["id"] for c in response.data] == [reciente.pk, media.pk, antigua.pk]
