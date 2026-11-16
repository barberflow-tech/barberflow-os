"""Concurrencia real de la reprogramacion de citas contra PostgreSQL (SCRUM-52).

Usan django_db(transaction=True): cada hilo abre su propia conexion y sus
transacciones hacen COMMIT de verdad (ver test_concurrencia_crear_cita.py).
Cada escenario ejecuta los servicios reales; solo se pausa un hilo, cuando
hace falta observar que hace el otro mientras tanto.
"""

import threading
import time
from datetime import datetime, timedelta
from datetime import time as hora_del_dia
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

ESPERA_MAXIMA = 10


def hora_local(dias: int, hora: int, minuto: int = 0) -> datetime:
    """Hora de pared en la barberia, `dias` despues de hoy (siempre con zona)."""
    hoy = timezone.now().astimezone(services.ZONA_HORARIA_BARBERIA)
    dia = (hoy + timedelta(days=dias)).date()
    return datetime.combine(
        dia, hora_del_dia(hora, minuto), tzinfo=services.ZONA_HORARIA_BARBERIA
    )


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def barbero(barberia):
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=dia,
            open_time=hora_del_dia(9, 0),
            close_time=hora_del_dia(17, 0),
        )
    return barbero


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def usuario_a(django_user_model):
    return django_user_model.objects.create_user(username="usuario_a", password="x")


@pytest.fixture
def usuario_b(django_user_model):
    return django_user_model.objects.create_user(username="usuario_b", password="x")


@pytest.fixture
def cita_a(usuario_a, barbero, servicio):
    return crear_cita(usuario_a, barbero, servicio, hora_local(2, 10))


@pytest.fixture
def cita_b(usuario_b, barbero, servicio):
    return crear_cita(usuario_b, barbero, servicio, hora_local(2, 11))


@pytest.fixture
def franja_objetivo():
    """La franja que ambos hilos se disputan: en 3 dias a las 14:00."""
    return hora_local(3, 14)


def crear_cita(cliente, barbero, servicio, inicio) -> Cita:
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
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


def ejecutar_a_la_vez(*operaciones) -> list[object]:
    """Corre cada operacion en su hilo, soltadas a la vez; devuelve resultados.

    Una excepcion de negocio (CitaError) se devuelve como resultado para
    inspeccionarla en el hilo principal. Cualquier otra deja el resultado en
    None, y los assert de cada prueba la delatan.
    """
    barrera = threading.Barrier(len(operaciones))
    resultados: list[object] = [None] * len(operaciones)

    def correr(indice, operacion):
        try:
            barrera.wait()
            resultados[indice] = operacion()
        except services.CitaError as exc:
            resultados[indice] = exc
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=correr, args=(i, op))
        for i, op in enumerate(operaciones)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA_MAXIMA)
    return resultados


@pytest.mark.django_db(transaction=True)
def test_dos_reprogramaciones_a_la_misma_franja_solo_una_se_aplica(
    usuario_a, usuario_b, cita_a, cita_b, barbero, franja_objetivo
):
    # Dado dos clientes que mueven su cita a la misma franja libre, a la vez
    resultados = ejecutar_a_la_vez(
        lambda: services.reprogramar_cita(
            cita_id=cita_a.pk, usuario=usuario_a, nuevo_inicio=franja_objetivo
        ),
        lambda: services.reprogramar_cita(
            cita_id=cita_b.pk, usuario=usuario_b, nuevo_inicio=franja_objetivo
        ),
    )

    # Entonces una gana y la otra recibe franja no disponible
    exitos = [r for r in resultados if isinstance(r, Cita)]
    rechazos = [
        r for r in resultados if isinstance(r, services.FranjaNoDisponibleError)
    ]
    assert len(exitos) == 1
    assert len(rechazos) == 1
    # ...y solo hay una cita en esa franja
    fin = franja_objetivo + timedelta(minutes=30)
    assert Cita.objects.solapadas(barbero, franja_objetivo, fin).count() == 1


@pytest.mark.django_db(transaction=True)
def test_reprogramar_y_reservar_la_misma_franja_solo_uno_la_obtiene(
    usuario_a, usuario_b, cita_a, barbero, servicio, franja_objetivo
):
    # Dado una reprogramacion y una reserva nueva (HU-02) sobre la misma franja
    resultados = ejecutar_a_la_vez(
        lambda: services.reprogramar_cita(
            cita_id=cita_a.pk, usuario=usuario_a, nuevo_inicio=franja_objetivo
        ),
        lambda: services.crear_cita(
            cliente=usuario_b,
            barberia=barbero.barberia,
            barbero_id=barbero.pk,
            servicio_id=servicio.pk,
            inicio=franja_objetivo,
        ),
    )

    # Entonces comparten el bloqueo del barbero: una se aplica y la otra falla
    exitos = [r for r in resultados if isinstance(r, Cita)]
    rechazos = [
        r for r in resultados if isinstance(r, services.FranjaNoDisponibleError)
    ]
    assert len(exitos) == 1
    assert len(rechazos) == 1
    fin = franja_objetivo + timedelta(minutes=30)
    assert Cita.objects.solapadas(barbero, franja_objetivo, fin).count() == 1


@pytest.mark.django_db(transaction=True)
def test_cancelar_y_reprogramar_la_misma_cita_termina_cancelada(
    usuario_a, cita_a, franja_objetivo
):
    # Dado una cancelacion y una reprogramacion de la misma cita, a la vez
    resultados = ejecutar_a_la_vez(
        lambda: services.cancelar_cita(cita_id=cita_a.pk, usuario=usuario_a),
        lambda: services.reprogramar_cita(
            cita_id=cita_a.pk, usuario=usuario_a, nuevo_inicio=franja_objetivo
        ),
    )

    # Entonces ninguna deja la cita a medias: termina CANCELLED en cualquier
    # orden, y si la cancelacion gano primero, la reprogramacion fue rechazada.
    cita_a.refresh_from_db()
    assert cita_a.status == Cita.Estado.CANCELLED
    assert cita_a.cancelled_at is not None
    cancelacion, reprogramacion = resultados
    assert isinstance(cancelacion, Cita)
    assert isinstance(reprogramacion, (Cita, services.EstadoCitaInvalidoError))
    if isinstance(reprogramacion, services.EstadoCitaInvalidoError):
        assert cita_a.start_at == hora_local(2, 10)


@pytest.mark.django_db(transaction=True)
def test_bloqueo_del_barbero_serializa_las_reprogramaciones(
    usuario_a, usuario_b, cita_a, cita_b, franja_objetivo, monkeypatch
):
    """Demuestra que es el SELECT ... FOR UPDATE del barbero el que serializa.

    Ambas operaciones ejecutan el reprogramar_cita real. La unica intervencion
    es pausar la operacion A justo despues de su UPDATE, con la transaccion y
    los bloqueos aun abiertos, para observar que hace B mientras tanto.
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

    def operacion(nombre, cita, usuario):
        try:
            resultados[nombre] = services.reprogramar_cita(
                cita_id=cita.pk, usuario=usuario, nuevo_inicio=franja_objetivo
            )
        except services.CitaError as exc:  # se inspecciona en el hilo principal
            resultados[nombre] = exc
        finally:
            connection.close()

    # Dado que A ya movio su cita a la franja y mantiene el bloqueo del barbero
    hilo_a = threading.Thread(target=operacion, args=("A", cita_a, usuario_a), name="A")
    hilo_a.start()
    assert update_de_a_hecho.wait(ESPERA_MAXIMA)

    # Cuando B intenta moverse a la misma franja
    hilo_b = threading.Thread(target=operacion, args=("B", cita_b, usuario_b), name="B")
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
    cita_b.refresh_from_db()
    assert cita_b.start_at == hora_local(2, 11)
