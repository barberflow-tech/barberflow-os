"""Concurrencia real de la cancelacion de citas contra PostgreSQL (SCRUM-52).

Usan django_db(transaction=True): cada hilo abre su propia conexion y sus
transacciones hacen COMMIT de verdad (ver test_concurrencia_crear_cita.py).
"""

import threading
import time
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

ESPERA_MAXIMA = 10


@pytest.fixture
def propietario(django_user_model):
    return django_user_model.objects.create_user(username="propietario", password="x")


@pytest.fixture
def cita(propietario):
    barberia = Barberia.objects.create(name="Barberia Centro")
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    servicio = Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )
    inicio = timezone.now() + timedelta(days=2)
    return Cita.objects.create(
        barberia=barberia,
        client=propietario,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=servicio.price,
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
def test_dos_cancelaciones_simultaneas_solo_una_se_aplica(propietario, cita):
    # Dado dos peticiones que cancelan la misma cita a la vez (doble clic)
    barrera = threading.Barrier(2)
    resultados: list[str] = []

    def cancelar():
        try:
            barrera.wait()
            try:
                services.cancelar_cita(cita_id=cita.pk, usuario=propietario)
                resultados.append("cancelada")
            except services.EstadoCitaInvalidoError:
                resultados.append("rechazada")
        finally:
            connection.close()

    hilos = [threading.Thread(target=cancelar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA_MAXIMA)

    # Entonces una cancela y la otra se rechaza, sin pisar la primera
    assert sorted(resultados) == ["cancelada", "rechazada"]
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.CANCELLED
    assert cita.cancelled_at is not None


@pytest.mark.django_db(transaction=True)
def test_bloqueo_de_la_cita_serializa_las_cancelaciones(propietario, cita, monkeypatch):
    """Demuestra que es el SELECT ... FOR UPDATE sobre la cita el que serializa.

    Ambas operaciones ejecutan el cancelar_cita real. La unica intervencion es
    pausar la operacion A justo despues de su UPDATE, con la transaccion y el
    bloqueo aun abiertos, para observar que hace B mientras tanto.
    """
    update_de_a_hecho = threading.Event()
    confirmar_a = threading.Event()
    save_original = Cita.save

    def save_con_pausa_en_a(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        if threading.current_thread().name == "A":
            update_de_a_hecho.set()
            confirmar_a.wait(ESPERA_MAXIMA)

    monkeypatch.setattr(Cita, "save", save_con_pausa_en_a)

    resultados: dict[str, object] = {}

    def operacion(nombre):
        try:
            resultados[nombre] = services.cancelar_cita(
                cita_id=cita.pk, usuario=propietario
            )
        except services.CitaError as exc:  # se inspecciona en el hilo principal
            resultados[nombre] = exc
        finally:
            connection.close()

    # Dado que A ya actualizo la cita y mantiene su bloqueo
    hilo_a = threading.Thread(target=operacion, args=("A",), name="A")
    hilo_a.start()
    assert update_de_a_hecho.wait(ESPERA_MAXIMA)

    # Cuando B intenta cancelar la misma cita
    hilo_b = threading.Thread(target=operacion, args=("B",), name="B")
    hilo_b.start()

    # Entonces B queda bloqueada en PostgreSQL esperando el lock de A
    limite = time.monotonic() + ESPERA_MAXIMA
    while sesiones_esperando_bloqueo() == 0 and time.monotonic() < limite:
        time.sleep(0.05)
    assert sesiones_esperando_bloqueo() == 1
    assert hilo_b.is_alive()
    assert "B" not in resultados

    # Y al confirmar A, B relee la cita ya cancelada y la rechaza
    confirmar_a.set()
    hilo_a.join(ESPERA_MAXIMA)
    hilo_b.join(ESPERA_MAXIMA)

    assert isinstance(resultados["A"], Cita)
    assert isinstance(resultados["B"], services.EstadoCitaInvalidoError)
    cita.refresh_from_db()
    assert cita.cancelled_at == resultados["A"].cancelled_at
