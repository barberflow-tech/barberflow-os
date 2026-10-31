"""Concurrencia real de POST /api/v1/appointments contra PostgreSQL.

Usan django_db(transaction=True), el equivalente pytest de
TransactionTestCase: cada hilo abre su propia conexion y sus transacciones
hacen COMMIT de verdad. Con el django_db normal (TestCase) todo el test
corre dentro de una transaccion que nunca se confirma: los otros hilos no
verian los datos y el bloqueo nunca se disputaria.
"""

import threading
import time
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

URL = "/api/v1/appointments"
ESPERA_MAXIMA = 10


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def cliente(django_user_model, barberia):
    usuario = django_user_model.objects.create_user(username="cliente", password="x")
    Membresia.objects.create(user=usuario, barberia=barberia)
    return usuario


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
    )


@pytest.fixture
def inicio():
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


def sesiones_esperando_bloqueo() -> int:
    """Sesiones de la BD de test bloqueadas esperando un lock de fila."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pg_stat_activity "
            "WHERE datname = current_database() AND wait_event_type = 'Lock'"
        )
        return cursor.fetchone()[0]


@pytest.mark.django_db(transaction=True)
def test_dos_post_simultaneos_solo_uno_reserva(cliente, barbero, servicio, inicio):
    # Dado dos peticiones que reservan exactamente la misma franja a la vez
    payload = {
        "barber": barbero.pk,
        "service": servicio.pk,
        "start_at": inicio.isoformat(),
    }
    barrera = threading.Barrier(2)
    codigos: list[int] = []

    def reservar():
        api = APIClient()
        api.force_authenticate(user=cliente)
        try:
            barrera.wait()
            codigos.append(api.post(URL, payload, format="json").status_code)
        finally:
            connection.close()

    hilos = [threading.Thread(target=reservar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA_MAXIMA)

    # Entonces una obtiene 201, la otra 409, y solo existe una cita
    assert sorted(codigos) == [201, 409]
    assert Cita.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_bloqueo_pesimista_serializa_las_reservas(
    cliente, barbero, servicio, inicio, monkeypatch
):
    """Demuestra que es el SELECT ... FOR UPDATE el que evita el doble agendamiento.

    Ambas operaciones ejecutan el crear_cita real. La unica intervencion es
    pausar la operacion A justo despues de su INSERT, con la transaccion y el
    bloqueo aun abiertos, para observar que hace B mientras tanto.
    """
    insert_de_a_hecho = threading.Event()
    confirmar_a = threading.Event()
    save_original = Cita.save

    def save_con_pausa_en_a(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        if threading.current_thread().name == "A":
            insert_de_a_hecho.set()
            confirmar_a.wait(ESPERA_MAXIMA)

    monkeypatch.setattr(Cita, "save", save_con_pausa_en_a)

    resultados: dict[str, object] = {}

    def operacion(nombre):
        try:
            resultados[nombre] = services.crear_cita(
                cliente=cliente,
                barberia=barbero.barberia,
                barbero_id=barbero.pk,
                servicio_id=servicio.pk,
                inicio=inicio,
            )
        except Exception as exc:  # se inspecciona en el hilo principal
            resultados[nombre] = exc
        finally:
            connection.close()

    # Dado que A ya inserto su cita y mantiene el bloqueo del barbero
    hilo_a = threading.Thread(target=operacion, args=("A",), name="A")
    hilo_a.start()
    assert insert_de_a_hecho.wait(ESPERA_MAXIMA)

    # Cuando B intenta reservar la misma franja
    hilo_b = threading.Thread(target=operacion, args=("B",), name="B")
    hilo_b.start()

    # Entonces B queda bloqueada en PostgreSQL esperando el lock de A
    limite = time.monotonic() + ESPERA_MAXIMA
    while sesiones_esperando_bloqueo() == 0 and time.monotonic() < limite:
        time.sleep(0.05)
    assert sesiones_esperando_bloqueo() == 1
    assert hilo_b.is_alive()
    assert "B" not in resultados

    # Y al confirmar A, B revalida con el bloqueo, ve la cita de A y la rechaza
    confirmar_a.set()
    hilo_a.join(ESPERA_MAXIMA)
    hilo_b.join(ESPERA_MAXIMA)

    assert isinstance(resultados["A"], Cita)
    assert isinstance(resultados["B"], services.FranjaNoDisponibleError)
    # Lo detecto la revalidacion tras el bloqueo, no el ExclusionConstraint
    # (en ese caso la excepcion vendria encadenada a un IntegrityError).
    assert resultados["B"].__cause__ is None
    assert list(Cita.objects.values_list("pk", flat=True)) == [resultados["A"].pk]
