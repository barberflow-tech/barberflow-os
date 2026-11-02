"""SCRUM-42 / HU-01: bateria de concurrencia y solapamiento sobre POST /api/v1/appointments.

Complementa test_concurrencia_crear_cita.py (dos POST simultaneos y bloqueo
pesimista) con mas carga y con combinaciones de franjas y barberos que llegan
al mismo tiempo. Usa django_db(transaction=True) para que cada hilo abra su
propia conexion y sus transacciones hagan COMMIT real.
"""

import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

URL = "/api/v1/appointments"
ESPERA_MAXIMA = 20

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def make_cliente(django_user_model, barberia):
    def _make_cliente(username):
        usuario = django_user_model.objects.create_user(username=username, password="x")
        Membresia.objects.create(user=usuario, barberia=barberia)
        return usuario

    return _make_cliente


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Juan")


@pytest.fixture
def otro_barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Pedro")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def inicio():
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


def _reservar_en_paralelo(reservas):
    """Lanza todas las reservas a la vez; reservas = [(usuario, payload), ...].

    Devuelve los codigos HTTP en el mismo orden de la lista.
    """
    barrera = threading.Barrier(len(reservas))
    codigos = [None] * len(reservas)

    def reservar(indice, usuario, payload):
        api = APIClient()
        api.force_authenticate(user=usuario)
        try:
            barrera.wait()
            codigos[indice] = api.post(URL, payload, format="json").status_code
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=reservar, args=(i, usuario, payload))
        for i, (usuario, payload) in enumerate(reservas)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA_MAXIMA)
    return codigos


def _payload(barbero, servicio, start_at):
    return {
        "barber": barbero.pk,
        "service": servicio.pk,
        "start_at": start_at.isoformat(),
    }


def test_conc02_diez_clientes_por_el_mismo_slot_solo_uno_reserva(
    make_cliente, barbero, servicio, inicio
):
    # Dado 10 clientes que piden el mismo barbero y la misma hora a la vez
    reservas = [
        (make_cliente(f"cliente{i}"), _payload(barbero, servicio, inicio))
        for i in range(10)
    ]

    # Cuando las 10 peticiones llegan en paralelo
    codigos = _reservar_en_paralelo(reservas)

    # Entonces solo una queda agendada y las otras 9 reciben 409
    assert sorted(codigos) == [201] + [409] * 9
    assert Cita.objects.count() == 1


def test_conc03_solapes_parciales_simultaneos_solo_uno_reserva(
    make_cliente, barbero, servicio, inicio
):
    # Dado tres peticiones de 30 min que se cruzan entre si: 15:00, 15:10 y 15:20
    reservas = [
        (make_cliente(f"cliente{i}"), _payload(barbero, servicio, inicio + offset))
        for i, offset in enumerate(
            [timedelta(0), timedelta(minutes=10), timedelta(minutes=20)]
        )
    ]

    codigos = _reservar_en_paralelo(reservas)

    # Entonces solo una gana y en la agenda no queda ningun cruce
    assert codigos.count(201) == 1
    assert codigos.count(409) == 2
    assert Cita.objects.count() == 1


def test_conc04_franjas_contiguas_simultaneas_se_aceptan_todas(
    make_cliente, barbero, servicio, inicio
):
    # Dado tres franjas seguidas sin cruce (15:00, 15:30 y 16:00) pedidas a la vez
    reservas = [
        (
            make_cliente(f"cliente{i}"),
            _payload(barbero, servicio, inicio + timedelta(minutes=30 * i)),
        )
        for i in range(3)
    ]

    codigos = _reservar_en_paralelo(reservas)

    # Entonces todas se agendan: el borde de una franja no cuenta como cruce
    assert codigos == [201, 201, 201]
    assert Cita.objects.filter(barber=barbero).count() == 3


def test_conc05_mismo_slot_con_barberos_distintos_se_aceptan_ambas(
    make_cliente, barbero, otro_barbero, servicio, inicio
):
    # Dado dos clientes que piden la misma hora con barberos distintos a la vez
    reservas = [
        (make_cliente("cliente_a"), _payload(barbero, servicio, inicio)),
        (make_cliente("cliente_b"), _payload(otro_barbero, servicio, inicio)),
    ]

    codigos = _reservar_en_paralelo(reservas)

    # Entonces el bloqueo de un barbero no frena al otro: ambas se agendan
    assert codigos == [201, 201]
    assert Cita.objects.count() == 2


def test_conc05b_carga_mixta_un_ganador_por_barbero(
    make_cliente, barbero, otro_barbero, servicio, inicio
):
    # Dado 5 clientes por barbero pidiendo la misma hora, todos a la vez
    reservas = [
        (make_cliente(f"cliente_{b.pk}_{i}"), _payload(b, servicio, inicio))
        for b in (barbero, otro_barbero)
        for i in range(5)
    ]

    codigos = _reservar_en_paralelo(reservas)

    # Entonces queda exactamente una cita por barbero
    assert codigos.count(201) == 2
    assert codigos.count(409) == 8
    assert Cita.objects.filter(barber=barbero).count() == 1
    assert Cita.objects.filter(barber=otro_barbero).count() == 1


def test_conc_mismo_cliente_doble_click_crea_una_sola_cita(
    make_cliente, barbero, servicio, inicio
):
    # Dado un cliente que envia la misma reserva dos veces a la vez (doble click)
    cliente = make_cliente("cliente")
    payload = _payload(barbero, servicio, inicio)

    codigos = _reservar_en_paralelo([(cliente, payload), (cliente, payload)])

    # Entonces solo se crea una cita
    assert sorted(codigos) == [201, 409]
    assert Cita.objects.filter(client=cliente).count() == 1
