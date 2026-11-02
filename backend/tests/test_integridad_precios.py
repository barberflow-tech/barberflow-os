"""SCRUM-39 / HU-10: un cambio de precio en el catalogo no altera citas ya agendadas.

La cita guarda una copia del precio del servicio al reservarse (Cita.price), de
modo que el historico no depende del valor actual del catalogo.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

URL = "/api/v1/appointments"
PRECIO_ORIGINAL = Decimal("20000.00")
PRECIO_NUEVO = Decimal("25000.00")

pytestmark = pytest.mark.django_db


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def cliente(django_user_model, barberia):
    usuario = django_user_model.objects.create_user(username="cliente", password="x")
    Membresia.objects.create(user=usuario, barberia=barberia)
    return usuario


@pytest.fixture
def api(cliente):
    api = APIClient()
    api.force_authenticate(user=cliente)
    return api


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Juan")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=PRECIO_ORIGINAL,
        duration_minutes=30,
    )


@pytest.fixture
def inicio():
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


def _reservar(api, barbero, servicio, inicio, **extra):
    payload = {
        "barber": barbero.pk,
        "service": servicio.pk,
        "start_at": inicio.isoformat(),
        **extra,
    }
    return api.post(URL, payload, format="json")


def test_pre01_cita_conserva_el_precio_original_tras_subir_el_precio(
    api, barbero, servicio, inicio
):
    # Dado un servicio de $20.000 con una cita ya agendada
    reserva = _reservar(api, barbero, servicio, inicio)
    assert reserva.status_code == 201

    # Cuando el precio del servicio sube a $25.000
    servicio.price = PRECIO_NUEVO
    servicio.save()

    # Entonces la cita mantiene el precio original de $20.000
    cita = Cita.objects.get(pk=reserva.json()["id"])
    assert cita.price == PRECIO_ORIGINAL
    assert Decimal(reserva.json()["price"]) == PRECIO_ORIGINAL


def test_pre02_cita_nueva_toma_el_precio_vigente(api, barbero, servicio, inicio):
    # Dado un servicio cuyo precio ya cambio a $25.000
    servicio.price = PRECIO_NUEVO
    servicio.save()

    # Cuando se agenda una cita nueva
    reserva = _reservar(api, barbero, servicio, inicio)

    # Entonces la cita toma el precio vigente
    assert reserva.status_code == 201
    assert Cita.objects.get(pk=reserva.json()["id"]).price == PRECIO_NUEVO


def test_pre02b_citas_antes_y_despues_del_cambio_conservan_cada_una_su_precio(
    api, barbero, servicio, inicio
):
    antes = _reservar(api, barbero, servicio, inicio)
    servicio.price = PRECIO_NUEVO
    servicio.save()
    despues = _reservar(api, barbero, servicio, inicio + timedelta(hours=1))

    assert Cita.objects.get(pk=antes.json()["id"]).price == PRECIO_ORIGINAL
    assert Cita.objects.get(pk=despues.json()["id"]).price == PRECIO_NUEVO


def test_pre02c_el_cliente_no_puede_fijar_el_precio_de_la_cita(
    api, barbero, servicio, inicio
):
    # Dado un cliente que envia un precio propio en la reserva
    reserva = _reservar(api, barbero, servicio, inicio, price="1.00")

    # Entonces el precio se toma del catalogo, no del payload
    assert reserva.status_code == 201
    assert Cita.objects.get(pk=reserva.json()["id"]).price == PRECIO_ORIGINAL


def test_pre03_desactivar_servicio_no_afecta_citas_existentes(
    api, barbero, servicio, inicio
):
    # Dado un servicio con una cita agendada
    reserva = _reservar(api, barbero, servicio, inicio)

    # Cuando el servicio se desactiva
    servicio.is_active = False
    servicio.save()

    # Entonces la cita sigue existiendo con su precio
    cita = Cita.objects.get(pk=reserva.json()["id"])
    assert cita.price == PRECIO_ORIGINAL
    # Y no se pueden agendar citas nuevas con ese servicio
    nueva = _reservar(api, barbero, servicio, inicio + timedelta(hours=1))
    assert nueva.status_code == 400


def test_pre04_no_se_puede_borrar_un_servicio_con_citas(api, barbero, servicio, inicio):
    # Dado un servicio con una cita agendada
    reserva = _reservar(api, barbero, servicio, inicio)

    # Cuando se intenta borrar el servicio
    with pytest.raises(ProtectedError):
        servicio.delete()

    # Entonces la cita no se borra en cascada
    assert Cita.objects.filter(pk=reserva.json()["id"]).exists()


def test_pre05_servicio_con_precio_negativo_es_rechazado_por_la_bd(barberia):
    with pytest.raises(IntegrityError), transaction.atomic():
        Servicio.objects.create(
            barberia=barberia,
            name="Precio invalido",
            price=Decimal("-1.00"),
            duration_minutes=30,
        )


def test_pre05b_servicio_con_precio_cero_es_valido(barberia):
    # Un servicio de cortesia (precio 0) es valido: la restriccion es price >= 0
    servicio = Servicio.objects.create(
        barberia=barberia, name="Cortesia", price=Decimal("0"), duration_minutes=15
    )

    assert servicio.price == Decimal("0")


def test_pre05c_cita_con_precio_negativo_es_rechazada_por_la_bd(
    cliente, barberia, barbero, servicio, inicio
):
    with pytest.raises(IntegrityError), transaction.atomic():
        Cita.objects.create(
            barberia=barberia,
            client=cliente,
            barber=barbero,
            service=servicio,
            start_at=inicio,
            end_at=inicio + timedelta(minutes=30),
            price=Decimal("-1.00"),
        )


def test_pre06_servicio_con_duracion_cero_es_rechazado_por_la_bd(barberia):
    with pytest.raises(IntegrityError), transaction.atomic():
        Servicio.objects.create(
            barberia=barberia,
            name="Duracion invalida",
            price=PRECIO_ORIGINAL,
            duration_minutes=0,
        )
